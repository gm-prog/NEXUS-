# NEXUS Phase 0 Status

> **Status:** COMPLETE — Phase 0 deliverables implemented and verified by an
> executed corrective pass on 2026-10-10.
>
> This file records **only checks that were actually run**. Local results and
> hosted GitHub Actions results are listed separately. Nothing here is claimed
> as verified unless the command was executed and its output inspected.

---

## Objective

Establish a trustworthy engineering foundation and executable benchmark before
implementing telemetry ingestion or AI investigation.

---

## Corrective Pass (2026-10-10)

An independent audit of `master` @ `f1e8f94` returned NO-GO for Phase 1. This
section maps every finding to its fix.

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 1 | CI triggered on `main`; the repository's only branch is `master`, so Actions reported zero runs | P1 | `.github/workflows/ci.yml` now triggers on `push`/`pull_request` against `master`, plus `workflow_dispatch` |
| 2 | `[project.scripts]` targeted `nexus_benchmarks.cli:main`, which did not exist | P1 | `main()` added in `src/nexus_benchmarks/cli.py`; smoke tests invoke the installed executable (`--help`, `list`, `validate`) |
| 3 | Schema declared `format: "uuid"` for slug IDs; no `FormatChecker`, so no format was enforced | P1 | Slug patterns in `$defs` (`svc-…`, `env-…`), `FormatChecker` enabled everywhere, `rfc3339-validator` added as a runtime dependency, negative tests for malformed timestamps and UUID-shaped IDs |
| 4 | Ground-truth leakage tests were vacuous (field-name substring check; a loop body of `pass`) | P1 | Allowlisted agent-view projection (`src/nexus_benchmarks/agent_view.py`) that fails closed; `tests/test_agent_view.py` proves injection is detected |
| 5 | `required_checks` modelled mutating actions as ordinary read-only checks | P1 | Every check declares `execution_class`, `target_environment`, `mutates_state`, `automated_execution_allowed`; policy enforced by schema `allOf` and `execution_policy.py`; INC-013/015/017/019 rewritten |
| 6 | `ruff check .` failed with 71 errors (never run by CI) | P1/P2 | All fixed in code/tests; `lint.ignore` is still `[]` — no rule was weakened |
| 7 | Ambiguity invariant used a fixed count of 5 | P2 | `required_ambiguous_cases(total) = max(5, ceil(total × 0.20))`; regression tests with a 60-case synthetic suite |
| 8 | SECURITY.md claimed pinned dependencies; no lockfile exists | P2 | Documentation corrected; lockfile recorded as a tracked Phase 1 follow-up (not silently added) |
| 9 | ADR and sign-off dates said 2024-01-15 for a 2026-10-09 initial commit | P2 | ADRs re-dated to 2026-10-09; intentionally synthetic scenario timestamps left untouched |
| 10 | CLI located fixtures by walking to the repository root, so a built wheel could not find them | P2 | `benchmarks/` shipped as package data (hatchling `force-include`), layered resolution in `assets.py`, `scripts/wheel_smoke_test.sh` verifies the installed wheel outside the checkout |

New decisions are recorded as [ADR-0008](../decisions/ADR-0008-benchmark-identifier-contract.md),
[ADR-0009](../decisions/ADR-0009-verification-step-execution-classes.md),
[ADR-0010](../decisions/ADR-0010-agent-view-projection.md) and
[ADR-0011](../decisions/ADR-0011-benchmark-assets-in-the-distribution.md).

---

## Implemented Items

### Repository Foundation
- [x] Python 3.11+ project with `pyproject.toml`
- [x] Ruff for linting/formatting (`lint.ignore = []` — no rules suppressed)
- [x] Pytest for testing (113 tests)
- [x] GitHub Actions CI triggering on `master`
- [x] MIT `LICENSE` (was referenced by the README but missing)
- [x] `.gitignore` with secrets, env, caches excluded

