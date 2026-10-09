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
| [ADR-0001](ADR-0001-evidence-first-architecture.md) | Evidence-First Architecture | Accepted | 2024-01-15 |
| [ADR-0002](ADR-0002-benchmark-format.md) | Benchmark Format: JSON Schema | Accepted | 2024-01-15 |
| [ADR-0003](ADR-0003-modular-monolith-first.md) | Modular Monolith First | Accepted | 2024-01-15 |
| [ADR-0004](ADR-0004-read-only-investigation.md) | Read-Only Investigation & Isolated Remediation | Accepted | 2024-01-15 |
| [ADR-0005](ADR-0005-frozen-benchmark-snapshots.md) | Frozen Benchmark Snapshots | Accepted | 2024-01-15 |
| [ADR-0006](ADR-0006-telemetry-state-store-criteria.md) | Telemetry & State Store Decision Criteria | Accepted | 2024-01-15 |
| [ADR-0007](ADR-0007-product-naming.md) | Product Naming & Positioning | Accepted | 2024-01-15 |

## When to Create an ADR

Create an ADR when:
- Adding/removing a major dependency or infrastructure component
- Changing the benchmark schema version
- Changing the CLI interface or output format
- Introducing a new evaluation metric
- Changing the incident lifecycle or evidence model
- Any decision with significant trade-offs or future impact