from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import httpx
from fastapi import FastAPI
from opentelemetry.sdk._logs.export import InMemoryLogExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from phase1a_demo.app import create_app
from phase1a_demo.telemetry import Telemetry


class ServiceRouter(httpx.AsyncBaseTransport):
    def __init__(self, apps: dict[str, FastAPI]) -> None:
        self.apps = apps
        self.calls: list[tuple[str, str, str, dict[str, str]]] = []
        self.overrides: dict[tuple[str, str], int] = {}
        self.failures: set[tuple[str, str]] = set()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        self.calls.append((host, request.method, request.url.path, dict(request.headers)))
        key = (host, request.url.path)
        if key in self.failures:
            raise httpx.ConnectError("private test transport failure", request=request)
        if key in self.overrides:
            return httpx.Response(
                self.overrides[key], json={"error": "test_rejection"}, request=request
            )
        app = self.apps[host]
        return await httpx.ASGITransport(app=app).handle_async_request(request)


async def environment(
    metric_readers: dict[str, InMemoryMetricReader] | None = None,
    log_exporters: dict[str, InMemoryLogExporter] | None = None,
) -> tuple[dict[str, FastAPI], ServiceRouter, httpx.AsyncClient]:
    router = ServiceRouter({})
    client = httpx.AsyncClient(transport=router)
    env = {
        "NEXUS_DEMO_MODE": "true",
        "NEXUS_DEMO_TOKEN": "unit-test-token",
        "CHECKOUT_URL": "http://checkout-service:8000",
        "ORDER_URL": "http://order-service:8000",
        "PAYMENT_URL": "http://payment-service:8000",
        "PAYCO_URL": "http://payco-mock:8000",
    }
    apps = {
        name: create_app(
            name,
            http_client=client,
            environ=env,
            metric_reader=(metric_readers or {}).get(name),
            log_exporter=(log_exporters or {}).get(name),
        )
        for name in [
            "api-gateway",
            "checkout-service",
            "order-service",
            "payment-service",
            "payco-mock",
        ]
    }
    router.apps.update(apps)
    return apps, router, client


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def metric_points(reader: InMemoryMetricReader, name: str) -> list[tuple[str, Any, dict[str, Any]]]:
    data = reader.get_metrics_data()
    if data is None:
        return []
    return [
        (metric.unit, point, dict(point.attributes))
        for resource in data.resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
        if metric.name == name
        for point in metric.data.data_points
    ]


def test_inc001_checkout_to_payment_failure_and_reset() -> None:
    async def scenario() -> None:
        apps, router, client = await environment()
        gateway = httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["api-gateway"]))
        headers = {"authorization": "Bearer unit-test-token"}
        try:
            triggered = await gateway.post(
                "http://gateway/__demo__/trigger/INC-001", headers=headers
            )
            assert triggered.status_code == 200
            result = await gateway.post(
                "http://gateway/api/v1/checkout",
                json={},
                headers={"x-nexus-scenario": "INC-001"},
            )
            assert result.status_code == 500
            assert result.json()["service"] == "payment-service"
            calls = [(host, path) for host, _, path, _ in router.calls]
            assert ("checkout-service", "/api/v1/checkout") in calls
            assert ("payment-service", "/api/v1/charge") in calls
            gateway_hop = next(
                headers["traceparent"]
                for host, _, path, headers in router.calls
                if host == "checkout-service" and path == "/api/v1/checkout"
            )
            payment_hop = next(
                headers["traceparent"]
                for host, _, path, headers in router.calls
                if host == "payment-service" and path == "/api/v1/charge"
            )
            gateway_trace, gateway_client_span = gateway_hop.split("-")[1:3]
            payment_trace, payment_client_span = payment_hop.split("-")[1:3]
            assert gateway_trace == payment_trace
            assert gateway_client_span != payment_client_span
            reset = await gateway.post("http://gateway/__demo__/reset", headers=headers)
            assert reset.status_code == 200
            assert reset.json() == {"reset": True, "rate_limit_per_minute": 10000}
        finally:
            await gateway.aclose()
            await client.aclose()
            for app in apps.values():
                app.state.telemetry.shutdown()

    run(scenario())


