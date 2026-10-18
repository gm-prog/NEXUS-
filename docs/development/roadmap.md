# NEXUS Development Roadmap

> **Status:** Phase 0 is the only implemented phase; Phase 1+ remain planned.
> [PR #1](https://github.com/gm-prog/NEXUS-/pull/1) is merged (2026-10-18); the
> merge SHA and the pre-merge/post-merge CI evidence are recorded in
> [Phase 0 Status](phase-0-status.md). Phase 1 requires separate authorization
> and is unstarted.

---

## Phase 0 — Foundation and Benchmark ✅ IMPLEMENTED

**Goal:** Establish greenfield foundation, architecture documentation, benchmark schemas, 20+ incident scenarios, validation CLI, automated tests, and CI.

**Prerequisites:** None (greenfield)

**Deliverables:**
- [x] Repository structure with Python packaging
- [x] Architecture documentation (7 docs)
- [x] Security documentation (threat model, permission model)
- [x] 14 ADRs recording key decisions and corrective trade-offs
- [x] JSON Schema for incident cases and evaluation results
- [x] 22 incident scenario fixtures (5 ambiguous/insufficient_evidence)
- [x] Validation CLI (`nexus-benchmark`)
- [x] Automated tests (pytest + schema validation)
- [x] Ruff linting/formatting
- [x] GitHub Actions CI

**Exit Criteria:**
- [x] All fixtures validate
- [x] Tests pass
- [x] CI passes
- [x] Minimum 20 cases with `max(5, ceil(total * 20%))` ambiguous/insufficient
- [x] Typed investigation-cutoff and evaluator-only resolution-time boundary
- [x] Evidence-backed INC-016/INC-019 semantic corrections and focused regressions (ADR-0014)
- [x] Committed dependency lock and enforced locked/hashed runtime/dev/build installs (ADR-0014)

---

## Phase 1 — Reproducible Demo Application and Telemetry 📋 PLANNED

**Goal:** Build a small instrumented application with fault injection to prove telemetry collection and correlation works locally.

**Prerequisites:** Phase 0 complete

**Deliverables:**
- [ ] Demo application: 3-4 services (API gateway, order, payment, inventory)
- [ ] OpenTelemetry instrumentation (traces, metrics, logs)
- [ ] OTel Collector configuration (local)
- [ ] Fault injection framework (chaos mesh or custom)
- [ ] Docker Compose for local stack
- [ ] Telemetry correlation proof-of-concept

**Services:**
1. **api-gateway** — Routes requests, rate limiting
2. **order-service** — Order creation, calls inventory + payment
3. **payment-service** — Payment processing, calls external gateway
4. **inventory-service** — Stock reservation, Kafka consumer
5. **notification-service** — Async email/WebSocket

**Fault Injection Scenarios (matching benchmarks):**
- Null pointer in payment (INC-001)
- DB pool exhaustion in order (INC-002)
- Slow query in user (INC-003)
- Redis outage (INC-004)
- Payment gateway timeout (INC-005)
- Config typo in gateway (INC-006)
- Memory leak in notification (INC-007)
- CPU recursion in analytics (INC-008)
- Queue backlog in email (INC-009)
- Kafka consumer crash (INC-010)

**Exit Criteria:**
- [ ] All services instrumented and emitting OTel
- [ ] Collector receives and exports to stdout/file
- [ ] Fault injection triggers all 10 scenarios
- [ ] Telemetry correlated manually (no AI yet)
- [ ] Local stack runs with `docker compose up`

---

## Phase 2 — Evidence Storage and Deterministic Correlation 📋 PLANNED

**Goal:** Persist telemetry and application state; implement deterministic correlation queries.

**Prerequisites:** Phase 1 demo app running locally

**Deliverables:**
- [ ] Telemetry storage (ClickHouse or TimescaleDB prototype)
- [ ] Application state store (PostgreSQL)
- [ ] Ingestion pipeline (OTLP → validation → normalization → storage)
- [ ] Deterministic intelligence module:
  - Time-window alignment
  - Deployment correlation
  - Service dependency lookups
  - Baseline calculations
  - Signal extraction (anomaly detection)
- [ ] Evidence bundle assembly API
- [ ] Query APIs for: logs, metrics, traces, deployments, commits

**Technology Decisions (to be made via ADR):**
- Telemetry store: ClickHouse vs TimescaleDB vs Parquet/S3
- Application state: PostgreSQL (confirmed direction)
- Query interface: SQL vs custom API

**Exit Criteria:**
- [ ] Ingestion pipeline processes demo app telemetry
- [ ] Deterministic queries return correct evidence bundles for all 10 fault scenarios
- [ ] Baselines compute correctly from 7-day windows
- [ ] Deployment correlation identifies trigger changes
- [ ] Performance: query p99 < 500ms for evidence bundle

---

## Phase 3 — Incident Detection and Initial UI 📋 PLANNED

**Goal:** Create deterministic incident candidates and expose investigation UI.

**Prerequisites:** Phase 2 storage and correlation working

**Deliverables:**
- [ ] Detection rules (threshold-based, rate-of-change, ML-free)
- [ ] Incident candidate generation and grouping/deduplication
- [ ] Incident lifecycle state machine (DETECTED → TRIAGED → ...)
- [ ] Web UI (React/TypeScript):
  - Incident timeline with correlated events
  - Service topology graph
  - Evidence cards with source links
  - Deployment comparison view
  - Investigation journal
- [ ] API for UI consumption

**Exit Criteria:**
- [ ] Detection catches all 10 fault scenarios as incidents
- [ ] UI shows correct timeline, topology, evidence for each
- [ ] Evidence links navigate to source (trace, log, commit, deployment)
- [ ] Deployment comparison shows diff for trigger changes

---

## Phase 4 — Read-Only AI Investigator 📋 PLANNED

**Goal:** Add a single controlled investigation workflow with read-only tools.

**Prerequisites:** Phase 3 UI and evidence bundle API working

**Deliverables:**
- [ ] Investigation agent framework (single workflow)
- [ ] Read-only tool set:
  - `query_logs(service, time_window, filter)`
  - `query_metrics(service, metric, time_window)`
  - `get_trace(trace_id)`
  - `get_deployment(deployment_id)`
  - `get_commit(commit_sha)`
  - `search_runbooks(query)`
  - `get_historical_incidents(similarity)`
  - `get_dependency_status(service)`
- [ ] Structured hypothesis generation
- [ ] Verification step execution
- [ ] Structured diagnosis output
- [ ] Full audit trail (AgentRun + ToolCall records)
- [ ] Budget enforcement (tokens, time, tool calls)

**Exit Criteria:**
- [ ] Agent investigates all 10 fault scenarios
- [ ] Produces structured diagnosis with evidence references
- [ ] All tool results validated against evidence
- [ ] No hallucinated evidence IDs
- [ ] Audit trail complete and replayable
- [ ] Benchmark evaluation runs on all 21 cases

---

## Phase 5 — Evidence-Backed Diagnosis, Repository Intelligence and Memory 📋 PLANNED

**Goal:** Enrich investigation with code intelligence, history, and uncertainty handling.

**Prerequisites:** Phase 4 investigator working

**Deliverables:**
- [ ] Code symbol extraction (LSIF/SCIP or ctags)
- [ ] Commit analysis (diff summarization, risk scoring)
- [ ] Runbook integration (matching, execution history)
- [ ] Historical incident retrieval (similarity search)
- [ ] Supporting/contradicting evidence explicit handling
- [ ] Uncertainty calibration (confidence scores, abstention)
- [ ] Memory: incident embeddings for future retrieval

**Exit Criteria:**
- [ ] Benchmark scores improve on Phase 4 baseline
- [ ] Ambiguous cases show appropriate uncertainty
- [ ] Code symbols linked in evidence
- [ ] Historical incidents retrieved for similar patterns

---

## Phase 6 — Evaluation Hardening 📋 PLANNED

**Goal:** Expand benchmarks, test model/prompt/tool changes, measure regressions.

**Prerequisites:** Phase 5 evaluation running

**Deliverables:**
- [ ] Expand to 50+ benchmark cases
- [ ] Add real-world/public benchmark cases (license-checked)
- [ ] Model/prompt/tool version comparison matrix
- [ ] Cost/latency tracking per run
- [ ] Regression detection automation
- [ ] Human evaluation protocol for prose quality

**Exit Criteria:**
- [ ] 50+ cases covering all categories
- [ ] Regression detection catches known degradations
- [ ] Cost/latency measured and tracked
- [ ] Human evaluation protocol documented

---

## Phase 7 — Sandboxed Remediation 📋 PLANNED

**Goal:** Generate patches in isolated environment, run tests/scans, human approval gate.

**Prerequisites:** Phase 5 diagnosis quality acceptable

**Deliverables:**
- [ ] Isolated sandbox (gVisor/Firecracker/container)
- [ ] Patch generation from diagnosis
- [ ] Test execution (unit, integration, contract)
- [ ] Security scans (SAST, SCA, secrets)
- [ ] Artifact storage (logs, coverage, SBOM)
- [ ] Human review UI (diff, test results, scan results)
- [ ] PR creation via Git provider API (scoped token)

**Exit Criteria:**
- [ ] Sandbox catches >90% regressions in benchmark remediation tasks
- [ ] Zero production incidents from NEXUS PRs in 6 months
- [ ] Human approval required for every PR
- [ ] Sandbox has no production network access

---

## Phase 8 — Git Provider Integration and Reliability Hardening 📋 PLANNED

**Goal:** Production-ready Git integration with auditability.

**Prerequisites:** Phase 7 sandbox working

**Deliverables:**
- [ ] GitHub App / GitLab integration (scoped permissions)
- [ ] Credential management (OIDC, short-lived tokens)
- [ ] Audit logging for all privileged actions
- [ ] Retry/timeout/failure isolation
- [ ] Operational monitoring (health checks, alerts)
- [ ] Multi-repo support

**Exit Criteria:**
- [ ] GitHub App installed and tested
- [ ] All write actions audited
- [ ] Failure scenarios handled gracefully
- [ ] Operational runbooks for NEXUS itself

---

## Phase 9 — Self-Observability and Advanced Capabilities 📋 PLANNED

**Goal:** NEXUS observes itself; advanced features only with evidence.

**Prerequisites:** Phase 8 production-ready

**Deliverables:**
- [ ] NEXUS instrumented with NEXUS (dogfooding)
- [ ] Incident memory maintenance (dedup, linking, aging)
- [ ] Predictive insights (only if evaluation justifies)
- [ ] Automated actions (only with human-in-loop, safety evidence)

**Exit Criteria:**
- [ ] NEXUS detects its own incidents
- [ ] Memory improves investigation over time
- [ ] Any predictive/automated feature has benchmark evidence

---

## Cross-Cutting Concerns

| Concern | Phase Addressed |
|---------|-----------------|
| Security | Phase 0 (design), Phase 1+ (implementation) |
| Multi-tenancy | Post-Phase 3 |
| Scaling | When metrics demand (ADR-0003) |
| Compliance | Phase 8+ |
| Internationalization | Not planned |

---

## Decision Gates

Each phase requires explicit go/no-go decision based on exit criteria. No phase starts without previous phase exit criteria met and documented.

**No schedule commitments.** Phases are sequential; timeline depends on evidence from previous phase.