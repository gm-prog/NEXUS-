# ADR-0016: Phase 1A Local Demo Runtime and Telemetry

- **Status:** Proposed
- **Date:** 2026-10-18
- **Decision owners:** NEXUS maintainers

## Context

Phase 1A needs a reproducible local vertical slice for exactly four application services (`api-gateway`, `checkout-service`, `order-service`, and `payment-service`), a non-application PayCo mock, and an OpenTelemetry proof sink. The Phase 0 `nexus-benchmarks` package and root lock are deliberately stable; the demo must not add runtime dependencies to them. The slice is synthetic and must not contact real payment providers, persist telemetry, or imply that fixture observations came from production systems.

## Decision

Implement the demo under `apps/phase1a/` as a separately locked Python project using FastAPI, Uvicorn, HTTPX, and the OpenTelemetry Python SDK/exporters. One shared application package is run as five separate Compose services/processes with distinct service names and health endpoints. The gateway is the only host-published app endpoint, bound to `127.0.0.1`; backend services and PayCo remain on a private Compose bridge network. A pinned OpenTelemetry Collector receives OTLP traces, metrics and logs and exports them through the `debug` exporter to container stdout only.

Scenario controls are enabled only when `NEXUS_DEMO_MODE=true` and require a demo-only bearer token. The local control interface has no production capability. Server middleware and HTTPX wrappers create explicit SDK spans and inject W3C context at the client-span boundary; this small manual instrumentation avoids additional auto-instrumentation packages and keeps routes/metric dimensions explicit. Scenario time/traffic measurements are synthetic virtual observations and carry explicit provenance/assumption labels. Phase 1A includes only INC-001, INC-005 and INC-006. It has no database, durable telemetry backend, AI, evaluator, or remediation capability.

## Alternatives considered

1. **Add FastAPI/OpenTelemetry to the root project.** Rejected because it changes the Phase 0 CLI's dependency/runtime contract and root lock for the demo.
2. **Use one process with four logical service names.** Rejected because it would not prove independent service processes or real inter-service HTTP calls.
3. **Use a production observability backend or database.** Rejected because Phase 1A requires a non-durable local proof sink; storage selection is deferred to the ADR-0006 measurement work in Phase 1B.
4. **Call real PayCo or a Git/deployment provider.** Rejected because the demo is deterministic and local. Fixture IDs/commit references are synthetic scenario records, not provider observations.
5. **Use Kubernetes, a service mesh, or a distributed chaos framework.** Rejected as disproportionate for this bounded local slice.

## Consequences

- The app has its own `pyproject.toml` and `uv.lock`; root dependency declarations and `uv.lock` remain unchanged.
- Compose is required for the multi-process integration proof. Unit/contract tests remain runnable without Docker.
- Collector stdout is ephemeral and must be inspected with `docker compose logs` or cleared by removing the stack.
- The demo mapping documents implementation assumptions separately from benchmark fixture facts. In particular, HTTP 429 is not counted as 5xx; the deterministic INC-006 traffic mix is an explicit harness assumption, not a fixture ratio.
- The Python implementation of the INC-001 null dereference is a controlled Python exception, not a fabricated Java stack trace.

## Validation and reversal

Before treating Phase 1A as complete, verify the isolated app lock, app tests under Python 3.11 and 3.12, Compose health/readiness, all three scenario paths, Collector receipt of all three signals, reset/repeatability, root Phase 0 gates, and CI on the exact PR head. Revisit this choice if measured workload or developer experience shows the separate Python project or stdout-only Collector cannot meet the Phase 1A exit criteria. This proposal does not accept or modify ADR-0004, ADR-0006, or ADR-0015.
