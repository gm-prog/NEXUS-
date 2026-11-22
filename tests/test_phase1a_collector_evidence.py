from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.phase1a_collector import (
    EXPECTED_SIGNAL_SERVICES,
    Polling,
    missing_signal_services,
    parse_collector_evidence,
    wait_for_collector_evidence,
)

SINCE = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


def transcript_block(signal: str, service: str, timestamp: datetime = SINCE) -> str:
    header = {
        "traces": "ResourceSpans",
        "metrics": "ResourceMetrics",
        "logs": "ResourceLogs",
    }[signal]
    stamp = timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")
    scope_type = {"traces": "Spans", "metrics": "Metrics", "logs": "Logs"}[signal]
    return "\n".join([
        f"{stamp} otel-collector-1 | {header} #0",
        f"{stamp} otel-collector-1 | Resource attributes:",
        f"{stamp} otel-collector-1 |     -> service.name: Str({service})",
        f"{stamp} otel-collector-1 | Scope{scope_type}",
    ])


def valid_transcript() -> str:
    return "\n".join(
        transcript_block(signal, service)
        for signal, services in EXPECTED_SIGNAL_SERVICES.items()
        for service in sorted(services)
    )


def test_valid_current_run_collector_transcript_associates_service_resources() -> None:
    found = parse_collector_evidence(valid_transcript(), since=SINCE)
    assert missing_signal_services(found) == {}
    assert found == {signal: set(services) for signal, services in EXPECTED_SIGNAL_SERVICES.items()}


def test_missing_log_signal_fails() -> None:
    output = "\n".join(
        transcript_block(signal, service)
        for signal, services in EXPECTED_SIGNAL_SERVICES.items()
        if signal != "logs"
        for service in services
    )
    missing = missing_signal_services(parse_collector_evidence(output, since=SINCE))
    assert missing == {"logs": sorted(EXPECTED_SIGNAL_SERVICES["logs"])}


def test_required_service_missing_from_signal_fails() -> None:
    output = "\n".join(
        transcript_block(signal, service)
        for signal, services in EXPECTED_SIGNAL_SERVICES.items()
        for service in services
        if not (signal == "metrics" and service == "order-service")
    )
    missing = missing_signal_services(parse_collector_evidence(output, since=SINCE))
    assert missing == {"metrics": ["order-service"]}


def test_service_name_under_wrong_signal_does_not_satisfy_matrix() -> None:
    output = "\n".join(
        transcript_block(signal, service)
        for signal, services in EXPECTED_SIGNAL_SERVICES.items()
        for service in services
        if not (signal == "traces" and service == "payment-service")
    )
    output += "\n" + transcript_block("metrics", "payment-service")
    missing = missing_signal_services(parse_collector_evidence(output, since=SINCE))
    assert missing == {"traces": ["payment-service"]}


def test_only_pre_cutoff_stale_evidence_fails() -> None:
    stale = SINCE - timedelta(seconds=1)
    output = "\n".join(
        transcript_block(signal, service, stale)
        for signal, services in EXPECTED_SIGNAL_SERVICES.items()
        for service in services
    )
    missing = missing_signal_services(parse_collector_evidence(output, since=SINCE))
    assert set(missing) == set(EXPECTED_SIGNAL_SERVICES)


def test_markers_and_names_without_associated_resource_blocks_fail() -> None:
    stamp = SINCE.isoformat(timespec="seconds").replace("+00:00", "Z")
    output = "\n".join([
        f"{stamp} otel | ResourceSpans #0 ResourceMetrics #0 ResourceLogs #0",
        f"{stamp} otel | api-gateway checkout-service order-service payment-service payco-mock",
    ])
    missing = missing_signal_services(parse_collector_evidence(output, since=SINCE))
    assert missing == {
        signal: sorted(services) for signal, services in EXPECTED_SIGNAL_SERVICES.items()
    }


def test_bounded_polling_error_names_missing_signal_and_service() -> None:
    now = [0.0]
    polls: list[int] = []

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    def read() -> str:
        polls.append(1)
        return transcript_block("traces", "api-gateway")

    with pytest.raises(AssertionError, match=r"logs: api-gateway, checkout-service"):
        wait_for_collector_evidence(
            read,
            since=SINCE,
            polling=Polling(timeout_seconds=1, poll_interval=0.4, monotonic=clock, sleep=sleep),
        )
    expected_poll_count = 4
    assert len(polls) == expected_poll_count
    assert now[0] == 1.0
