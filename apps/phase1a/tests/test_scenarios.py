from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import httpx
from fastapi import FastAPI

from phase1a_demo.app import create_app


class ServiceRouter(httpx.AsyncBaseTransport):
    def __init__(self, apps: dict[str, FastAPI]) -> None:
        self.apps = apps
        self.calls: list[tuple[str, str, str, dict[str, str]]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        self.calls.append((host, request.method, request.url.path, dict(request.headers)))
        app = self.apps[host]
        return await httpx.ASGITransport(app=app).handle_async_request(request)


async def environment() -> tuple[dict[str, FastAPI], ServiceRouter, httpx.AsyncClient]:
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
        name: create_app(name, http_client=client, environ=env)
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
            assert data["scaled_status_counts"] == {"503": 4750, "429": 150, "forwarded": 100}
            assert data["http_5xx_percent"] == 95.0
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
