"""Parse current-run Collector debug output into signal/service evidence."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

SIGNALS = {
    "ResourceSpans": "traces",
    "ResourceMetrics": "metrics",
    "ResourceLogs": "logs",
}
SIGNAL_HEADER = re.compile(r"\b(ResourceSpans|ResourceMetrics|ResourceLogs)\s+#\d+\b")
TIMESTAMP = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)")
SERVICE_NAME = re.compile(r"service\.name:\s*Str\(([^()]*)\)")
RESOURCE_START = re.compile(r"\bResource attributes:\s*")
RESOURCE_END = re.compile(r"\bScope(?:Spans|Metrics|Logs)\b|\b(?:Span|Metric|LogRecord) #\d+")

EXPECTED_SIGNAL_SERVICES: Mapping[str, frozenset[str]] = {
    "traces": frozenset({
        "api-gateway",
        "checkout-service",
        "order-service",
        "payment-service",
        "payco-mock",
    }),
    "metrics": frozenset({
        "api-gateway",
        "checkout-service",
        "order-service",
        "payment-service",
        "payco-mock",
    }),
    # order-service intentionally emits no business log during these scenarios.
    "logs": frozenset({"api-gateway", "checkout-service", "payment-service", "payco-mock"}),
}


def _parse_utc(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    # Docker may print nanoseconds; datetime accepts at most microsecond precision.
    if "." in normalized:
        head, tail = normalized.split(".", 1)
        fractional, zone = tail.split("+", 1)
        normalized = f"{head}.{fractional[:6]}+{zone}"
    parsed = datetime.fromisoformat(normalized)
    return parsed.astimezone(UTC)


def parse_collector_evidence(
    output: str,
    *,
    since: datetime,
    expected: Mapping[str, frozenset[str]] = EXPECTED_SIGNAL_SERVICES,
) -> dict[str, set[str]]:
    """Return service identities associated with signal resource blocks after ``since``.

    Docker's timestamped log prefix supplies the freshness boundary. A resource identity
    is accepted only inside a Collector signal's `Resource attributes` section.
    """
    found = {signal: set() for signal in expected}
    active_signal: str | None = None
    in_resource_attributes = False
    for line in output.splitlines():
        timestamp_match = TIMESTAMP.search(line)
        if timestamp_match is None:
            active_signal = None
            in_resource_attributes = False
            continue
        if _parse_utc(timestamp_match.group(1)) < since.astimezone(UTC):
            active_signal = None
            in_resource_attributes = False
            continue
        payload = line[timestamp_match.end() :]
        header = SIGNAL_HEADER.search(payload)
        if header:
            active_signal = SIGNALS[header.group(1)]
            in_resource_attributes = False
            continue
        if active_signal is None:
            continue
        if RESOURCE_START.search(payload.strip()):
            in_resource_attributes = True
            continue
        if RESOURCE_END.search(payload):
            in_resource_attributes = False
        if in_resource_attributes:
            match = SERVICE_NAME.search(payload)
            if match and active_signal in found:
                found[active_signal].add(match.group(1))
    return found


def missing_signal_services(
    found: Mapping[str, set[str]], expected: Mapping[str, frozenset[str]] = EXPECTED_SIGNAL_SERVICES
) -> dict[str, list[str]]:
    return {
        signal: sorted(services - found.get(signal, set()))
        for signal, services in expected.items()
        if services - found.get(signal, set())
    }


def format_missing(missing: Mapping[str, list[str]]) -> str:
    if not missing:
        return "none"
    return "; ".join(f"{signal}: {', '.join(services)}" for signal, services in missing.items())


@dataclass(frozen=True)
class Polling:
    timeout_seconds: float = 25
    poll_interval: float = 0.5
    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep


DEFAULT_POLLING = Polling()


class CollectorEvidenceTimeout(AssertionError):
    def __init__(
        self,
        timeout_seconds: float,
        missing: Mapping[str, list[str]],
        found: Mapping[str, set[str]],
        block_counts: Mapping[str, int],
    ) -> None:
        observed = "; ".join(
            f"{signal}={','.join(sorted(services)) or 'none'}" for signal, services in found.items()
        )
        counts = ", ".join(f"{signal}={count}" for signal, count in block_counts.items())
        super().__init__(
            f"Collector current-run evidence timed out after {timeout_seconds:g}s; "
            f"missing signal/service pairs: {format_missing(missing)}; "
            f"associated resources: {observed}; signal blocks: {counts}"
        )


def wait_for_collector_evidence(
    read_logs: Callable[[], str],
    *,
    since: datetime,
    expected: Mapping[str, frozenset[str]] = EXPECTED_SIGNAL_SERVICES,
    polling: Polling = DEFAULT_POLLING,
) -> dict[str, set[str]]:
    """Poll boundedly until all expected current-run signal/service pairs are received."""
    deadline = polling.monotonic() + polling.timeout_seconds
    found = {signal: set() for signal in expected}
    output = ""
    while True:
        output = read_logs()
        found = parse_collector_evidence(output, since=since, expected=expected)
        missing = missing_signal_services(found, expected)
        if not missing:
            return found
        remaining = deadline - polling.monotonic()
        if remaining <= 0:
            block_counts = {
                signal: sum(
                    1 for match in SIGNAL_HEADER.finditer(output) if match.group(1) == marker
                )
                for marker, signal in SIGNALS.items()
            }
            raise CollectorEvidenceTimeout(polling.timeout_seconds, missing, found, block_counts)
        polling.sleep(min(polling.poll_interval, remaining))
