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


## Phase 1 — Reproducible Demo Application and Telemetry (Phases 1A/1B) 📋 PLANNED

**Goal:** Build and instrument a deterministic local demo whose emitted evidence can be checked against the incident fixtures. Counts below refer to application services; mocks and infrastructure are counted separately.

**Prerequisites:** Phase 0 complete.

### Phase 1A — Minimal deterministic vertical slice

**Application services (4):** `api-gateway`, `checkout-service`, `order-service`, and `payment-service`, plus a **mock PayCo/payment gateway dependency** that is not counted as an application service.

**Scenario scope:** INC-001, INC-005, and INC-006 only.

- INC-001: preserve the fixture's `checkout-service` caller and `payment-service` fault-site roles.
- INC-005: model `checkout-service` calling mocked PayCo directly; do not insert `payment-service` into this fixture's causal path.
- INC-006: exercise the gateway configuration/rate-limit fault and its payment/checkout/order impact roles.

**Deliverables:**
- [ ] Deterministic trigger/reset interface with health checks.
- [ ] Fault-injection harness; the dedicated chaos-tool choice (e.g. Chaos Mesh versus a custom harness) remains open pending workload-based evidence.
- [ ] OpenTelemetry traces, metrics, and logs appropriate to each scenario.
- [ ] Local OTel Collector exporting to stdout/file only (**non-durable proof sink**).
- [ ] Deployment/configuration-change observations where fixture records exist.
- [ ] Docker Compose and repeatable demo/test-harness assertions.
- [ ] Fixture-to-demo mapping with preserved roles and limitations in [Testing Strategy](testing-strategy.md).

**Exit criteria:**
- [ ] The four application services and mock dependency start and reset reproducibly.
- [ ] INC-001/005/006 assertions observe their specified triggers, causal paths, and available evidence classes.
- [ ] Demo telemetry added beyond a fixture's evidence catalog is labelled as supplemental instrumentation.
- [ ] Collector output and assertion results can be inspected locally; no durable storage or AI is implied.

### Phase 1B — Full Phase 1 scenario topology

**Application-service roles (11):** `api-gateway`, `checkout-service`, `order-service`, `payment-service`, `user-service`, `auth-service`, `product-service`, `notification-service`, `analytics-service`, `email-service`, and `inventory-service`. This is the fixture-role union for INC-001…INC-010; it does not assert every role must be a separately deployed process if the mapping documents an adaptation. `notification-service` and `email-service` are distinct roles.

PostgreSQL, Redis, Kafka, queue backends, OOM/memory limits, and mock PayCo are infrastructure/dependencies, **not application services**. INC-002's inventory timeout source must be represented in the demo mapping, but the fixture gives it no separate `service_id`; do not invent one.

**Scenario scope:** all ten cases INC-001…INC-010 by the end of Phase 1B.

**Additional deliverables:**
- [ ] Telemetry prototype: single-node ClickHouse with OTel Collector and the ADR-0006 telemetry measurement battery.
- [ ] Application-state prototype: single-node PostgreSQL with SQLAlchemy/Alembic and the ADR-0006 transaction/query/JSON measurement battery.
- [ ] Record prototype measurements, load profile, commands, and limitations for the ADR-0006 follow-up decision; no production-final store is selected in Phase 1B.
- [ ] Add service roles and only the infrastructure required by the scenario mapping.
- [ ] Model Redis outage/failover, bounded PostgreSQL connection-pool/index changes, memory/OOM, analytics CPU/recursion, queue backlog, and Kafka consumer/poison-message behavior as applicable.
- [ ] Extend traces/metrics/logs/config/deployment evidence to match each mapping's stated signals.
- [ ] Keep fixture ground truth and IDs unchanged; mappings remain proposed until an actual demo run verifies the asserted signals.

**Phase 1 overall exit criteria (after 1A and 1B):**
- [ ] The full topology runs locally and can be reset deterministically.
- [ ] All ten INC-001…INC-010 scenarios are triggerable and pass mapped signal assertions.
- [ ] The Collector exports telemetry to the non-durable stdout/file proof sink.
- [ ] Evidence can be correlated manually for all ten scenarios; no AI investigator is required.
- [ ] A clean checkout can start the stack with the documented local command.
- [ ] The ADR-0006 prototype pair and planned measurement battery are complete and documented; results inform, but do not pre-decide, the Phase 2 storage decision.


## Phase 2 — Evidence Storage and Deterministic Correlation 📋 PLANNED

