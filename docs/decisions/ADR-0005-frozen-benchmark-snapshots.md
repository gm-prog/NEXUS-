# ADR-0005: Frozen Benchmark Snapshots

- Status: Accepted
- Date: 2024-01-15

## Context

Evaluation integrity requires that the investigator sees only information available at the incident cutoff time. Leaking future knowledge (ground truth, postmortem, fix commits) invalidates benchmark scores.

## Decision

**Frozen snapshot principle: The investigator receives only telemetry, code revisions, deployments, and documents available at the defined investigation cutoff.**

### Implementation

1. **Benchmark fixture structure** (`incident-case.schema.json`):
   - `evidence_catalog` — Agent-visible evidence specifications (what exists at cutoff)
   - `ground_truth` — Evaluator-only authoritative answer (root cause, ambiguity, etc.)
   - `incident_window` — Explicit cutoff timestamp

2. **Evaluator implementation** (future):
   - Loads `ground_truth` separately
   - Constructs agent input from `evidence_catalog` + `incident_window` only
   - Never passes `ground_truth` fields to agent
   - Compares agent output against `ground_truth` after run completes

3. **CI Enforcement** (Phase 0):
   - `nexus-benchmark validate` checks schema compliance
   - Future: Add check that `ground_truth` keys don't appear in `evidence_catalog` summaries

### Scenario Time Travel

Each scenario defines:
- `incident_window.start` / `incident_window.end` — When symptoms occurred
- `investigation_cutoff` — When investigation begins (typically `incident_window.end` + small buffer)
- Evidence in `evidence_catalog` must have `event_time` ≤ `investigation_cutoff`
- Deployments/commits after cutoff are excluded

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Single fixture with "agent_view" filter | Too easy to accidentally include ground truth in view |
| Runtime filtering in evaluator | Bug in filter leaks truth; static separation is safer |
| Separate files for ground truth | Harder to keep in sync; single file with clear separation is clearer |

## Trade-offs and Consequences

**Pros:**
- Guarantees no leakage by construction
- Clear mental model for fixture authors
- Evaluator implementation straightforward
- Benchmark scores reflect true investigative ability

**Cons:**
- Fixture authoring requires discipline (two mindsets: scenario designer vs. evaluator)
- `evidence_catalog` must be realistic (not "perfect evidence")

## Validation / Reversal Criteria

- **Validate:** Manual audit of 5 random fixtures confirms no ground truth in evidence catalog; evaluator integration test passes with mocked agent
- **Reverse if:** Fixture authoring becomes bottleneck; consider tooling to generate evidence_catalog from ground_truth + simulation