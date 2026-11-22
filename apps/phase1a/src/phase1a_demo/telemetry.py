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
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
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

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
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
            self.logger_provider = LoggerProvider(resource=resource)
            self.logger_provider.add_log_record_processor(
                SimpleLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True))
            )
            self.logger.addHandler(
                LoggingHandler(level=logging.INFO, logger_provider=self.logger_provider)
            )
            trace.set_tracer_provider(self.tracer_provider)
            metrics.set_meter_provider(self.meter_provider)
        else:
            self.tracer_provider = TracerProvider(resource=resource)
            self.meter_provider = MeterProvider(resource=resource)
            self.logger_provider = LoggerProvider(resource=resource)

        self.tracer = self.tracer_provider.get_tracer("nexus.phase1a", "0.1.0")
        meter = self.meter_provider.get_meter("nexus.phase1a", "0.1.0")
        self.requests = meter.create_counter("http.server.request.count", unit="{request}")
        self.request_duration = meter.create_histogram(
            "http.server.request.duration", unit="ms", description="HTTP server duration"
        )
        self.payments = meter.create_counter("nexus.payment.attempts", unit="{attempt}")
        self.payco_timeouts = meter.create_counter("nexus.payco.logical_timeouts", unit="{call}")
        self.rate_decisions = meter.create_counter(
            "nexus.gateway.rate_limit.decisions", unit="{request}"
        )
        self.fixture_measurements = meter.create_histogram(
            "nexus.fixture.synthetic.rate_percent", unit="%", description="Synthetic fixture rates"
        )

    def log(self, level: int, message: str, **attributes: Any) -> None:
        # Structured fields are represented in JSON and are bounded, non-sensitive metadata.
        self.logger.log(level, message, extra=attributes)

    def shutdown(self) -> None:
        self.tracer_provider.force_flush(timeout_millis=2000)
        self.meter_provider.force_flush(timeout_millis=2000)
        self.logger_provider.force_flush(timeout_millis=2000)
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()
        self.logger_provider.shutdown()


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


def record_fixture_rate(telemetry: Telemetry, case_id: str, name: str, value: float) -> None:
    telemetry.fixture_measurements.record(
        value,
        {"nexus.case_id": case_id, "nexus.measurement": name, "nexus.provenance": "synthetic"},
    )


def now_ms() -> float:
    return time.perf_counter() * 1000