**Goal:** Operationalize durable telemetry/application-state storage and deterministic evidence correlation after Phase 1B prototypes have been measured.

**Prerequisites:** Phase 1B demo topology and mapped assertions pass. Phase 1A's stdout/file proof sink is non-durable, not an operational store.

**Deliverables:**
- [ ] Operational ingestion pipeline (OTLP → validation → normalization → storage).
- [ ] Telemetry storage/query path selected from measured prototype evidence; no store is final before ADR-0006's required measurements and ADR update.
- [ ] PostgreSQL application-state path with SQLAlchemy/Alembic, informed by Phase 1B prototype results.
- [ ] Deterministic intelligence: time-window alignment, deployment correlation, service-dependency lookups, baselines, and signal extraction.
- [ ] Evidence-bundle assembly API.
- [ ] Query APIs for logs, metrics, traces, deployments, commits, and scenario evidence.
- [ ] Record the final store decision through the ADR update required by accepted ADR-0006.

**Storage sequence required by ADR-0006:**
- **Phase 1A:** stdout/file proof sink only; non-durable.
- **Phase 1B:** measurement prototypes—single-node ClickHouse + OTel Collector for telemetry, and single-node PostgreSQL + SQLAlchemy/Alembic for application state. Exercise ADR-0006's measurement battery. These are prototypes, not final production commitments.
- **Phase 2:** operationalize the selected ingestion/storage/query/correlation path after reviewing measurements and updating the ADR.

**Technology decisions retained for measurement/ADR review:**
- Telemetry-store final choice remains open among ADR-0006's documented directions; ClickHouse is a Phase 1B prototype, not a production-final selection.
- PostgreSQL remains the application-state direction recorded by ADR-0006, subject to the accepted measurement criteria.
- Query interface (**SQL vs. custom API**) remains an explicit open decision until reviewed against the prototype and workload.

**Exit criteria:**
- [ ] Durable ingestion processes telemetry from all ten Phase 1 scenarios.
- [ ] Deterministic queries return correct evidence bundles for all ten cases.
- [ ] Baselines compute from documented seven-day windows.
- [ ] Correlation identifies supported local trigger changes while preserving external/system-initiated causes without a local change record.
- [ ] Evidence-bundle query p99 target is below 500 ms under documented test load.


## Phase 3 — Incident Detection and Initial UI 📋 PLANNED

**Goal:** Create deterministic incident candidates and expose evidence in an investigation UI.

**Prerequisites:** Phase 2 storage, ingestion, and correlation work for the complete Phase 1B scenario set.

**Deliverables:**
- [ ] Detection rules (threshold-based and rate-of-change; ML-free).
- [ ] Incident candidate generation and grouping/deduplication.
- [ ] Incident lifecycle state machine (DETECTED → TRIAGED → ...).
- [ ] Web UI (React/TypeScript):
  - Incident timeline with correlated events
  - Service topology graph
  - Evidence cards with source links
  - Deployment comparison view
  - Investigation journal
- [ ] API for UI consumption.

**Exit criteria:**
- [ ] Detection catches all ten Phase 1 scenarios as incident candidates.
- [ ] UI shows correctly mapped timelines, topology, and evidence for each case.
- [ ] Evidence links navigate to source records (trace, log, commit, deployment) where those records exist.
- [ ] Deployment comparison shows diffs for recorded trigger changes; externally initiated incidents remain representable without a local deployment.


## Phase 4 — Read-Only AI Investigator 📋 PLANNED

**Goal:** Add one controlled, auditable investigation workflow using read-only capabilities and a separately specified evaluation pipeline.

**Prerequisites:** Phase 3 UI/evidence-bundle API working and the ten Phase 1 scenarios mapped end-to-end.

**Fixture-required investigator tool candidates (planned, not implemented):**
Phase 0's `TOOL_REGISTRY` validates fixture metadata; it does **not** provide callable agent tools or runtime authorization. The following names are proposed read-only tools required by fixture checks:
- `query_logs`
- `query_metrics`
- `get_trace`
- `get_deployment`
- `get_commit`
- `get_dependency_status`
- `query_database` (read-only, allowlisted queries only)
- `get_config`
- `get_thread_dump`
- `inspect_queue`
- `inspect_kafka_message`

The previous draft's `search_runbooks` and `get_historical_incidents` are not registered in the Phase 0 tool registry. They remain future candidates only and must be specified, registered, side-effect-classified, and tested before any fixture or runtime use. No tool here is claimed to be implemented.

