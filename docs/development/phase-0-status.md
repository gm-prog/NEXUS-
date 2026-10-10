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

## Second Corrective Pass (2026-10-10)

The first corrective pass was audited against the Phase 0 acceptance criteria
rather than against "do the tests pass". Four defects survived it. All four are
fixed in commit `558c4bd`, which is the current head of PR #1.

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 11 | `incident_window.end` was allowlisted as agent-visible. It is later than `investigation_cutoff` in **21 of 21** fixtures, so the projection told the investigator when an in-flight incident resolved | P1 | Conditionally excluded: `end` is forwarded only when it parses as an instant **at or before** the cutoff. Unparseable, missing or naive ⇒ dropped, so "cannot prove it is past" never becomes "assume it is past" |
| 12 | The temporal cutoff invariant was documented but unenforced. Zero of the 112 evidence items violate it today — by luck, not by construction | P1 | New `src/nexus_benchmarks/temporal.py`; `nexus-benchmark validate` gained a **Temporal integrity checks** line covering evidence `event_time` / `collection_time` / `time_window_end`, `changes[].timestamp`, `incident_window.start`, and both reversed-window orderings |
| 13 | `is_mutating_tool()` was a prefix/name heuristic, so it failed **open**: a step using `set_feature_flag`, `promote_deployment` or `run_migration` was accepted as `read_only` and therefore autonomously executable | P1 | Positive registry `TOOL_REGISTRY` naming all 21 corpus tools. Unregistered ⇒ reported, never defaults to `read_only`. Prefix patterns kept only as defence in depth |
| 14 | Structurally invalid fixtures escaped the CLI as uncaught `AttributeError`s (four reproducible inputs), and `validate_all()` ran policy checks over cases that had already failed schema validation | P2 | All three per-case checks are structurally defensive and return controlled `MalformedCaseError` strings; policy/temporal/projection checks now run only on schema-valid cases, with a "skipped" note for the rest |

Also fixed: `actions/checkout` v4 → v7.0.1 and `actions/setup-python` v5 →
v7.0.0 (both v4/v5 declare `using: node20`, which GitHub deprecated —
version facts read from upstream `action.yml` and release notes, not guessed);
`security@nexus.local` removed from SECURITY.md (placeholder domain nobody
monitors); lockfile follow-up given an owner and a trigger.

Deliberately **not** changed, with the rationale recorded in the commit and in
`CONTRIBUTING.md`: INC-013 (an `ambiguous` case whose leading alternative sits
at 0.7–0.9) and INC-017 (`trigger_change_id` set while
`change_attribution_match` is `false`). Both are coherent under the corpus's own
conventions, and both conventions are now pinned by tests instead of by
rewriting fixtures the audit did not author.

Tests went from 113 to **218**.

---

## Implemented Items

### Repository Foundation
- [x] Python 3.11+ project with `pyproject.toml`
- [x] Ruff for linting/formatting (`lint.ignore = []` — no rules suppressed)
- [x] Pytest for testing (218 tests)
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
| Format check | `ruff format --check .` | ✅ PASS — "44 files already formatted" |
| Lint | `ruff check .` | ✅ PASS — "All checks passed!" (0 errors, `lint.ignore = []`) |
| Tests | `pytest -v` | ✅ PASS — 218 passed |
| CLI help | `nexus-benchmark --help` | ✅ PASS |
| CLI list | `nexus-benchmark list` | ✅ PASS — 21 cases listed |
| CLI validate | `nexus-benchmark validate` | ✅ PASS — exit 0, "All 21 cases: VALID" + composition, execution-policy, temporal-integrity and agent-view checks |
| Build | `python -m build` | ✅ PASS — sdist + wheel built |
| Wheel smoke test | `./scripts/wheel_smoke_test.sh` | ✅ PASS — wheel installed in a clean venv, CLI run from `/tmp`, 21 fixtures packaged |

All nine rows above were re-executed at `558c4bd` after the second corrective
pass; the counts and quoting are from that run, not from the first pass.

`nexus-benchmark validate` output:

```
Loading schemas...
Schema version: https://nexus.local/schemas/incident-case.schema.json
Validating cases...

All 21 cases: VALID
Composition checks: PASSED
Execution policy checks: PASSED
Temporal integrity checks: PASSED
Agent-view separation checks: PASSED

Note: This validator checks schema compliance and benchmark hygiene only.
It does NOT evaluate AI diagnosis quality or accuracy.
```

