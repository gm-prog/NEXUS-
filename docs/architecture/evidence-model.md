# NEXUS Evidence Model

> **Status:** Conceptual design for Phase 1+. Not implemented in Phase 0.

---

## Core Definitions

### Observation
A captured or computed fact. Examples:
- A metric sample: `http_requests_total{service="api",status="500"} = 42` at `2024-01-15T10:30:00Z`
- A log line: `ERROR: connection pool exhausted` at `2024-01-15T10:30:05Z`
- A computed baseline: `p99_latency_baseline(api, 7d) = 145ms`

Observations are raw or derived but have no incident context yet.

### Evidence
An observation or artifact **relevant to an incident**, with a retrievable source reference.

**Evidence = Observation + Incident Context + Source Reference**

Key properties:
- Stable evidence ID (UUID)
- Evidence type (metric, log, trace, deployment, commit, runbook, historical_incident, configuration, dependency_status, baseline, verification_result)
- Source (telemetry_storage, application_state, git_provider, ci_system, runbook_store, manual)
- Source reference (query ID, trace ID, commit SHA, URL, runbook ID, etc.)
- Event/observation time (when the fact occurred)
- Collection time (when evidence was retrieved/recorded)
- Time window (for aggregated evidence)
- Service/environment identifiers
- Human-readable summary
- Query/source reference (how to reproduce retrieval)
- Data provenance (direct_observation, derived_calculation, model_inference, manual_entry)
- Integrity status (verified, unverified, corrupted, partial)
- Availability status (available, partial, missing, access_denied)

### Signal
A derived indication suggesting a potential issue. Examples:
- Error-rate growth: `error_rate(api) increased 300% over 5m`
- Latency anomaly: `p99_latency(api) > 3 * baseline`
- Throughput drop: `request_rate(api) < 0.1 * baseline`
- Saturation indicator: `cpu_usage(api) > 90% for 10m`

Signals are **derived from observations** via deterministic rules. They are not evidence until linked to an incident with context.

### Hypothesis
A falsifiable proposed explanation for an incident.

Structure:
- Title & description
- Causal chain (ordered links: trigger → mechanism → symptom → impact)
- Supporting evidence IDs
- Contradicting evidence IDs
- Required verification steps (each with tool, parameters, expected outcomes)
- Status (proposed, investigating, supported, contradicted, rejected, confirmed)
- Confidence (0.0–1.0)

### Claim
A statement in the diagnosis that should be supported by evidence.

Examples:
- "Deployment `abc123` introduced a null-pointer dereference in `PaymentService.charge()`"
- "Redis connection pool was exhausted due to missing `close()` in error path"
- "Third-party payment provider `payco` returned 503 for 15 minutes"

Every claim must reference evidence IDs. The backend validates references.

### Verification
A check designed to support, weaken, or falsify a hypothesis.

Structure:
- Description
- Tool name + parameters
- Expected outcome if hypothesis is true
- Expected outcome if hypothesis is false
- Status (pending, executed, passed, failed, inconclusive)
- Result evidence ID (if executed)

### Causal Chain
Ordered proposed links between:
1. **Trigger** — proximate event (deployment, config change, dependency outage, traffic spike)
2. **Mechanism** — how the trigger caused the failure (code path, resource exhaustion, cascade)
3. **Symptom** — observable deviation (errors, latency, unavailability)
4. **Impact** — user/business effect (checkout failing, data loss, SLA breach)

Each link has evidence IDs and confidence.

---

## Evidence Record Schema (Conceptual)

```json
{
  "id": "uuid",
  "incident_id": "uuid",
  "evidence_type": "metric|log|trace|deployment|commit|runbook|historical_incident|configuration|dependency_status|baseline|verification_result",
  "source": "telemetry_storage|application_state|git_provider|ci_system|runbook_store|manual",
  "source_reference": "string",
  "event_time": "2024-01-15T10:30:00Z",
  "collection_time": "2024-01-15T10:35:00Z",
  "time_window_start": "2024-01-15T10:25:00Z",
  "time_window_end": "2024-01-15T10:35:00Z",
  "service_id": "uuid",
  "environment_id": "uuid",
  "summary": "Error rate for api-service increased from 0.1% to 12% over 5 minutes",
  "query_reference": "SELECT quantile(0.99)(duration) FROM traces WHERE service='api' AND timestamp BETWEEN ...",
  "data_provenance": "direct_observation|derived_calculation|model_inference|manual_entry",
  "integrity_status": "verified|unverified|corrupted|partial",
  "availability_status": "available|partial|missing|access_denied",
  "raw_data_ref": "s3://bucket/evidence/uuid.json"
}
```

---

## Confidence vs. Reliability

**Observation reliability** ≠ **Causal inference strength**.

- A metric sample may have high reliability (direct from instrumentation) but low causal relevance.
- A model-inferred causal link may have low reliability (model uncertainty) even if observations are solid.
- Evidence records track **both**:
  - `integrity_status` / `availability_status` → observation reliability
  - `confidence` on `CausalLink` → inference strength

**Rule:** Confidence is never automatically `1.0` merely because a record exists.

---

## Model-Generated Claims: Validation Rules

1. **No invented evidence IDs** — Every `evidence_ref` in a model claim must exist in the evidence bundle.
2. **No paraphrasing as strengthening** — A claim cannot state "the error rate *doubled*" if the evidence says "increased from 1% to 1.5%".
3. **Backend validates references and values** — Before accepting a diagnosis, the system checks:
   - All referenced evidence IDs exist
   - Claimed numeric values match evidence within tolerance
   - Causal links reference valid evidence
   - Contradicting evidence is acknowledged
4. **Uncertainty is explicit** — Claims without sufficient evidence must use `insufficient_evidence` or `unknown` with rationale.

---

## Evidence Categories for Benchmark Scenarios

| Category | Examples |
|----------|----------|
| **Metric** | Error rate, latency percentiles, throughput, saturation (CPU, memory, connections), queue depth |
| **Log** | Error messages, stack traces, timeout warnings, circuit breaker events, configuration logs |
| **Trace** | Span errors, latency breakdown, downstream call failures, retry counts |
| **Deployment** | Version deployed, config diff, feature flag changes, rollback events |
| **Commit** | Code changes in relevant files, authors, linked PR, review comments |
| **Runbook** | Applicable procedures, past execution history, owner contacts |
| **Historical Incident** | Similar past incidents, resolutions, root causes |
| **Configuration** | Feature flag values, config maps, secrets (redacted), environment variables |
| **Dependency Status** | Upstream health checks, circuit breaker state, rate limit headers |
| **Baseline** | 7-day/30-day baselines for key metrics, seasonal patterns |
| **Verification Result** | Output of a hypothesis test (e.g., "canary shows 0% error rate") |

---

## Separation: Ground Truth vs. Agent-Visible Evidence

**Critical for benchmark integrity.**

- **Ground Truth (Evaluator-only):** The authoritative answer for a synthetic scenario. Includes root cause, trigger change, full causal chain, ambiguity designation. **Never passed to the agent.**
- **Agent-Visible Evidence Bundle:** The observations, signals, deployments, commits, runbooks, and historical incidents that would be available at the investigation cutoff time. **No ground truth fields.**

The benchmark schema enforces this separation via distinct top-level objects: `ground_truth` (evaluator-only) and `evidence_catalog` (agent-visible specifications). The evaluator compares the agent's output against `ground_truth`; the agent never sees it.