**Deliverables:**
- [ ] Controlled investigation workflow with validated tool schemas and fail-closed tool execution.
- [ ] Evidence validation, structured hypotheses/diagnosis, uncertainty/abstention behavior, and replayable audit trail.
- [ ] Budget enforcement (tokens, time, tool calls) and no hallucinated evidence IDs.
- [ ] **Evaluation-contract design checkpoint at Phase 4 entry.** Contract/scorer specification is a separate task requiring explicit authorization; this roadmap edit does not authorize Evaluation Contract v0.
- [ ] After the contract is separately authorized and defined, a runner/scorer that emits records conforming to `evaluation-result.schema.json`.
- [ ] Evaluate all current benchmark cases (22 at this baseline; inventory owned by [benchmarks/README.md](../../benchmarks/README.md)); retain result provenance and contract/evaluator version.
- [ ] Establish a versioned baseline only after an actual end-to-end evaluation run. No result files or baseline are implied by this plan.

**Exit criteria:**
- [ ] Read-only investigation covers all ten demo scenarios and produces evidence-linked structured diagnoses.
- [ ] Evaluation runs end-to-end on all current 22 cases, emits schema-conformant results, and records a versioned baseline with provenance.
- [ ] Scoring semantics and baseline provenance are documented before Phase 5 claims improvement.
- [ ] Agent-visible/evaluator-only data remain separated; fixture validation is not model-accuracy evidence.

## Phase 5 — Evidence-Backed Diagnosis, Repository Intelligence and Memory 📋 PLANNED

**Goal:** Enrich investigation with code intelligence, history, and uncertainty handling.

**Prerequisites:** Phase 4 investigator working and a versioned evaluation baseline established

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

**Goal:** Generate and verify patches in an isolated, non-production environment and produce a human-review package.

**Prerequisites:** Phase 5 diagnosis quality and evaluation gates are accepted; isolation and capability enforcement must be implemented and reviewed before mutation-capable runtime is enabled.

**Deliverables:**
- [ ] Isolated sandbox (gVisor/Firecracker/container decision remains open) with resource limits, restricted network, and no production/provider credentials.
- [ ] Patch generation limited to the sandbox workspace.
- [ ] Sandboxed tests and security scans (unit/integration/contract, SAST/SCA/secrets).
- [ ] Auditable artifacts: patch/diff, test/scan output, logs, coverage, and SBOM where applicable.
- [ ] Human-review package containing rationale, proposed diff, evidence, test results, and scan results.
- [ ] Local/fake Git-provider interface for acceptance tests; no live provider account, remote branch/push, or remote PR operation in Phase 7.

**Exit criteria:**
- [ ] Remediation regression-catch target (>90%) is evaluated against a versioned benchmark; this is a future target, not a measured result.
- [ ] Every proposed change requires human review; the sandbox has no production network access or credentials.
- [ ] Artifacts are reproducible and linked to diagnosis, patch, and test run.
- [ ] Phase 7 emits a PR-proposal package, not a remotely created PR.


## Phase 8 — Git Provider Integration and Reliability Hardening 📋 PLANNED

**Goal:** Add auditable remote Git-provider operations only after sandboxed remediation is independently safe.

**Prerequisites:** Phase 7 sandbox, review package, audit trail, and human-approval workflow pass their gates.

**Deliverables:**
- [ ] GitHub App / GitLab integration with least-privilege, repository-scoped permissions.
- [ ] Credential management (OIDC/JIT, short-lived tokens, rotation/revocation) and isolated provider access.
- [ ] Remote feature-branch creation and commit pushes to explicitly allowed **unprotected feature branches only**.
- [ ] Remote pull-request creation after explicit human approval.
- [ ] Audit logging for every privileged operation; retries, timeouts, failure isolation, health checks, and alerts.
- [ ] Multi-repo support only after single-repository controls are validated.

**Safety boundaries:** no production credentials in the sandbox; no agent capability to write protected branches, merge PRs, force-push, or bypass repository rules. Humans merge PRs through the provider's normal protection gates.

**Exit criteria:**
- [ ] Provider app and scoped permissions are installed and tested.
- [ ] Every remote write is audited and restricted to allowed feature branches.
- [ ] PR creation requires explicit human approval; merge remains human-controlled.
- [ ] Failure scenarios are handled safely and operational runbooks exist.

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