def test_inc005_calls_payco_directly_and_models_virtual_timeout() -> None:
    async def scenario() -> None:
        apps, router, client = await environment()
        gateway = httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["api-gateway"]))
        headers = {"authorization": "Bearer unit-test-token"}
        try:
            healthy = await gateway.post("http://gateway/api/v1/checkout", json={})
            assert healthy.status_code == 200
            router.calls.clear()
            assert (
                await gateway.post("http://gateway/__demo__/trigger/INC-005", headers=headers)
            ).status_code == 200
            result = await gateway.post(
                "http://gateway/api/v1/checkout", json={}, headers={"x-nexus-scenario": "INC-005"}
            )
            assert result.status_code == 504
            assert result.json()["logical_latency_ms"] == 30000
            assert result.json()["timeout_ms"] == 10000
            calls = [(host, path) for host, _, path, _ in router.calls]
            assert ("payco-mock", "/api/v1/charge") in calls
            assert ("payment-service", "/api/v1/charge") not in calls
            await gateway.post("http://gateway/__demo__/reset", headers=headers)
        finally:
            await gateway.aclose()
            await client.aclose()
            for app in apps.values():
                app.state.telemetry.shutdown()

    run(scenario())


def test_inc006_keeps_5xx_separate_from_429_and_resets() -> None:
    async def scenario() -> None:
        apps, _, client = await environment()
        gateway = httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["api-gateway"]))
        headers = {"authorization": "Bearer unit-test-token"}
        try:
            triggered = await gateway.post(
                "http://gateway/__demo__/trigger/INC-006", headers=headers
            )
            assert triggered.json()["rate_limit_after"] == 100
            measured = await gateway.post(
                "http://gateway/__demo__/simulate/inc-006", headers=headers
            )
            data = measured.json()
            assert data["logical_requests"] == 5000
            assert data["modeled_scaled_status_counts"] == {
                "503": 4750,
                "429": 150,
                "forwarded": 100,
            }
            assert data["modeled_http_5xx_percent"] == 95.0
            assert data["status_mix_is_fixture_fact"] is False
            statuses = Counter()
            paths = ["checkout", "orders", "payments"]
            for index in range(100):
                route = paths[index % len(paths)]
                response = await gateway.post(f"http://gateway/api/v1/{route}", json={})
                statuses[response.status_code] += 1
            assert statuses == Counter({503: 95, 429: 3, 200: 2})
            await gateway.post("http://gateway/__demo__/reset", headers=headers)
            healthy = await gateway.post("http://gateway/api/v1/orders", json={})
            assert healthy.status_code == 200
        finally:
            await gateway.aclose()
            await client.aclose()
            for app in apps.values():
                app.state.telemetry.shutdown()

    run(scenario())