### Documentation
- [x] `README.md` — Project overview, architecture diagram, quick start, status table
- [x] `CONTRIBUTING.md` — Dev environment, checks, conventions, ADR process, dependency policy
- [x] `SECURITY.md` — Policy, threat model link, permission model link, accurate supply-chain statement
- [x] `docs/architecture/system-architecture.md` — 9-component architecture with Mermaid diagram
- [x] `docs/architecture/principles.md` — 13 principles with engineering consequences
- [x] `docs/architecture/domain-model.md` — 23 entities with relationships
- [x] `docs/architecture/evidence-model.md` — 7 core definitions, evidence schema, confidence rules
- [x] `docs/architecture/incident-lifecycle.md` — 10 states, transitions, investigation≠resolved
- [x] `docs/architecture/data-flow.md` — 10 boundaries with inputs/outputs/guarantees/failures
- [x] `docs/architecture/schema-strategy.md` — JSON Schema rationale, versioning, future evolution
- [x] `docs/security/threat-model.md` — 11 threat categories, trust boundaries, phase requirements
- [x] `docs/security/permission-model.md` — 14 capabilities, 3 risk tiers, authorization principles
- [x] `docs/decisions/README.md` — ADR template and index
- [x] `docs/decisions/ADR-0001` … `ADR-0011`
- [x] `docs/development/testing-strategy.md`
- [x] `docs/development/roadmap.md`
- [x] `docs/development/phase-0-status.md` (this file)
- [x] `benchmarks/README.md` — Benchmark structure, categories, separation rules

### Benchmark Schemas
- [x] `benchmarks/schema/incident-case.schema.json` — Draft 2020-12, slug identifier contract, execution classes for verification steps
- [x] `benchmarks/schema/evaluation-result.schema.json` — 25+ metrics, Draft 2020-12, slug service IDs

### Incident Scenarios (21 total)
| ID | Title | Category | Type | Difficulty |
|----|-------|----------|------|------------|
| INC-001 | Null Pointer in Payment | unhandled_exception | single_cause | easy |
| INC-002 | DB Pool Exhaustion | connection_pool_exhaustion | single_cause | medium |
| INC-003 | Slow Query (Index Drop) | slow_query | single_cause | medium |
| INC-004 | Redis Outage → Cache Storm | redis_outage | single_cause | medium |
| INC-005 | Payment Gateway Timeout | downstream_timeout | single_cause | easy |
| INC-006 | Config Typo (Rate Limit) | http_5xx_burst | single_cause | easy |
| INC-007 | Memory Leak (WebSocket) | memory_leak | single_cause | medium |
| INC-008 | CPU Saturation (Recursion) | cpu_saturation | single_cause | medium |
| INC-009 | Queue Backlog (Email) | queue_backlog | single_cause | medium |
| INC-010 | Kafka Consumer Crash | consumer_crash | single_cause | medium |
| INC-011 | Faulty Deployment (Ranking) | faulty_deployment | single_cause | medium |
| INC-012 | Config Drift (Feature Flag) | config_drift | single_cause | medium |
| INC-013 | Flag + Dependency Simultaneous | feature_flag_regression | **ambiguous** | hard |
| INC-014 | CDN Outage (No Local Change) | dependency_regression | **insufficient_evidence** | hard |
| INC-015 | Circular Dependency (Payment↔Order) | cascading_failure | **ambiguous** | hard |
| INC-016 | Broken Instrumentation (False Alert) | http_5xx_burst | **insufficient_evidence** | hard |
| INC-017 | Cache Stampede vs DB Lock | cache_stampede | **ambiguous** | expert |
| INC-018 | API Schema Mismatch | schema_mismatch | single_cause | medium |
| INC-019 | DB Lock Contention (Ad-hoc Query) | db_lock_contention | single_cause | medium |
| INC-020 | FD Exhaustion (Gateway) | resource_exhaustion | single_cause | medium |
| INC-021 | Cascading Failure (Auth Disk) | cascading_failure | multi_factor | expert |

**Ambiguous/Insufficient-Evidence Count:** 5 of 21 (23.8%). The requirement is
enforced as `max(5, ceil(total × 0.20))`, so it cannot degrade as the suite
grows.

### Validation CLI
- [x] `nexus-benchmark validate` — All cases
- [x] `nexus-benchmark validate --case INC-XXX` — Single case
- [x] `nexus-benchmark list` — Deterministic listing
- [x] Schema meta-validation
- [x] Cross-file invariants (unique IDs, counts, ambiguity **ratio**)
- [x] `date-time` / `uuid` format checking (via `FormatChecker`)
- [x] Verification-step execution policy
- [x] Agent-view / ground-truth separation on every case
- [x] Explicit output: "does NOT evaluate AI diagnosis quality"

