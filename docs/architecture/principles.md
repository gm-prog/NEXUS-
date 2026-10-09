# NEXUS Design Principles

Each principle includes its engineering consequence.

---

## 1. Evidence Before AI

**Principle:** Deterministic retrieval, correlation, and anomaly detection run before any model reasoning. The model receives a curated evidence bundle, not raw telemetry.

**Consequence:** The ingestion and intelligence layers are pure functions. No model call can bypass evidence validation. Investigation quality is bounded by evidence quality, not model capability.

---

## 2. Deterministic Systems Do Deterministic Work

**Principle:** Queries, time-window alignment, deployment correlation, service lookups, and baseline calculations are implemented as pure, testable functions. Models do not perform arithmetic, string matching, or temporal reasoning.

**Consequence:** These functions are unit-testable, reproducible, and auditable. They form the "calculator" the model uses — the model proposes *what to calculate*, the tool *calculates it exactly*.

---

## 3. AI Is for Interpretation and Adaptive Investigation, Not Replacing Reliable Queries

**Principle:** Models excel at synthesizing disparate evidence, proposing hypotheses, and selecting adaptive next steps. They do not replace SQL, time-series queries, or graph traversals.

**Consequence:** Tool interfaces expose precise, typed operations (e.g., `query_error_rate(service, window)`, `get_deployment_diff(sha1, sha2)`). The model calls tools; it does not re-implement them.

---

## 4. Conclusions Reference Evidence Records

**Principle:** Every claim in a diagnosis must link to one or more evidence records with stable IDs, source references, and retrieval timestamps.

**Consequence:** The diagnosis data structure requires `evidence_refs: string[]` for each claim. The backend validates that referenced evidence exists and matches the claimed values.

---

## 5. Supporting and Contradicting Evidence Are Both First-Class

**Principle:** Evidence that weakens a hypothesis is as important as evidence that supports it. Both are stored, surfaced, and scored.

**Consequence:** Evidence records have `role: "supporting" | "contradicting" | "neutral"`. Evaluation measures coverage of both. A diagnosis that ignores contradicting evidence scores poorly.

---

## 6. Distinguish Symptom, Contributing Factor, Trigger/Change, and Root Cause

**Principle:** Causal analysis uses a structured chain, not a flat label.

- **Symptom:** Observable deviation (error rate spike, latency p99 breach)
- **Contributing Factor:** Condition that amplified impact (low replica count, missing timeout)
- **Trigger/Change:** Proximate event that initiated the incident (deployment, config push, dependency outage)
- **Root Cause:** Underlying defect or design gap (missing null check, connection leak, unbounded queue)

**Consequence:** The diagnosis schema enforces this structure. Evaluation scores each link in the chain independently.

---

## 7. Express Uncertainty; Abstain When Evidence Is Insufficient

**Principle:** `unknown` or `insufficient_evidence` is a valid, scored conclusion. Forced certainty is penalized.

**Consequence:** Diagnosis includes `confidence: number` (0.0–1.0) and `uncertainty_rationale: string`. Benchmark cases include ambiguous/insufficient scenarios where the correct answer is "cannot determine."

---

## 8. Every Agent/Tool Action Will Be Auditable

**Principle:** Full investigation trace: hypothesis → tool call → parameters → result → updated belief. Replayable for debugging and evaluation.

**Consequence:** Agent runs persist `AgentRun` with ordered `ToolCall` records. Evaluation replays runs deterministically.

---

## 9. Read-Only Investigation Precedes Any Write-Capable Workflow

**Principle:** Phases 0–4 are strictly read-only. No production mutations, no code pushes, no shell access.

**Consequence:** Tool interfaces in early phases expose only `read` operations. Write capabilities (`branch.create`, `code.modify`, `execution.test`) are gated behind explicit phase gates and human approval.

---

## 10. Remediation Runs Outside Production and Is Human-Reviewable

**Principle:** Patch generation, test execution, and validation occur in an isolated environment. A human reviews artifacts before any PR is created.

**Consequence:** Remediation sandbox has no production network access. Output artifacts (diff, test logs, scan results) are stored for review. `pull_request.create` requires explicit human confirmation.

---

## 11. Prefer a Modular Monolith Until Independent Scaling, Ownership, or Failure Isolation Justifies Service Separation

**Principle:** Start with a single deployable unit with clear internal module boundaries. Split only when metrics (latency, throughput, team ownership, blast radius) demand it.

**Consequence:** Phase 1–3 build a modular monolith. Internal packages: `ingestion`, `storage`, `intelligence`, `investigation`, `evaluation`, `api`. Shared database with schema-per-module.

---

## 12. Add Infrastructure Only When an Identified Requirement Supports It

**Principle:** No Kafka, Kubernetes, vector database, graph database, or agent framework until a specific, measured workload requires it.

**Consequence:** Architecture documents note "PLANNED" for all infrastructure. ADRs record the criteria that must be met before adoption.

---

## 13. Evaluate Changes Against a Stable Benchmark Before Claiming Improvement

**Principle:** Frozen incident scenarios are the regression test for the investigation system. No accuracy claim without benchmark evidence.

**Consequence:** `benchmarks/incidents/` is the source of truth. `nexus-benchmark validate` enforces schema and composition rules. Evaluation runs produce versioned results for comparison.