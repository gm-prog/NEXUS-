#!/usr/bin/env python3
# Ruff exceptions are local to this user-facing CLI: it prints results, compares
# HTTP/status literals, and reports assertion detail at the command boundary.
# ruff: noqa: PLR2004, PLW0717, T201, TRY003, TRY300
"""Black-box smoke runner for the loopback-published Phase 1A Compose stack."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from phase1a_collector import wait_for_collector_evidence

BASE_URL = os.environ.get("NEXUS_PHASE1A_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("NEXUS_DEMO_TOKEN", "local-demo-only")
COMPOSE = [
    "docker",
    "compose",
    "-f",
    "apps/phase1a/compose.yaml",
    "--project-directory",
    "apps/phase1a",
]


def request(
    path: str, body: dict[str, Any] | None = None, *, control: bool = False
) -> tuple[int, dict[str, Any]]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"content-type": "application/json"}
    if control:
        headers["authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(
        BASE_URL + path, data=data, headers=headers, method="POST" if data is not None else "GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def wait_ready(timeout: int = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            code, data = request("/health/ready")
            if code == 200 and data.get("service") == "api-gateway":
                return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise RuntimeError("gateway did not become ready within 120 seconds")


def reset() -> None:
    status, payload = request("/__demo__/reset", {}, control=True)
    if status != 200 or payload.get("reset") is not True:
        raise AssertionError(f"reset failed: HTTP {status} {payload}")


def run_case(case_id: str) -> None:
    reset()
    if case_id == "INC-001":
        status, payload = request("/__demo__/trigger/INC-001", {}, control=True)
        assert (
            status == 200 and payload["metric"]["window"] == "synthetic 5-minute evidence window"
        ), payload
        # The scenario header marks the controlled request; the omitted billing
        # address is not logged.
        status, payload = request_with_scenario("/api/v1/checkout", {}, "INC-001")
        assert status == 500 and payload.get("service") == "payment-service", payload
        print(
            "PASS INC-001 gateway -> checkout -> payment; controlled HTTP 500; synthetic 5m metric"
        )
    elif case_id == "INC-005":
        status, _ = request("/api/v1/checkout", {"billing_address": {"synthetic": True}})
        assert status == 200, "healthy checkout should work before fault injection"
        status, payload = request("/__demo__/trigger/INC-005", {}, control=True)
        assert status == 200 and payload["path"] == "checkout-service -> payco-mock", payload
        status, payload = request_with_scenario("/api/v1/checkout", {}, "INC-005")
        assert status == 504, payload
        assert payload["logical_latency_ms"] == 30000 and payload["timeout_ms"] == 10000, payload
        assert payload["payment_success_rate_before_percent"] == 99.5
        assert payload["payment_success_rate_after_percent"] == 12.0
        print("PASS INC-005 direct checkout -> payco-mock; virtual 30s vs 10s timeout")
    elif case_id == "INC-006":
        status, payload = request("/__demo__/trigger/INC-006", {}, control=True)
        assert status == 200 and payload["rate_limit_after"] == 100, payload
        status, modeled = request("/__demo__/simulate/inc-006", {}, control=True)
        assert status == 200 and modeled["modeled_http_5xx_percent"] == 95.0, modeled
        statuses: Counter[int] = Counter()
        routes = ["checkout", "orders", "payments"]
        for index in range(100):
            status, _ = request(f"/api/v1/{routes[index % len(routes)]}", {})
            statuses[status] += 1
        assert statuses == Counter({503: 95, 429: 3, 200: 2}), dict(statuses)
        print("PASS INC-006 95/3/2 synthetic model plus separate real HTTP decision sample")
    else:
        raise ValueError(f"unsupported case: {case_id}")
    reset()


def request_with_scenario(
    path: str, body: dict[str, Any], case_id: str
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "x-nexus-scenario": case_id},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def verify_topology() -> None:
    status, _ = request("/api/v1/checkout", {"billing_address": {"synthetic": True}})
    assert status == 200, "healthy checkout route failed"
    status, data = request("/api/v1/orders", {})
    assert status == 200 and data["service"] == "order-service", data
    status, data = request("/api/v1/payments", {"billing_address": {"synthetic": True}})
    assert status == 200 and data["service"] == "payment-service", data
    print("PASS healthy gateway routes reach checkout, order, and payment services")


def verify_collector(since: datetime) -> None:
    since_value = since.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

    def read_current_run_logs() -> str:
        try:
            result = subprocess.run(
                [
                    *COMPOSE,
                    "logs",
                    "--no-color",
                    "--timestamps",
                    "--since",
                    since_value,
                    "otel-collector",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Compose Collector log read exceeded its 5-second bound") from exc
        if result.returncode:
            raise RuntimeError(f"Compose Collector log read failed: {result.stderr[-1000:]}")
        return result.stdout

    found = wait_for_collector_evidence(read_current_run_logs, since=since)
    for signal, services in found.items():
        print(f"PASS Collector {signal}: {', '.join(sorted(services))}")
    print(
        "PASS current-run Collector receipt matches required signal/service pairs; "
        "order-service emits no scenario business log by design"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", choices=["INC-001", "INC-005", "INC-006", "all"], default="all"
    )
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--verify-telemetry", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1 or args.repeat > 5:
        parser.error("--repeat must be between 1 and 5")
    try:
        wait_ready()
        # Set the freshness cutoff immediately before topology/scenario smoke traffic.
        smoke_started_at = datetime.now(UTC)
        if args.scenario == "all":
            verify_topology()
            scenarios = ["INC-001", "INC-005", "INC-006"]
        else:
            scenarios = [args.scenario]
        for repetition in range(args.repeat):
            print(f"Scenario pass {repetition + 1}/{args.repeat}")
            for case_id in scenarios:
                run_case(case_id)
        if args.verify_telemetry:
            verify_collector(smoke_started_at)
        print("Phase 1A smoke checks passed")
        return 0
    except (AssertionError, RuntimeError, OSError, ValueError) as error:
        message = f"Phase 1A smoke check failed: {error}"
        print(message, file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            annotation = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=Phase 1A smoke failure::{annotation}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
