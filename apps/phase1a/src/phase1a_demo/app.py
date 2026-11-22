"""Service factory for the independently run Phase 1A HTTP processes."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind, Status, StatusCode

from phase1a_demo.telemetry import Telemetry, instrument_request, record_fixture_rate

SERVICE_NAMES = {
    "api-gateway",
    "checkout-service",
    "order-service",
    "payment-service",
    "payco-mock",
}
CONTROL_CASES = {"INC-001", "INC-005", "INC-006"}


def create_app(
    service_name: str,
    *,
    http_client: httpx.AsyncClient | None = None,
    environ: Mapping[str, str] | None = None,
) -> FastAPI:
    """Create a service app. ``http_client`` is injectable for in-process contract tests."""
    if service_name not in SERVICE_NAMES:
        raise ValueError(f"Unknown Phase 1A service: {service_name}")
    env = os.environ if environ is None else environ

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if application.state.client is None:
            application.state.client = httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0))
        try:
            yield
        finally:
            if application.state.owns_client and application.state.client is not None:
                await application.state.client.aclose()
            application.state.telemetry.shutdown()

    app = FastAPI(title=f"NEXUS {service_name}", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.service_name = service_name
    app.state.demo_mode = env.get("NEXUS_DEMO_MODE", "false").lower() == "true"
    app.state.demo_token = env.get("NEXUS_DEMO_TOKEN", "local-demo-only")
    app.state.telemetry = Telemetry(service_name)
    app.state.client = http_client
    app.state.owns_client = http_client is None
    app.state.faults = {"payment_null": False, "payco_degraded": False}
    app.state.gateway = {"rate_limit": 10000, "config_generation": 0, "scenario_index": 0}
    app.state.urls = {
        "checkout-service": env.get("CHECKOUT_URL", "http://checkout-service:8000"),
        "order-service": env.get("ORDER_URL", "http://order-service:8000"),
        "payment-service": env.get("PAYMENT_URL", "http://payment-service:8000"),
        "payco-mock": env.get("PAYCO_URL", "http://payco-mock:8000"),
    }

    @app.middleware("http")
    async def observe_requests(request: Request, call_next: Any) -> JSONResponse:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > 16384:
            return JSONResponse({"error": "request_too_large"}, status_code=413)
        route = request.url.path
        parent_context = extract(dict(request.headers))
        start = time.perf_counter()
        status = 500
        with app.state.telemetry.tracer.start_as_current_span(
            f"{request.method} {route}", context=parent_context, kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("http.route", route)
            span.set_attribute("service.name", service_name)
            try:
                response = await call_next(request)
                status = response.status_code
                span.set_attribute("http.response.status_code", status)
                if status >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                return response
            except Exception as exc:  # noqa: BLE001 - fail closed at the HTTP boundary
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                app.state.telemetry.log(
                    logging.ERROR, "request.unhandled_error", error_type=type(exc).__name__
                )
                return JSONResponse({"error": "internal_error"}, status_code=500)
            finally:
                instrument_request(
                    app.state.telemetry,
                    request.method,
                    route,
                    status,
                    (time.perf_counter() - start) * 1000,
                )

    def authorized(token: str | None) -> bool:
        return bool(app.state.demo_mode and token == f"Bearer {app.state.demo_token}")

    async def remote_request(
        destination: str,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        scenario: str | None = None,
        control: bool = False,
    ) -> httpx.Response:
        base = app.state.urls[destination].rstrip("/")
        parts = urlsplit(base)
        headers = {"content-type": "application/json"}
        if scenario:
            headers["x-nexus-scenario"] = scenario
        if control:
            headers["authorization"] = f"Bearer {app.state.demo_token}"
        url = f"{base}{path}"
        with app.state.telemetry.tracer.start_as_current_span(
            f"HTTP {method} {destination}", kind=SpanKind.CLIENT
        ) as span:
            span.set_attribute("server.address", parts.hostname or destination)
            span.set_attribute("http.request.method", method)
            span.set_attribute("http.route", path)
            carrier: dict[str, str] = {}
            inject(carrier)
            headers.update(carrier)
            try:
                response = await app.state.client.request(
                    method,
                    url,
                    json=body,
                    headers=headers,
                    timeout=httpx.Timeout(1.0, connect=0.5),
                )
                span.set_attribute("http.response.status_code", response.status_code)
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                return response
            except httpx.HTTPError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                raise

    async def internal_control(destination: str, enabled_case: str | None) -> None:
        await remote_request(
            destination,
            "POST",
            "/__internal__/scenario",
            body={"case_id": enabled_case},
            control=True,
        )

    @app.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "alive", "service": service_name}

    @app.get("/health/ready")
    async def readiness() -> dict[str, str]:
        return {"status": "ready", "service": service_name}

    if service_name == "payment-service":

        @app.post("/api/v1/charge")
        async def charge(request: Request) -> JSONResponse:
            payload = await request.json()
            billing_present = payload.get("billing_address") is not None
            case_id = request.headers.get("x-nexus-scenario", "")
            app.state.telemetry.payments.add(
                1, {"service.name": service_name, "outcome": "attempt"}
            )
            with app.state.telemetry.tracer.start_as_current_span("payment.charge") as span:
                span.set_attribute("nexus.billing_address_present", billing_present)
                if (
                    app.state.faults["payment_null"]
                    and case_id == "INC-001"
                    and not billing_present
                ):
                    exc = ValueError("billing_address was null")
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, "null billing address"))
                    app.state.telemetry.payments.add(
                        1, {"service.name": service_name, "outcome": "failure"}
                    )
                    app.state.telemetry.log(
                        logging.ERROR,
                        "payment.charge_failed",
                        case_id="INC-001",
                        exception_type="ValueError",
                        billing_address_present=False,
                    )
                    return JSONResponse(
                        {"error": "payment_charge_failed", "service": service_name}, status_code=500
                    )
            app.state.telemetry.payments.add(
                1, {"service.name": service_name, "outcome": "success"}
            )
            return JSONResponse({"status": "charged", "service": service_name}, status_code=200)

    elif service_name == "payco-mock":

        @app.post("/api/v1/charge")
        async def payco_charge() -> JSONResponse:
            if app.state.faults["payco_degraded"]:
                app.state.telemetry.log(
                    logging.WARNING,
                    "payco.logical_timeout",
                    case_id="INC-005",
                    logical_latency_ms=30000,
                    timeout_ms=10000,
                    wall_clock_sleep_ms=0,
                )
                return JSONResponse(
                    {
                        "error": "external_dependency_timeout",
                        "dependency": "payco-mock",
                        "logical_latency_ms": 30000,
                        "timeout_ms": 10000,
                        "wall_clock_sleep_ms": 0,
                        "provenance": "synthetic_virtual_observation",
                    },
                    status_code=504,
                )
            return JSONResponse({"status": "approved", "dependency": "payco-mock"})

    elif service_name == "checkout-service":

        @app.post("/api/v1/checkout")
        async def checkout(request: Request) -> JSONResponse:
            payload = await request.json()
            case_id = request.headers.get("x-nexus-scenario", "")
            if case_id == "INC-005":
                app.state.telemetry.payments.add(
                    1, {"service.name": service_name, "outcome": "attempt"}
                )
                app.state.telemetry.fixture_measurements.record(
                    30000,
                    {
                        "nexus.case_id": "INC-005",
                        "nexus.measurement": "payco_logical_latency_ms",
                        "nexus.provenance": "synthetic",
                    },
                )
                app.state.telemetry.payco_timeouts.add(1, {"dependency": "payco-mock"})
                with app.state.telemetry.tracer.start_as_current_span(
                    "checkout.payco_dependency"
                ) as span:
                    span.set_attribute("peer.service", "payco-mock")
                    span.set_attribute("nexus.demo.logical_latency_ms", 30000)
                    span.set_attribute("nexus.demo.timeout_ms", 10000)
                    response = await remote_request(
                        "payco-mock", "POST", "/api/v1/charge", body={}, scenario="INC-005"
                    )
                    if response.status_code == 504:
                        span.set_status(Status(StatusCode.ERROR, "logical external timeout"))
                        app.state.telemetry.payments.add(
                            1, {"service.name": service_name, "outcome": "failure"}
                        )
                        app.state.telemetry.log(
                            logging.WARNING,
                            "checkout.external_timeout",
                            case_id="INC-005",
                            dependency="payco-mock",
                            logical_latency_ms=30000,
                            timeout_ms=10000,
                            wall_clock_sleep_ms=0,
                        )
                        record_fixture_rate(
                            app.state.telemetry, "INC-005", "payment_success_rate", 99.5
                        )
                        record_fixture_rate(
                            app.state.telemetry, "INC-005", "payment_success_rate", 12.0
                        )
                        return JSONResponse(
                            {
                                "error": "external_dependency_timeout",
                                "dependency": "payco-mock",
                                "payment_success_rate_before_percent": 99.5,
                                "payment_success_rate_after_percent": 12.0,
                                "timeout_ms": 10000,
                                "logical_latency_ms": 30000,
                                "provenance": "synthetic_virtual_observation",
                            },
                            status_code=504,
                        )
                    app.state.telemetry.payments.add(
                        1, {"service.name": service_name, "outcome": "success"}
                    )
                    return JSONResponse({"status": "checked_out", "payment": response.json()})

            response = await remote_request(
                "payment-service",
                "POST",
                "/api/v1/charge",
                body={"billing_address": payload.get("billing_address")},
                scenario=case_id or None,
            )
            if response.status_code >= 400:
                return JSONResponse(response.json(), status_code=response.status_code)
            return JSONResponse({"status": "checked_out", "payment": response.json()})

    elif service_name == "order-service":

        @app.post("/api/v1/orders")
        async def place_order() -> dict[str, str]:
            return {"status": "accepted", "service": "order-service", "order_ref": "demo-order"}

    if service_name == "api-gateway":

        @app.get("/__demo__/status")
        async def demo_status() -> JSONResponse:
            return JSONResponse(
                {
                    "demo_mode": app.state.demo_mode,
                    "service": service_name,
                    "rate_limit_per_minute": app.state.gateway["rate_limit"],
                    "scenario_index": app.state.gateway["scenario_index"],
                }
            )

        @app.post("/__demo__/trigger/{case_id}")
        async def trigger(
            case_id: str, authorization: str | None = Header(default=None)
        ) -> JSONResponse:
            if not authorized(authorization):
                return JSONResponse({"error": "demo_control_not_authorized"}, status_code=403)
            if case_id not in CONTROL_CASES:
                return JSONResponse({"error": "unsupported_scenario"}, status_code=404)
            if case_id == "INC-001":
                await internal_control("payment-service", case_id)
                record_fixture_rate(app.state.telemetry, case_id, "payment_error_rate", 0.1)
                record_fixture_rate(app.state.telemetry, case_id, "payment_error_rate", 12.0)
                app.state.telemetry.log(
                    logging.INFO,
                    "scenario.synthetic_change_observation",
                    case_id=case_id,
                    change_id="chg-001-deploy-payment-v231",
                    fixture_commit_reference="abc123def456",
                    version="2.3.1",
                    occurred_at="2024-01-15T09:55:00Z",
                    provenance="synthetic_fixture_observation_not_provider_data",
                )
                return JSONResponse(
                    {
                        "case_id": case_id,
                        "triggered": True,
                        "fault_service": "payment-service",
                        "metric": {
                            "before_percent": 0.1,
                            "after_percent": 12,
                            "window": "synthetic 5-minute evidence window",
                        },
                        "source_discrepancy": "fixture symptom says 2 minutes; ev-001-metric-error-rate says 5 minutes",
                        "change_observation": "synthetic; no Git/deployment provider queried",
                    }
                )
            if case_id == "INC-005":
                await internal_control("payco-mock", case_id)
                return JSONResponse(
                    {
                        "case_id": case_id,
                        "triggered": True,
                        "path": "checkout-service -> payco-mock",
                        "logical_latency_ms": 30000,
                        "timeout_ms": 10000,
                        "wall_clock_sleep_ms": 0,
                        "changes": "none; fixture has no local change record",
                    }
                )
            app.state.gateway.update(rate_limit=100, scenario_index=0)
            app.state.gateway["config_generation"] += 1
            app.state.telemetry.log(
                logging.WARNING,
                "gateway.synthetic_config_change",
                case_id=case_id,
                previous_value=10000,
                new_value=100,
                unit="requests_per_minute",
                fixture_change_id="chg-001-config-rate-limit",
                config_changed_at="2024-01-20T07:59:00Z",
                fixture_commit_reference="stu901vwx234",
                fixture_commit_time="2024-01-19T15:00:00Z",
                provenance="synthetic_fixture_observation_not_provider_data",
            )
            record_fixture_rate(app.state.telemetry, case_id, "gateway_5xx_rate", 0.0)
            record_fixture_rate(app.state.telemetry, case_id, "gateway_5xx_rate", 95.0)
            return JSONResponse(
                {
                    "case_id": case_id,
                    "triggered": True,
                    "primary_service": "api-gateway",
                    "rate_limit_before": 10000,
                    "rate_limit_after": 100,
                    "fixture_http_5xx_rate_percent": 95,
                    "traffic_model": "5000 logical requests/minute; 100 actual requests stand for 5000 virtual requests",
                    "status_mix_assumption": "95 503, 3 429, 2 forwarded per 100 actual requests; illustrative harness mix, not fixture ratio",
                    "trace_evidence": "supplemental instrumentation; fixture has no trace evidence",
                }
            )

        @app.post("/__demo__/reset")
        async def reset(authorization: str | None = Header(default=None)) -> JSONResponse:
            if not authorized(authorization):
                return JSONResponse({"error": "demo_control_not_authorized"}, status_code=403)
            app.state.gateway.update(rate_limit=10000, scenario_index=0)
            await internal_control("payment-service", None)
            await internal_control("payco-mock", None)
            return JSONResponse({"reset": True, "rate_limit_per_minute": 10000})

        @app.post("/__demo__/simulate/inc-006")
        async def simulate_inc006(authorization: str | None = Header(default=None)) -> JSONResponse:
            if not authorized(authorization):
                return JSONResponse({"error": "demo_control_not_authorized"}, status_code=403)
            if app.state.gateway["rate_limit"] != 100:
                return JSONResponse({"error": "INC-006_not_triggered"}, status_code=409)
            # 100 request units model 5,000 requests/minute at 50 requests per unit.
            # The 503/429 split is a documented deterministic harness assumption.
            counts = {"503": 0, "429": 0, "forwarded": 0}
            for _ in range(100):
                index = app.state.gateway["scenario_index"] % 100
                app.state.gateway["scenario_index"] += 1
                if index < 95:
                    counts["503"] += 1
                elif index < 98:
                    counts["429"] += 1
                else:
                    counts["forwarded"] += 1
            scaled = {key: value * 50 for key, value in counts.items()}
            app.state.telemetry.rate_decisions.add(
                counts["503"], {"http.response.status_code": 503}
            )
            app.state.telemetry.rate_decisions.add(
                counts["429"], {"http.response.status_code": 429}
            )
            app.state.telemetry.rate_decisions.add(
                counts["forwarded"], {"http.response.status_code": 200}
            )
            return JSONResponse(
                {
                    "actual_request_units": 100,
                    "logical_requests": 5000,
                    "logical_requests_per_minute": 5000,
                    "scaled_status_counts": scaled,
                    "http_5xx_percent": 95.0,
                    "http_429_percent": 3.0,
                    "forwarded_percent": 2.0,
                    "status_mix_is_fixture_fact": False,
                }
            )

        async def gateway_proxy(
            request: Request, destination: str, path: str, body: dict[str, Any]
        ) -> JSONResponse:
            if app.state.gateway["rate_limit"] == 100:
                index = app.state.gateway["scenario_index"] % 100
                app.state.gateway["scenario_index"] += 1
                if index < 95:
                    app.state.telemetry.rate_decisions.add(1, {"http.response.status_code": 503})
                    app.state.telemetry.log(
                        logging.WARNING,
                        "gateway.rate_limit_exceeded",
                        case_id="INC-006",
                        configured_limit_per_minute=100,
                        logical_status=503,
                    )
                    return JSONResponse(
                        {"error": "rate_limit_upstream_unavailable"}, status_code=503
                    )
                if index < 98:
                    app.state.telemetry.rate_decisions.add(1, {"http.response.status_code": 429})
                    return JSONResponse({"error": "rate_limit_exceeded"}, status_code=429)
            scenario = request.headers.get("x-nexus-scenario")
            try:
                response = await remote_request(
                    destination, "POST", path, body=body, scenario=scenario
                )
            except httpx.HTTPError:
                return JSONResponse({"error": "downstream_unavailable"}, status_code=503)
            if app.state.gateway["rate_limit"] == 100:
                app.state.telemetry.rate_decisions.add(
                    1, {"http.response.status_code": response.status_code}
                )
            return JSONResponse(response.json(), status_code=response.status_code)

        @app.post("/api/v1/checkout")
        async def gateway_checkout(request: Request) -> JSONResponse:
            payload = await request.json()
            return await gateway_proxy(request, "checkout-service", "/api/v1/checkout", payload)

        @app.post("/api/v1/orders")
        async def gateway_orders(request: Request) -> JSONResponse:
            payload = await request.json()
            return await gateway_proxy(request, "order-service", "/api/v1/orders", payload)

        @app.post("/api/v1/payments")
        async def gateway_payments(request: Request) -> JSONResponse:
            payload = await request.json()
            return await gateway_proxy(request, "payment-service", "/api/v1/charge", payload)

    if service_name != "api-gateway":

        @app.post("/__internal__/scenario")
        async def internal_scenario(
            request: Request, authorization: str | None = Header(default=None)
        ) -> JSONResponse:
            if not authorized(authorization):
                return JSONResponse({"error": "demo_control_not_authorized"}, status_code=403)
            payload = await request.json()
            case_id = payload.get("case_id")
            if service_name == "payment-service":
                app.state.faults["payment_null"] = case_id == "INC-001"
            elif service_name == "payco-mock":
                app.state.faults["payco_degraded"] = case_id == "INC-005"
            return JSONResponse({"service": service_name, "case_id": case_id, "updated": True})

    return app
