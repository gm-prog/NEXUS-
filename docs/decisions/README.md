# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for NEXUS.

## ADR Template

```markdown
# ADR-NNNN: Title

- Status: Proposed | Accepted | Superseded
- Date: YYYY-MM-DD

## Context

## Decision

## Alternatives Considered

## Trade-offs and Consequences

## Validation / Reversal Criteria
```

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](ADR-0001-evidence-first-architecture.md) | Evidence-First Architecture | Accepted | 2026-10-09 |
| [ADR-0002](ADR-0002-benchmark-format.md) | Benchmark Format: JSON Schema | Accepted | 2026-10-09 |
| [ADR-0003](ADR-0003-modular-monolith-first.md) | Modular Monolith First | Accepted | 2026-10-09 |
| [ADR-0004](ADR-0004-read-only-investigation.md) | Read-Only Investigation & Isolated Remediation | Accepted | 2026-10-09 |
| [ADR-0005](ADR-0005-frozen-benchmark-snapshots.md) | Frozen Benchmark Snapshots | Accepted | 2026-10-09 |
| [ADR-0006](ADR-0006-telemetry-state-store-criteria.md) | Telemetry & State Store Decision Criteria | Accepted | 2026-10-09 |
| [ADR-0007](ADR-0007-product-naming.md) | Product Naming & Positioning | Accepted | 2026-10-09 |
| [ADR-0008](ADR-0008-benchmark-identifier-contract.md) | Benchmark Identifier Contract: Stable Slugs, Not UUIDs | Accepted | 2026-10-10 |
| [ADR-0009](ADR-0009-verification-step-execution-classes.md) | Execution Classification for Benchmark Verification Steps | Accepted | 2026-10-10 |
| [ADR-0010](ADR-0010-agent-view-projection.md) | Allowlisted Agent-View Projection for Benchmark Cases | Accepted | 2026-10-10 |
| [ADR-0011](ADR-0011-benchmark-assets-in-the-distribution.md) | Benchmark Assets Ship Inside the Distribution | Accepted | 2026-10-10 |
| [ADR-0012](ADR-0012-temporal-cutoff-integrity.md) | Fail-Closed Temporal Cutoff Integrity | Accepted | 2026-10-10 |
| [ADR-0013](ADR-0013-observed-incident-target.md) | Score the Observed Incident, Not a Hypothetical Latent Defect | Accepted | 2026-10-10 |

## When to Create an ADR

Create an ADR when:
- Adding/removing a major dependency or infrastructure component
- Changing the benchmark schema version
- Changing the CLI interface or output format
- Introducing a new evaluation metric
- Changing the incident lifecycle or evidence model
- Any decision with significant trade-offs or future impact