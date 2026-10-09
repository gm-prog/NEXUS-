# NEXUS Data Flow

> **Status:** Conceptual design for Phase 1+. Not implemented in Phase 0.

---

## End-to-End Data Flow

```
Application / Git / CI
        ↓
Collection and Ingestion
        ↓
Validation and Normalization
        ↓
Enrichment and Storage
        ↓
Deterministic Anomaly Detection / Incident Trigger
        ↓
Evidence Bundle and Correlation
        ↓
Bounded AI Investigation
        ↓
Evidence-Backed Diagnosis or Explicit Uncertainty
        ↓
Human-Reviewed Remediation Proposal
        ↓
Future Sandbox Validation
        ↓
Human-Reviewed Pull Request
```

---

## Boundary Specifications

### 1. Application / Git / CI → Collection and Ingestion

| Aspect | Detail |
|--------|--------|
| **Inputs** | OTLP traces/metrics/logs (gRPC/HTTP), Git webhooks (push, PR, merge), CI webhooks (deployment, build) |
| **Outputs** | Validated, normalized events to ingestion pipeline |
| **Owner** | Platform/Observability team |
| **Guarantees** | At-least-once delivery, schema validation, timestamp normalization to UTC |
| **Failure Modes** | Schema rejection (dead letter), enrichment lookup failure (retry with backoff), backpressure (buffer/spill) |

### 2. Collection and Ingestion → Validation and Normalization

| Aspect | Detail |
|--------|--------|
| **Inputs** | Raw events from collectors/webhooks |
| **Outputs** | Normalized events with canonical field names, types, UTC timestamps |
| **Owner** | Platform/Observability team |
| **Guarantees** | Idempotent processing (dedup by event ID), field mapping rules versioned |
| **Failure Modes** | Unmappable fields (quarantine), timestamp parse errors (reject), enrichment service unavailable (cache/retry) |

### 3. Validation and Normalization → Enrichment and Storage

| Aspect | Detail |
|--------|--------|
| **Inputs** | Normalized events |
| **Outputs** | Events written to Telemetry Storage + Application State |
| **Owner** | Platform/Observability team |
| **Guarantees** | Telemetry: append-only, time-partitioned. Application state: transactional, consistent |
| **Failure Modes** | Telemetry write failure (buffer/retry), Application state conflict (retry with backoff), partition imbalance (rebalance) |

### 4. Enrichment and Storage → Deterministic Anomaly Detection / Incident Trigger

| Aspect | Detail |
|--------|--------|
| **Inputs** | Telemetry streams + application state (deployments, services, dependencies) |
| **Outputs** | Incident candidates (DETECTED state) with initial evidence bundle |
| **Owner** | Detection/Intelligence team |
| **Guarantees** | Deterministic rules (pure functions), no model inference, configurable thresholds |
| **Failure Modes** | Rule misfire (false positive), rule miss (false negative), baseline insufficient (degraded mode) |

### 5. Deterministic Anomaly Detection → Evidence Bundle and Correlation

| Aspect | Detail |
|--------|--------|
| **Inputs** | Incident candidate + time window + affected services |
| **Outputs** | Structured evidence bundle: metrics, logs, traces, deployments, commits, runbooks, historical incidents, baselines, dependency status |
| **Owner** | Intelligence/Investigation team |
| **Guarantees** | Complete within SLA (e.g., 30s), all references resolvable, no ground-truth leakage |
| **Failure Modes** | Partial evidence (degraded storage), reference resolution timeout, evidence gap (insufficient coverage) |

### 6. Evidence Bundle → Bounded AI Investigation

| Aspect | Detail |
|--------|--------|
| **Inputs** | Evidence bundle + incident context (service, environment, window, symptoms) |
| **Outputs** | Structured investigation trace: hypotheses, tool calls, verifications, final diagnosis |
| **Owner** | AI/Investigation team |
| **Guarantees** | Tool results validated, evidence refs verified, budget enforced (tokens, time, tool calls), full audit trail |
| **Failure Modes** | Model hallucination (caught by evidence validation), tool error (retry/fallback), budget exceeded (abort with partial result), loop detection (max iterations) |

### 7. Bounded AI Investigation → Evidence-Backed Diagnosis or Explicit Uncertainty

| Aspect | Detail |
|--------|--------|
| **Inputs** | Investigation trace |
| **Outputs** | Diagnosis record (IDENTIFIED) or FAILED/ABORTED with uncertainty rationale |
| **Owner** | AI/Investigation team |
| **Guarantees** | Diagnosis schema enforced, all claims reference evidence, confidence calibrated, contradicting evidence acknowledged |
| **Failure Modes** | Insufficient evidence → explicit `unknown` with rationale, contradicting evidence ignored → low score, hallucinated evidence → validation failure |

### 8. Diagnosis → Human-Reviewed Remediation Proposal

| Aspect | Detail |
|--------|--------|
| **Inputs** | Diagnosis + incident context |
| **Outputs** | RemediationProposal (code/config/infra changes, test plan, risk assessment, rollback plan) |
| **Owner** | Engineering team (human) |
| **Guarantees** | Human review required, proposal linked to diagnosis, test plan specified |
| **Failure Modes** | No viable remediation (e.g., third-party outage), proposal rejected, risk too high |

### 9. Remediation Proposal → Future Sandbox Validation

| Aspect | Detail |
|--------|--------|
| **Inputs** | Approved RemediationProposal |
| **Outputs** | RemediationAttempt with test results, scan results, artifacts |
| **Owner** | Automation/Platform team |
| **Guarantees** | Isolated execution (no production network), deterministic test runs, artifact persistence |
| **Failure Modes** | Sandbox provisioning failure, test flakiness, scan false positives, resource limits |

### 10. Sandbox Validation → Human-Reviewed Pull Request

| Aspect | Detail |
|--------|--------|
| **Inputs** | Successful RemediationAttempt |
| **Outputs** | Pull request with diff, test logs, scan results, approval trail |
| **Owner** | Engineering team (human) |
| **Guarantees** | Human approval gate, PR linked to incident, audit trail complete |
| **Failure Modes** | Human rejects, merge conflict, post-merge regression |

---

## Data Contracts at Boundaries

Each boundary has a defined schema (JSON Schema / OpenAPI) validated in CI. Schemas versioned explicitly. Backward compatibility required within major version.

---

## Failure Mode Taxonomy

| Category | Examples | Mitigation |
|----------|----------|------------|
| **Data Quality** | Missing telemetry, schema drift, clock skew | Validation at ingestion, schema registry, NTP enforcement |
| **Detection** | False positive, false negative, alert storm | Rule testing against benchmarks, adaptive baselines, grouping/dedup |
| **Correlation** | Incomplete evidence, wrong time window, missing dependency | Evidence completeness checks, configurable windows, dependency graph validation |
| **Investigation** | Hallucination, tool misuse, budget exhaustion | Evidence validation, tool schemas, strict budgets, loop detection |
| **Remediation** | Sandbox escape, test flake, scan false positive | Network isolation, test retry, scan allowlist, human gate |
| **Operational** | Deployment failure, credential expiry, capacity exhaustion | Health checks, rotation automation, autoscaling, runbooks |

---

## Phase 0 Scope

Only the **benchmark data contracts** (incident case schema, evaluation result schema) are implemented in Phase 0. All pipeline components above are **PLANNED**.