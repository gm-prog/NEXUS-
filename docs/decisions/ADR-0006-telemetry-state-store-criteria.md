# ADR-0006: Telemetry & State Store Decision Criteria

- Status: Accepted
- Date: 2024-01-15

## Context

NEXUS needs two distinct storage systems:
1. **Telemetry Storage** — High-volume, append-only logs, metrics, traces. Optimized for time-range queries, aggregations, trace traversal.
2. **Application State Storage** — Transactional, relational data: incidents, hypotheses, evidence refs, deployments, commits, evaluation records.

Technology choices must be driven by measured workload, not speculation.

## Decision

**Document current direction and the evidence/scale requirements that must be measured before committing to specific production services.**

### Current Direction (Not Commitment)

| Store | Direction | Rationale |
|-------|-----------|-----------|
| Telemetry | Columnar analytical DB (ClickHouse, TimescaleDB, or Apache Parquet on object store) | Time-series optimizations, compression, SQL interface |
| Application State | Relational DB (PostgreSQL) | ACID, complex relationships, mature tooling, JSON support |

### Required Measurements Before Commitment

#### Telemetry Store

| Metric | Measurement Method | Threshold for Decision |
|--------|-------------------|------------------------|
| Ingest throughput (events/sec) | Phase 1 demo app + load test | >50k eps sustained |
| Query latency (p99) | Representative queries (time-range, service filter, trace lookup) | <500ms p99 |
| Storage cost / TB / month | Projected 30-day retention | <$50/TB/mo |
| Compression ratio | Real telemetry sample | >5x |
| Operational complexity | Team assessment (setup, scaling, backup) | Runs on single node for dev |

#### Application State Store

| Metric | Measurement Method | Threshold for Decision |
|--------|-------------------|------------------------|
| Transaction throughput | Simulated investigation workload | >1k txn/sec |
| Query complexity | Join-heavy queries (incident → evidence → hypothesis) | <100ms p99 |
| JSON query performance | Evidence payload queries | <50ms p99 |
| Migration tooling maturity | Team assessment | Standard (Alembic, etc.) |

### Phase 1 Prototype

Phase 1 will prototype both with:
- **Telemetry:** ClickHouse (single node) + OTel Collector
- **Application State:** PostgreSQL (single node) + SQLAlchemy/Alembic

Measurements from Phase 1 will inform the final decision in an ADR update.

## Alternatives Considered (Not Ruled Out)

| Store | Alternatives | When They'd Win |
|-------|--------------|-----------------|
| Telemetry | TimescaleDB, Apache Druid, Loki+Tempo, Parquet/S3+Trino | If PostgreSQL-compatible preferred; if log-first; if serverless needed |
| Application State | SQLite (embedded), CockroachDB, FoundationDB | If embedded deployment needed; if global distribution needed |

## Trade-offs and Consequences

**Pros:**
- Avoids premature commitment to specific technology
- Phase 1 prototype provides real data
- Criteria are objective and measurable
- ADR provides audit trail for decision

**Cons:**
- Delays final architecture diagram
- Phase 1 prototype may need migration

## Validation / Reversal Criteria

- **Validate:** Phase 1 measurements meet thresholds; team consensus on choice
- **Reverse if:** Measurements show chosen direction fails thresholds; pivot to alternative with new ADR