def test_inc006_metrics_separate_synthetic_model_from_real_http_decisions() -> None:
    async def scenario() -> None:
        reader = InMemoryMetricReader()
        apps, _, client = await environment({"api-gateway": reader})
        gateway = httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["api-gateway"]))
        headers = {"authorization": "Bearer unit-test-token"}
        try:
            assert (
                await gateway.post("http://gateway/__demo__/trigger/INC-006", headers=headers)
            ).status_code == 200
            modeled = await gateway.post(
                "http://gateway/__demo__/simulate/inc-006", headers=headers
            )
            body = modeled.json()
            assert body["modeled_scaled_status_counts"] == {
                "503": 4750,
                "429": 150,
                "forwarded": 100,
            }
            assert body["telemetry_recorded"].startswith("synthetic_model_counts_only")

            synthetic_before = metric_points(
                reader, "nexus.demo.synthetic.gateway.modeled_request_decisions"
            )
            assert sum(point.value for _, point, _ in synthetic_before) == 5000
            assert all(unit == "{request}" for unit, _, _ in synthetic_before)
            assert all(
                attrs["nexus.provenance"] == "synthetic_harness_assumption"
                for _, _, attrs in synthetic_before
            )
            assert metric_points(reader, "nexus.gateway.http.rate_limit.decisions") == []

            statuses: Counter[int] = Counter()
            routes = ["checkout", "orders", "payments"]
            for index in range(100):
                response = await gateway.post(f"http://gateway/api/v1/{routes[index % 3]}", json={})
                statuses[response.status_code] += 1
            assert statuses == Counter({503: 95, 429: 3, 200: 2})

            operational = metric_points(reader, "nexus.gateway.http.rate_limit.decisions")
            assert sum(point.value for _, point, _ in operational) == 100
            assert all(unit == "{request}" for unit, _, _ in operational)
            actual_by_class = {
                attrs["nexus.decision_class"]: (point.value, attrs["http.response.status_code"])
                for _, point, attrs in operational
            }
            assert actual_by_class == {
                "http_5xx": (95, 503),
                "http_429": (3, 429),
                "forwarded": (2, 200),
            }
            assert all(
                attrs["nexus.provenance"] == "observed_http_request" for _, _, attrs in operational
            )
            synthetic_after = metric_points(
                reader, "nexus.demo.synthetic.gateway.modeled_request_decisions"
            )
            assert [(u, p.value, a) for u, p, a in synthetic_after] == [
                (u, p.value, a) for u, p, a in synthetic_before
            ]
            assert metric_points(reader, "nexus.gateway.rate_limit.decisions") == []
        finally:
            await gateway.aclose()
            await client.aclose()
            for app in apps.values():
                app.state.telemetry.shutdown()

    run(scenario())


def test_inc005_timeout_counter_and_virtual_latency_have_correct_units() -> None:
    async def scenario() -> None:
        checkout_reader = InMemoryMetricReader()
        apps, _, client = await environment({"checkout-service": checkout_reader})
        gateway = httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["api-gateway"]))
        headers = {"authorization": "Bearer unit-test-token"}
        try:
            healthy = await gateway.post(
                "http://gateway/api/v1/checkout",
                json={},
                headers={"x-nexus-scenario": "INC-005"},
            )
            assert healthy.status_code == 200
            assert metric_points(checkout_reader, "nexus.payco.logical_timeouts") == []
            assert metric_points(checkout_reader, "nexus.demo.synthetic.logical_latency") == []
            assert metric_points(checkout_reader, "nexus.fixture.synthetic.rate_percent") == []

            assert (
                await gateway.post("http://gateway/__demo__/trigger/INC-005", headers=headers)
            ).status_code == 200
            first_timeout = await gateway.post(
                "http://gateway/api/v1/checkout",
                json={},
                headers={"x-nexus-scenario": "INC-005"},
            )
            assert first_timeout.status_code == 504
            first_latency = metric_points(checkout_reader, "nexus.demo.synthetic.logical_latency")
            assert len(first_latency) == 1
            assert first_latency[0][0] == "ms"
            assert first_latency[0][1].count == 1 and first_latency[0][1].sum == 30000

            second_timeout = await gateway.post(
                "http://gateway/api/v1/checkout",
                json={},
                headers={"x-nexus-scenario": "INC-005"},
            )
            assert second_timeout.status_code == 504

            timeout_points = metric_points(checkout_reader, "nexus.payco.logical_timeouts")
            assert sum(point.value for _, point, _ in timeout_points) == 2
            assert all(
                attrs["nexus.provenance"] == "observed_http_504" for _, _, attrs in timeout_points
            )
            latency_points = metric_points(checkout_reader, "nexus.demo.synthetic.logical_latency")
            assert len(latency_points) == 1
            unit, latency, attrs = latency_points[0]
            assert unit == "ms" and latency.count == 2 and latency.sum == 60000
            assert attrs["nexus.case_id"] == "INC-005"
            assert attrs["nexus.provenance"] == "synthetic_virtual_observation"
            percentage_points = metric_points(
                checkout_reader, "nexus.fixture.synthetic.rate_percent"
            )
            assert all(unit == "%" for unit, _, _ in percentage_points)
            assert sum(point.count for _, point, _ in percentage_points) == 4
            assert all(point.sum != 30000 for _, point, _ in percentage_points)
        finally:
            await gateway.aclose()
            await client.aclose()
            for app in apps.values():
                app.state.telemetry.shutdown()

    run(scenario())


