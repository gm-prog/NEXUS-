"""Small, bounded-cardinality OpenTelemetry and structured logging setup."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class JsonFormatter(logging.Formatter):
    """Emit safe JSON records with active trace correlation when available."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        payload: dict[str, Any] = {
            "timestamp_unix_ms": int(record.created * 1000),
            "severity": record.levelname,
            "service.name": self.service_name,
            "message": record.getMessage(),
        }
        if span_context.is_valid:
            payload["trace_id"] = f"{span_context.trace_id:032x}"
            payload["span_id"] = f"{span_context.span_id:016x}"
        standard_fields = logging.makeLogRecord({}).__dict__
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in standard_fields and key not in {"message", "asctime"}
            }
        )
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class Telemetry:
    """Per-process providers and instruments. Exporters are enabled by explicit config."""

    def __init__(
        self,
        service_name: str,
        *,
        metric_reader: MetricReader | None = None,
        log_exporter: LogExporter | None = None,
    ) -> None:
        self.service_name = service_name
        self._shutdown = False
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.handlers.clear()
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(JsonFormatter(service_name))
        self.logger.addHandler(console)

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": "0.1.0",
                "deployment.environment.name": "nexus-local-demo",
            }
        )
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            self.tracer_provider = TracerProvider(resource=resource)
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
            )
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint, insecure=True), export_interval_millis=1000
            )
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            otlp_log_exporter = OTLPLogExporter(endpoint=endpoint, insecure=True)
            trace.set_tracer_provider(self.tracer_provider)
            metrics.set_meter_provider(self.meter_provider)
        else:
            self.tracer_provider = TracerProvider(resource=resource)
            self.meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader] if metric_reader is not None else [],
            )
            otlp_log_exporter = log_exporter

        if endpoint:
            self.logger_provider = LoggerProvider(resource=resource)
            self.logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(otlp_log_exporter)
            )
            self.logger.addHandler(
                LoggingHandler(level=logging.INFO, logger_provider=self.logger_provider)
            )
        else:
            self.logger_provider = LoggerProvider(resource=resource)
            if log_exporter is not None:
                self.logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
                self.logger.addHandler(
                    LoggingHandler(level=logging.INFO, logger_provider=self.logger_provider)
                )

        self.tracer = self.tracer_provider.get_tracer("nexus.phase1a", "0.1.0")
        meter = self.meter_provider.get_meter("nexus.phase1a", "0.1.0")
        self.requests = meter.create_counter("http.server.request.count", unit="{request}")
        self.request_duration = meter.create_histogram(
            "http.server.request.duration", unit="ms", description="HTTP server duration"
        )
        self.payments = meter.create_counter("nexus.payment.attempts", unit="{attempt}")
        self.payco_timeouts = meter.create_counter("nexus.payco.logical_timeouts", unit="{call}")
        self.http_rate_decisions = meter.create_counter(
            "nexus.gateway.http.rate_limit.decisions",
            unit="{request}",
            description="Operational decisions made for real gateway HTTP requests only",
        )
        self.modeled_rate_decisions = meter.create_counter(
            "nexus.demo.synthetic.gateway.modeled_request_decisions",
            unit="{request}",
            description="Synthetic harness model counts, never observed HTTP requests",
        )
        self.fixture_measurements = meter.create_histogram(
            "nexus.fixture.synthetic.rate_percent", unit="%", description="Synthetic fixture rates"
        )
        self.logical_latency = meter.create_histogram(
            "nexus.demo.synthetic.logical_latency",
            unit="ms",
            description="Synthetic virtual per-call latency observations, not wall-clock duration",
        )

    def log(self, level: int, message: str, **attributes: Any) -> None:
        # Structured fields are represented in JSON and are bounded, non-sensitive metadata.
        self.logger.log(level, message, extra=attributes)

    def shutdown(self) -> None:
        """Flush queued telemetry once; repeated lifecycle shutdowns are harmless."""
        if self._shutdown:
            return
        self._shutdown = True
        providers = (
            ("traces", self.tracer_provider),
            ("metrics", self.meter_provider),
            ("logs", self.logger_provider),
        )
        failures: list[tuple[str, Exception | None]] = []
        for signal, provider in providers:
            try:
                if not provider.force_flush(timeout_millis=2000):
                    failures.append((signal, None))
            except Exception as exc:  # noqa: BLE001 - still close all providers below
                failures.append((signal, exc))
        for signal, provider in providers:
            try:
                provider.shutdown()
            except Exception as exc:  # noqa: BLE001 - finish closing the remaining providers
                failures.append((signal, exc))
        if failures:
            failed_signals = sorted({signal for signal, _ in failures})
            cause = next((error for _, error in failures if error is not None), None)
            raise RuntimeError(
                f"OpenTelemetry flush/shutdown failed for: {failed_signals}"
            ) from cause


def instrument_request(
    telemetry: Telemetry, method: str, route: str, status: int, elapsed_ms: float
) -> None:
    attributes = {
        "http.request.method": method,
        "http.route": route,
        "http.response.status_code": status,
    }
    telemetry.requests.add(1, attributes)
    telemetry.request_duration.record(elapsed_ms, attributes)


def record_gateway_http_decision(telemetry: Telemetry, status_code: int) -> None:
    """Record one real gateway request decision with explicit status classification."""
    decision = (
        "http_429"
        if status_code == 429
        else "http_5xx"
        if 500 <= status_code <= 599
        else "forwarded"
    )
    telemetry.http_rate_decisions.add(
        1,
        {
            "http.response.status_code": status_code,
            "nexus.decision_class": decision,
            "nexus.provenance": "observed_http_request",
        },
    )


def record_fixture_rate(telemetry: Telemetry, case_id: str, name: str, value: float) -> None:
    telemetry.fixture_measurements.record(
        value,
        {"nexus.case_id": case_id, "nexus.measurement": name, "nexus.provenance": "synthetic"},
    )


def now_ms() -> float:
    return time.perf_counter() * 1000
