# ADR-0003: Modular Monolith First

- Status: Accepted
- Date: 2026-10-09

## Context

NEXUS has multiple logical components: ingestion, storage, intelligence, investigation, evaluation, API. The question is whether to deploy as separate services (microservices) or a single modular monolith.

## Decision

**Start with a modular monolith. Split only when measurements justify it.**

### Modular Monolith Structure

```
nexus/
├── nexus_ingestion/       # Collection, validation, normalization
├── nexus_storage/         # Telemetry + application state access
├── nexus_intelligence/    # Deterministic correlation, baselines, signals
├── nexus_investigation/   # Evidence bundle, agent workflow, diagnosis
├── nexus_evaluation/      # Benchmark runner, scoring, regression
├── nexus_api/             # HTTP/gRPC interface (thin)
└── nexus_shared/          # Domain models, schemas, utils
```

- Single deployable (container/binary)
- Single database (PostgreSQL) with schema-per-module
- Internal communication: direct function calls (not RPC)
- Clear module boundaries: public interfaces, private implementation

### Split Criteria (All Must Be Met)

1. **Independent scaling** — One module's load profile differs 10x from others (e.g., ingestion 100k eps vs. investigation 10 rpm)
2. **Independent deployment** — Team ownership requires separate release cadence
3. **Failure isolation** — Failure in one module must not cascade to others (circuit breakers insufficient)
4. **Measured need** — Not speculative; based on production metrics

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Microservices from start | Operational complexity (K8s, service mesh, distributed tracing) without proven need |
| Serverless functions | Cold starts, vendor lock-in, debugging difficulty, not suited for stateful intelligence |
| Monolith without modules | Becomes spaghetti; hard to extract later |

## Trade-offs and Consequences

**Pros:**
- Simple deployment (one container, one DB)
- Easy debugging (single process, shared memory)
- Refactoring across modules is trivial
- No network latency between modules
- Transactional consistency across modules (single DB)

**Cons:**
- Single point of failure (mitigated: stateless, horizontal scaling)
- Technology lock-in (all modules same language/runtime)
- Scale ceiling (mitigated: split when measured)

## Validation / Reversal Criteria

- **Validate:** Phase 3 runs on single container with <500ms p99 API latency under load test
- **Reverse if:** Any split criterion met with production data (not speculation)