def test_trigger_rejection_and_partial_reset_are_reported_without_secrets() -> None:
    async def scenario() -> None:
        apps, router, client = await environment()
        gateway = httpx.AsyncClient(transport=httpx.ASGITransport(app=apps["api-gateway"]))
        headers = {"authorization": "Bearer unit-test-token"}
        try:
            router.overrides[("payment-service", "/__internal__/scenario")] = 403
            trigger = await gateway.post("http://gateway/__demo__/trigger/INC-001", headers=headers)
            assert trigger.status_code == 502
            assert trigger.json() == {
                "error": "downstream_control_failed",
                "case_id": "INC-001",
                "completed_services": [],
                "failed_services": ["payment-service"],
                "partial": False,
            }
            assert "unit-test-token" not in trigger.text

            router.overrides.pop(("payment-service", "/__internal__/scenario"))
            router.failures.add(("payment-service", "/__internal__/scenario"))
            failed_trigger = await gateway.post(
                "http://gateway/__demo__/trigger/INC-001", headers=headers
            )
            assert failed_trigger.status_code == 502
            assert failed_trigger.json()["failed_services"] == ["payment-service"]
            router.failures.clear()
            router.overrides[("payco-mock", "/__internal__/scenario")] = 403
            apps["api-gateway"].state.gateway["rate_limit"] = 100
            reset = await gateway.post("http://gateway/__demo__/reset", headers=headers)
            assert reset.status_code == 502
            assert reset.json() == {
                "error": "downstream_control_failed",
                "case_id": "reset",
                "completed_services": ["payment-service"],
                "failed_services": ["payco-mock"],
                "partial": True,
            }
            assert apps["api-gateway"].state.gateway["rate_limit"] == 100
            assert "unit-test-token" not in reset.text
        finally:
            await gateway.aclose()
            await client.aclose()
            for app in apps.values():
                app.state.telemetry.shutdown()

    run(scenario())


def test_batch_log_export_flushes_at_shutdown_and_shutdown_is_idempotent() -> None:
    exporter = InMemoryLogExporter()
    telemetry = Telemetry("checkout-service", log_exporter=exporter)
    telemetry.log(
        30,
        "checkout.external_timeout",
        case_id="INC-005",
        logical_latency_ms=30000,
        timeout_ms=10000,
    )
    telemetry.shutdown()
    telemetry.shutdown()
    finished = exporter.get_finished_logs()
    assert len(finished) == 1
    record = finished[0].log_record
    assert record.body == "checkout.external_timeout"
    assert record.attributes["case_id"] == "INC-005"
    assert record.attributes["logical_latency_ms"] == 30000
    assert record.resource.attributes["service.name"] == "checkout-service"


def test_controls_are_disabled_without_explicit_demo_mode() -> None:
    async def scenario() -> None:
        app = create_app("api-gateway", environ={"NEXUS_DEMO_MODE": "false"})
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
        try:
            response = await client.post(
                "http://gateway/__demo__/trigger/INC-001",
                headers={"authorization": "Bearer local-demo-only"},
            )
            assert response.status_code == 403
        finally:
            await client.aclose()
            app.state.telemetry.shutdown()

    run(scenario())