The `Temporal integrity checks` line is new in the second corrective pass. It
is a correctness gate, not a lint: a fixture whose evidence, changes or window
start post-date `investigation_cutoff` fails `nexus-benchmark validate`
non-zero in CI.

### Baseline before the corrective pass (recorded for contrast)

| Check | Before | After |
|-------|--------|-------|
| `ruff check .` | ❌ 71 errors | ✅ 0 errors |
| `ruff format --check .` | ✅ pass | ✅ pass |
| `pytest -v` | ✅ 40 passed (including 2 vacuous tests) | ✅ 218 passed |
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
| [38044380459](https://github.com/gm-prog/NEXUS-/actions/runs/38044380459) | `aaa325e3ad450fda59bef84bdfebda7ff5ada831` (status-report commit) | `pull_request` → `master` | ✅ success |
| **[38047759013](https://github.com/gm-prog/NEXUS-/actions/runs/38047759013)** | **`558c4bdbc79714684a4c5fbd13781ea5639abc08` (second corrective pass)** | `pull_request` → `master` | ✅ **success** |

Pull request: [#1](https://github.com/gm-prog/NEXUS-/pull/1), still open.
Every workflow run recorded for this branch has concluded successfully.

The run listed last is the verification for the current head. It is a distinct
run against a distinct SHA; it is not inferred from an earlier commit's result.

Jobs in run 38047759013 (`gh api .../jobs`), all on GitHub-hosted
`ubuntu-latest`:

| Job | Job ID | Started | Completed | Conclusion |
|-----|--------|---------|-----------|------------|
| Validate (Python 3.11) | 114200627971 | 2026-10-10T11:15:23Z | 2026-10-10T11:15:37Z | ✅ success |
| Validate (Python 3.12) | 114200628171 | 2026-10-10T11:15:23Z | 2026-10-10T11:15:39Z | ✅ success |
| Wheel smoke test | 114200628173 | 2026-10-10T11:15:23Z | 2026-10-10T11:15:47Z | ✅ success |

`gh run watch 38047759013 --exit-status` exited 0 with all steps in all three
jobs marked ✅, including Check formatting (Ruff), Lint (Ruff), Run tests
(pytest), Installed CLI help, List benchmarks, Validate benchmarks, and Build
and run the installed CLI outside the checkout.

**Node 20 deprecation is cleared.** Every run at `checkout@v4` /
`setup-python@v5` carried a Node 20 deprecation annotation. Run 38047759013's
annotation list contains only GitHub's "ubuntu-latest will migrate to Ubuntu
26" notice; no Node annotation is present, and the job logs contain no
reference to Node 20. (The old job logs could not be re-fetched to re-display
the previous warning text — the fetch returned empty — so this rests on the
new run's annotation list plus the fact that both actions now declare
`using: node24`, read from their upstream `action.yml`.)

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
| Tool registry must be extended by hand | **Accepted.** A new tool fails closed (it is reported and never defaults to `read_only`) until someone registers it; `tests/test_execution_policy.py` asserts that every tool used by the corpus is registered. The prefix/exact-name patterns remain only as defence in depth, to catch a name registered `read_only` that looks mutating |
| Fixture semantic conventions (INC-013, INC-017) | **Accepted, pinned by tests.** Ambiguity describes the evidence state, not the confidence of the leading hypothesis; `change_attribution_match` records whether attribution is *required*, which it is not when the change's causal role is exactly what is in doubt |
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

Phase 0 engineering checks completed and verified on 2026-10-10. Two corrective
passes are recorded above; the open items are risks, not passing checks.

Phase 0 is considered **complete pending sign-off**: the installed CLI works,
one enforced schema/identifier contract is validated in CI, ground truth is
excluded from a tested allowlisted projection, the 20% ambiguity rule is a ratio
over the whole set, mutating checks carry an explicit risk classification and are
backed by a fail-closed tool registry, and all format/lint/test/CLI/build checks
pass locally and in a hosted run at the current head.

**Phase 1 has not started.** No telemetry ingestion, database, agent runtime,
LLM integration, RAG, frontend, remediation or GitHub automation code exists
in this repository.
