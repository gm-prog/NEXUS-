# ADR-0005: Frozen Benchmark Snapshots

- Status: Accepted
- Date: 2026-10-09

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
   - Uses `build_agent_view(case)`; never forwards the raw case/window
   - `incident_window.end` stays evaluator-only (ADR-0012)
   - Never passes `ground_truth` fields to agent
   - Compares agent output against `ground_truth` after run completes

3. **CI Enforcement** (Phase 0):
   - `nexus-benchmark validate` checks schema, tool policy, temporal cutoff and
     agent-view separation; injected-leak tests prove the boundary is non-vacuous
   - Arbitrary prose/causal realism still needs fixture-author review

### Scenario Time Travel

Each scenario defines:
- `incident_window.start` — Symptom onset, at/before the investigation cutoff
- `incident_window.end` — Evaluator-only resolution/observation completion
- `investigation_cutoff` — Frozen boundary when investigation begins; it may be
  **before** the eventual incident end (all 21 original cases do this)
- Evidence event **and collection** times and both optional interval endpoints
  must be at/before cutoff. Future records/changes are rejected, not filtered
- All typed time comparisons use timezone-aware RFC 3339 instants in UTC

The earlier "end + small buffer" example contradicted the in-flight fixtures.
[ADR-0012](ADR-0012-temporal-cutoff-integrity.md) clarifies the boundary and the
validator/projection checks without changing original synthetic timestamps.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Single fixture with "agent_view" filter | Too easy to accidentally include ground truth in view |
| Runtime filtering in evaluator | Bug in filter leaks truth; static separation is safer |
| Separate files for ground truth | Harder to keep in sync; single file with clear separation is clearer |

## Trade-offs and Consequences

**Pros:**
- Enforces a tested field/typed-time boundary; opaque prose still needs review
- Clear mental model for fixture authors
- Evaluator implementation straightforward
- Designed to prevent future/answer metadata from contaminating future scores

**Cons:**
- Fixture authoring requires discipline (two mindsets: scenario designer vs. evaluator)
- `evidence_catalog` must be realistic (not "perfect evidence")

## Validation / Reversal Criteria

- **Validate:** All current fixtures pass typed-time and allowlist checks;
  negative temporal/injected-leak tests fail closed. A future real evaluator
  must retain that boundary; no evaluator accuracy has been measured in Phase 0
- **Reverse if:** Fixture authoring becomes bottleneck; consider tooling to generate evidence_catalog from ground_truth + simulation