### Automated Tests (113)
- [x] `tests/test_schema_validation.py` — schema loading, fixture validation, format negative tests, composition
- [x] `tests/test_ambiguity_coverage.py` — ratio invariant, regression at 60 cases
- [x] `tests/test_agent_view.py` — allowlist boundary, fail-closed behaviour, injected-leak detection
- [x] `tests/test_execution_policy.py` — every execution-class invariant, positive and negative
- [x] `tests/test_cli.py` — CliRunner coverage plus installed-executable smoke tests

---

## Deferred Items (Explicitly Out of Scope)

| Item | Phase |
|------|-------|
| Frontend / Dashboard | Phase 3 |
| Backend API Server | Phase 3 |
| Telemetry Ingestion Pipeline | Phase 1 |
| OpenTelemetry Collector Pipeline | Phase 1 |
| Live Application Monitoring | Phase 3 |
| PostgreSQL / Redis / ClickHouse / Kafka | Phase 2 |
| Vector Database | Phase 5 |
| Embeddings / RAG / Knowledge Graph | Phase 5 |
| Model API Calls / Agent Framework | Phase 4 |
| GitHub App / Repository Write | Phase 8 |
| Code Patching / Shell Execution | Phase 7 |
| Remediation Sandbox | Phase 7 |
| Kubernetes / Terraform / Cloud Deploy | Phase 8+ |
| Dependency lockfile | Phase 1 (tracked follow-up) |
| Accuracy Claims Without Evaluation | Never |

---

## Local Validation Results

Executed on 2026-10-10 in a clean virtual environment (Python 3.11.2) at the
repository root.

| Check | Command | Result |
|-------|---------|--------|
| Editable install | `python -m pip install -e ".[dev]" build` | ✅ PASS |
| Format check | `ruff format --check .` | ✅ PASS — "37 files already formatted" |
| Lint | `ruff check .` | ✅ PASS — "All checks passed!" (0 errors, `lint.ignore = []`) |
| Tests | `pytest -v` | ✅ PASS — 113 passed |
| CLI help | `nexus-benchmark --help` | ✅ PASS |
| CLI list | `nexus-benchmark list` | ✅ PASS — 21 cases listed |
| CLI validate | `nexus-benchmark validate` | ✅ PASS — exit 0, "All 21 cases: VALID" + composition, execution-policy and agent-view checks |
| Build | `python -m build` | ✅ PASS — sdist + wheel built |
| Wheel smoke test | `./scripts/wheel_smoke_test.sh` | ✅ PASS — wheel installed in a clean venv, CLI run from `/tmp`, 21 fixtures packaged |

`nexus-benchmark validate` output:

```
Loading schemas...
Schema version: https://nexus.local/schemas/incident-case.schema.json
Validating cases...

All 21 cases: VALID
Composition checks: PASSED
Execution policy checks: PASSED
Agent-view separation checks: PASSED

Note: This validator checks schema compliance and benchmark hygiene only.
It does NOT evaluate AI diagnosis quality or accuracy.
```

### Baseline before the corrective pass (recorded for contrast)

| Check | Before | After |
|-------|--------|-------|
| `ruff check .` | ❌ 71 errors | ✅ 0 errors |
| `ruff format --check .` | ✅ pass | ✅ pass |
| `pytest -v` | ✅ 40 passed (including 2 vacuous tests) | ✅ 113 passed |
| `nexus-benchmark --help` | ❌ `ImportError: cannot import name 'main'` | ✅ exit 0 |
| `nexus-benchmark validate` | ❌ same ImportError | ✅ exit 0 |
| Wheel install outside the checkout | ❌ assets not found | ✅ pass |

---

## Hosted Validation Results

Hosted on GitHub Actions, executed by GitHub's runners — not by this
environment.

