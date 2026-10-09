# ADR-0001: Evidence-First Architecture

- Status: Accepted
- Date: 2024-01-15

## Context

NEXUS must produce trustworthy incident investigations. The industry pattern of "throw logs at an LLM and hope for a root cause" fails because:
- Models hallucinate causal links
- Models cannot reliably perform temporal reasoning or arithmetic
- Evidence provenance is lost
- Contradicting evidence is ignored
- Results are not reproducible or auditable

## Decision

**Deterministic evidence retrieval, correlation, and anomaly detection run before any model reasoning.**

Architecture layers:
1. **Ingestion/Normalization** — Validate, enrich, store raw telemetry and state events
2. **Deterministic Evidence Intelligence** — Pure functions for time-window alignment, deployment correlation, service lookups, baseline calculations, signal extraction
3. **Investigation** — Model receives curated evidence bundle; proposes hypotheses; calls verified read-only tools; produces diagnosis with evidence references

The model never sees raw telemetry. It sees structured evidence: "Error rate increased 300% (evidence ID: ev-123)", "Deployment abc123 changed PaymentService.charge() (evidence ID: ev-456)".

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| RAG over raw logs | No temporal reasoning, hallucinated correlations, no provenance |
| Model-only with tools | Tools become "calculators" but model still drives query logic; hard to audit |
| Fine-tuned model for root cause | Black box; cannot validate evidence references; no uncertainty calibration |

## Trade-offs and Consequences

**Pros:**
- Investigations are reproducible (same evidence → same deterministic results)
- Evidence provenance preserved end-to-end
- Model scope reduced to interpretation → fewer hallucinations
- Deterministic layer unit-testable and benchmarkable
- Clear audit trail: evidence → hypothesis → verification → diagnosis

**Cons:**
- More upfront engineering (deterministic layer before AI)
- Evidence bundle quality bounds investigation quality
- Requires schema discipline for evidence records

## Validation / Reversal Criteria

- **Validate:** Phase 4 investigation agent achieves >80% root-cause accuracy on benchmark using only deterministic evidence bundle (no raw telemetry access)
- **Reverse if:** Deterministic layer cannot be built for a critical signal type within 2 sprints, forcing model to reason over raw data