| Run | Commit | Event | Conclusion |
|-----|--------|-------|------------|
| [38043944704](https://github.com/gm-prog/NEXUS-/actions/runs/38043944704) | `8e59e5039b67bfc34cca9ff33a2ef345eb348515` (corrective commit) | `pull_request` → `master` | ✅ success |
| [38044279834](https://github.com/gm-prog/NEXUS-/actions/runs/38044279834) | `5245f2cecf27e5e1767698bcae6dc69f9942beb6` (status-report commit) | `pull_request` → `master` | ✅ success |

Pull request: [#1](https://github.com/gm-prog/NEXUS-/pull/1). Every workflow run
recorded for this branch has concluded successfully.

Job results for the corrective commit's run (all three jobs, GitHub-hosted
`ubuntu-latest`):

| Job | Python | Conclusion |
|-----|--------|------------|
| Validate | 3.11 | ✅ success |
| Validate | 3.12 | ✅ success |
| Wheel smoke test | 3.12 | ✅ success |

Steps executed in each `Validate` job:

| Step | Result |
|------|--------|
| Install dependencies (`pip install -e ".[dev]" build`) | ✅ success |
| Check formatting (Ruff) | ✅ success |
| Lint (Ruff) | ✅ success |
| Run tests (pytest) | ✅ success |
| Installed CLI help | ✅ success |
| List benchmarks (sanity check) | ✅ success |
| Validate benchmarks | ✅ success |

Steps executed in the `Wheel smoke test` job:

| Step | Result |
|------|--------|
| Build and run the installed CLI outside the checkout (`./scripts/wheel_smoke_test.sh`) | ✅ success |

Prior to this pass GitHub reported `total_count: 0` for workflow runs, zero
status contexts and zero check runs, because the workflow targeted a `main`
branch that does not exist.


---

## Current Risks

| Risk | Status / Mitigation |
|------|---------------------|
| No dependency lockfile | **Open.** Minimum version bounds only; CI can resolve different versions over time. Tracked for Phase 1; documented in SECURITY.md and CONTRIBUTING.md |
| Wheel embeds a snapshot of `benchmarks/` | **Accepted.** A wheel built from an uncommitted working tree can differ from the committed fixtures; CI builds from a clean checkout |
| Tool-name mutation heuristic is a prefix/contains test | **Accepted.** A mutating tool with an innocuous name must be added to `execution_policy.py` by hand; the registry is a single source of truth and is unit-tested |
| Agent-view value scan is a substring heuristic | **Accepted.** Paraphrased leaks are not auto-detected and still need review; the key-level allowlist is the primary guarantee and fails closed |
| Benchmark fixture realism | **Open.** Synthetic notes specify Phase 1/2 generation requirements |
| Product naming collision (incident.io Nexus) | Documented in ADR-0007; legal review before public launch |
| Schema evolution | Versioning strategy documented; ADR required for breaking changes |
| `master` branch protection | **Open.** Not enabled — out of scope for this pass and not changed without authorization |

---

## Unresolved Questions

1. **Telemetry storage technology** — ClickHouse vs TimescaleDB vs Parquet/S3 (Phase 1 measurement needed)
2. **Application state DB** — PostgreSQL confirmed direction; embedded SQLite for local dev?
3. **Model provider abstraction** — Phase 4 decision
4. **Sandbox isolation** — gVisor vs Firecracker vs container (Phase 7)
5. **Multi-tenancy model** — Post-Phase 3
6. **Public product name** — Legal review required (ADR-0007)
7. **Lockfile tooling** — uv vs pip-compile, and whether CI should enforce `--require-hashes`

---

## Phase 1 Preconditions

**Exact conditions required before beginning Phase 1:**

1. [x] Phase 0 validation complete — all local checks executed and passing
2. [x] Hosted CI green on `master` — see "Hosted Validation Results"
3. [x] Benchmark fixtures cover all 10 fault injection targets for demo app
4. [x] Architecture documents consistent and complete
5. [x] ADRs record all major decisions with trade-offs
6. [ ] **Team alignment on Phase 1 scope** (which services, fault injection framework)
7. [ ] **Local Docker environment verified** (Docker Compose works on dev machines)
8. [ ] **OpenTelemetry SDK versions selected** (consistent across demo services)

---

## Sign-Off

Phase 0 engineering checks completed and verified on 2026-10-10. The corrective
pass above is complete; the open items are recorded as risks, not as passing
checks.

**Phase 1 has not started.** No telemetry ingestion, database, agent runtime,
LLM integration, RAG, frontend, remediation or GitHub automation code exists
in this repository.
