# NEXUS Phase 0 — Independent Audit Correction Pass 2

Date: **2026-10-10**. Scope: Phase 0 only. PR #1 remains open; no merge or
repository-setting change is authorised by this report.

## 1. Decision: NO-GO for Starting Phase 1

The requested temporal, tool-classification, malformed-input and INC-013
corrections are implemented and locally verified. Passing tests is **not**
benchmark diagnosis accuracy or a blanket Phase 0 sign-off. Phase 1 remains
blocked on the pre-Phase-1 lockfile policy, fixture-author review of two material
corpus contradictions, and the unverified external prerequisites listed below.
The temporal cutoff is a correctness gate; it is not waived by green CI.

**Phase 1 has not started.** No ingestion, database, demo app, frontend, model
calls, RAG, agent runtime, executable remediation or GitHub automation was added.

## 2. Baseline and Git Scope

| Item | Observed value |
|------|----------------|
| Actual `master` base | `f1e8f941e174dd8082de774527fda788ae3119ae` |
| Externally audited PR head | `aaa325e3ad450fda59bef84bdfebda7ff5ada831` |
| Working branch | `arena/eba8dba5-nexus` |
| Existing pull request | [PR #1](https://github.com/gm-prog/NEXUS-/pull/1), target `master` |
| `master` protection | `protected: false`, verified with read-only GitHub API |
| Private vulnerability reporting | `enabled: false`, verified with read-only GitHub API |

Intermediate pass-2 commits `558c4bd` and `39ceb40` had successful hosted checks,
but their INC-013 no-change rationale did not resolve the observed-incident
versus latent-defect target mismatch. Some malformed/precision cases also
remained unchecked. This final correction supersedes those conclusions; none
of that history was rewritten.

Corrective-code commit: `17a96c35a91ad70c2fe22f1a1883d8c9eb94eaef`.
Its fresh hosted run is verified in section 8. This report is an immutable
snapshot of that verified commit. A follow-up report-only commit necessarily
advances the PR tip; it must receive its own independently inspected run rather
than inheriting this conclusion. The final response records that tip/run, and
[PR #1 checks](https://github.com/gm-prog/NEXUS-/pull/1/checks) show live status.

## 3. Findings → Concrete Fixes

| Audit item | Fix and files | Regression evidence |
|------------|---------------|---------------------|
| §2.1 Future incident-resolution time leaked in all 21 original scenarios | `agent_view.py` excludes `incident_window.end` **unconditionally**; schema describes it as evaluator-only | Agent-view drift guard explicitly partitions this property; views exclude it whether before or after cutoff |
| §2.2–4 Future evidence/changes and malformed times were not rejected | `temporal.py`; CLI policy integration; direct projection guard; schema paired-window constraints | Each future start/event/collection/window endpoint/change fails helper, projection and installed CLI |
| §2.3 Offset/string-ordering and precision risks | RFC 3339 backend, aware UTC normalisation, exact fractional seconds; controlled UTC overflow errors | Equivalent offsets, both incorrect text-order directions, naive/malformed forms, invalid offsets and sub-microsecond future values |
| §2.5–7 Drift and CI enforcement | Explicit visible/evaluator nested partition and timestamp-path disposition test; `nexus-benchmark validate` in CI | Every current projection independently checked; installed subprocess negatives; temporal PASS line only on valid corpus |
| §3 Fail-open tool-name heuristic | Positive `TOOL_REGISTRY` in `execution_policy.py`; unknown tools rejected in **every** class; name patterns only defence in depth | All 21 current names registered, 18 independent read-only positives, registered mutations and novel unsafe names rejected |
| §3.6 Fixture metadata confused with runtime authorization | Module, ADR-0009, SECURITY and contributor docs state future capability/argument enforcement is still required | No executable tool or agent runtime introduced |
| §4 Invalid fixture shapes could crash dependent checks | `cli.py` validates root types and collects schema errors before dependent checks; invalid cases get NOT RUN diagnostics; defensive helpers and `MalformedCaseError` | Null/string/array/number roots; malformed lists/objects; missing nested fields; invalid identity/enum types; CLI exit 1 without traceback |
| §5 INC-013 scored an unproven latent defect as observed-incident ambiguity | INC-013 corrected to dependency failure, its optional staging check non-critical; evidence/timestamps preserved. INC-022 restores genuine ambiguity coverage | `test_fixture_semantics.py`; unchanged ratio/floor tests; ADR-0013 documents target and trade-off |
| §6.1 Conflicting lockfile deadlines | README, SECURITY, CONTRIBUTING and this report use one **pre-Phase-1 prerequisite** | No lockfile/reproducibility claim; owner/trigger explicit below |
| §6.2 Placeholder security email | Removed; GitHub Security Advisory workflow retained; disabled public reporting disclosed | Reporting configuration queried, no settings changed |
| §6.3 Local/hosted/accuracy claims conflated | Separate executed local evidence, observed hosted evidence and checks not performed | CLI still explicitly says it does not evaluate AI diagnosis quality |
| §10 Actions Node 20 maintenance warning | Verified official releases/action metadata; checkout `v7.0.1`, setup-python `v7.0.0`, both `node24` | Fresh hosted job/annotation evidence recorded below; no claim of warning-free CI |
| Packaging consumer assumed exactly 21 fixtures | Wheel smoke test now compares the actual source fixture manifest **and bytes**, rather than a magic count | 22 packaged fixtures exactly match the checkout; clean-wheel CLI validation |

Preserved from correction pass 1: installed `cli:main` entrypoint, slug identifier
contract, real FormatChecker, allowlisted answer separation, classified checks,
ambiguity ratio, wheel asset resolution, and all enabled lint rules. No lint
configuration was reduced; `lint.ignore` remains empty.

## 4. Benchmark Temporal Integrity

Reviewed **all 21 original cases**, plus the new INC-022: **22 current cases,
118 evidence records, 18 changes**. Compared every original case's
`incident_window`, evidence catalog and changes against the audited head:
**all original evidence, changes and synthetic timestamps are unchanged**.

| Corpus check | Actual result |
|--------------|---------------|
| Original future `end` leak | 21/21 original fixtures; now excluded in every view |
| Current projected `end` fields | **0** |
| Current typed temporal violations | **0** |
| Future projected evidence/change timestamps | **0** |
| Registered-tool policy violations | **0** |
| Proposed mutating steps | 6; none autonomously executable |

### Contract and Trade-off

- `end` is always evaluator-only, even when not future-dated; the projected
  window contains `start` and `investigation_cutoff`.
- `start`, evidence event/collection times, both optional interval endpoints,
  and changes must be at/before cutoff. Intervals require both endpoints in
  order; incident `start > end` is rejected too.
- Reject future records, do not silently filter them. Both the CLI and direct
  projection enforce the boundary. Invalid/naive times are errors, not skipped.
- Normalize RFC 3339 offsets to UTC and compare exact instants, never strings.
  Invalid UTC conversion is a controlled diagnostic, not a Python traceback.
- Standalone timestamp-like literals in projected configuration details also
  cannot hide future or naive times. Dates embedded in prose/URLs and arbitrary
  causal claims still require author review; the validator does not understand
  all natural language.
- Paired interval constraints tighten the unreleased draft schema without
  changing existing fixture records. All current intervals already comply.
  Consumers, schema docs and tests are updated consistently; a future published
  schema tightening would require a versioned migration.

See [ADR-0012](../decisions/ADR-0012-temporal-cutoff-integrity.md).

## 5. Execution Policy and Malformed Input

**Registered read-only tools (18):** `get_api_schema`, `get_commit`, `get_config`,
`get_config_audit`, `get_contract_test`, `get_dependency_status`,
`get_deployment`, `get_process_info`, `get_thread_dump`, `get_trace`,
`inspect_kafka_message`, `inspect_queue`, `network_diagnostic`, `query_database`,
`query_deployments`, `query_logs`, `query_metrics`, `query_traces`.

**Registered mutating tools (3):** `cache_warmup`, `execute_db_command`,
`toggle_feature_flag`.

Unknown names fail even when labelled non-automatable/human-approved, until a
reviewer explicitly registers their side effects. `set_feature_flag`,
`promote_deployment`, `run_migration` and `flip_switch` falsely labelled read-only
all produce an installed-CLI exit **1**. Read-only means no mutation; staging
experiments mutate only staging/sandbox and are non-autonomous; human-approved
mutations are non-autonomous everywhere. No automated mutating operation is
permitted. The metadata registry does **not** implement permissions, enforce
SQL/command arguments or authorize future execution.

Malformed-input subprocess tests cover array/string/null/number roots;
`evidence_catalog` as string/null or lists with null/string/empty objects;
`incident_window` as string/null/array/empty object; malformed `required_checks`;
invalid service/change structures; missing nested required structures; and
list/object identity/enum values. Observed behavior is **exit 1**, useful
field/file schema diagnostics, dependent checks marked **NOT RUN**, no Python
traceback. Valid cases still get policy checks when another case is malformed;
corpus composition is explicitly NOT RUN for an incomplete/invalid corpus.

Manual installed-CLI demonstrations also produced:

```text
Future collection_time => exit 1
INC-900: evidence_catalog[0].collection_time 2030-01-01T00:00:00+00:00
is after investigation_cutoff 2024-01-15T10:15:00+00:00

Unregistered set_feature_flag declared read_only => exit 1
... tool 'set_feature_flag' is not registered in TOOL_REGISTRY ...

Top-level null => exit 1
INC-900-negative.json: root value must be a JSON object, got null
... schema validation failed; dependent checks NOT RUN ...
```

## 6. INC-013 Semantic Decision

The target is **cause of the observed incident**, not whether new code has an
unrelated latent defect. Both old/new path traces fail at the same degraded
external engine, so INC-013 is now `single_cause` / `dependency_failure`, category
`dependency_regression`. Its diagnosis must cite both path traces and dependency
status, and must not claim flag causation or healthy-dependency code correctness.
The hypothetical code-defect alternative is removed; the staging toggle is an
optional non-critical resilience experiment with no assumed future result.
Symptoms, answer key, required checks and remediation wording agree on that target.

Reclassification left **4 uncertainty cases**, failing the unchanged floor of
5 (`nexus-benchmark validate` actually reported this). Instead of weakening
coverage or relabelling an unrelated fixture, INC-022 supplies a genuine missing
failure-location/holdout comparison. Both hypotheses concern its observed
errors. Final distribution: **16 single-cause, 1 multi-factor, 3 ambiguous,
2 insufficient-evidence; 5/22 = 22.7% uncertainty**.

See [ADR-0013](../decisions/ADR-0013-observed-incident-target.md). No model
baseline exists or was evaluated; these are authoring/consistency changes.
INC-017 was reviewed and not gratuitously rewritten: a named trigger with
optional attribution does not itself contradict unresolved primary contribution.

## 7. Executed Local Validation

A fresh `.venv` was created on 2026-10-10 with Python **3.11.2**, then all nine
requested commands executed. Commands used `set -euo pipefail`; raw output is
saved locally in ignored `test-results/phase-0-pass-2/`, not committed as artifacts.

| Exact command | Exit | Real inspected result |
|---------------|------|-----------------------|
| `python -m pip install -e ".[dev]" build` | 0 | Successfully installed nexus-benchmarks and development/build dependencies |
| `ruff format --check .` | 0 | `47 files already formatted` |
| `ruff check .` | 0 | `All checks passed!` |
| `pytest -v` | 0 | **345 passed in 13.83s**, no skips |
| `nexus-benchmark --help` | 0 | Installed console-script help displayed |
| `nexus-benchmark list` | 0 | 22 cases listed, corrected INC-013 and new INC-022 |
| `nexus-benchmark validate` | 0 | All 22 cases VALID; composition, tool policy, temporal integrity and agent-view checks PASSED |
| `python -m build` | 0 | Built `nexus_benchmarks-0.1.0.tar.gz` and `nexus_benchmarks-0.1.0-py3-none-any.whl` |
| `./scripts/wheel_smoke_test.sh` | 0 | 22 fixtures: manifest and bytes match; clean-wheel CLI from outside checkout; `Wheel smoke test PASSED` |

The first wheel smoke rerun failed because its old hardcoded `21` excluded the
new fixture. It was **not** reported passed: the manifest/byte comparison replaced
that obsolete count, and the real clean-wheel run then passed. The validator's
expected failure at 4 uncertainty cases likewise was fixed by adding true
coverage, not by lowering its threshold.

Explicit installed-CLI negative regression command (executed):

```bash
pytest -v tests/test_temporal_integrity.py tests/test_execution_policy.py -k 'test_installed_cli_rejects_each_future_timestamp or test_installed_cli_rejects_a_new_tool_falsely_declared_read_only'
```

Result: **10 passed, 132 deselected in 2.26s**. Each passing assertion proves
its intentionally invalid fixture caused a nonzero (1) CLI exit with the
expected temporal or unregistered-tool diagnostic; none is a skipped failure.

Installed versions: Ruff 0.17.0, pytest 9.1.1, jsonschema 4.26.0,
rfc3339-validator 0.1.4, click 8.5.0, build 1.6.1. These are observed versions,
**not** a committed lockfile. Build isolation used hatchling 1.32.4.

## 8. Hosted Validation (Independent Evidence)

**Fresh run:** [38049278138](https://github.com/gm-prog/NEXUS-/actions/runs/38049278138)

**Exact head SHA:** `17a96c35a91ad70c2fe22f1a1883d8c9eb94eaef`

**Event:** `pull_request`, branch `arena/eba8dba5-nexus`, target `master`.
This is PR validation, not a claim that changes have been pushed/merged to master.

**Created:** `2026-10-10T11:41:06Z`. **Status:** completed.
**Actual conclusion:** success, inspected with `gh run view` and the jobs API.
No result was inferred from a previous SHA's run.

| Job | Actual job URL | Actual conclusion |
|-----|----------------|-------------------|
| Validate (Python 3.11) | [114204960343](https://github.com/gm-prog/NEXUS-/actions/runs/38049278138/job/114204960343) | success |
| Validate (Python 3.12) | [114204960174](https://github.com/gm-prog/NEXUS-/actions/runs/38049278138/job/114204960174) | success |
| Wheel smoke test | [114204960290](https://github.com/gm-prog/NEXUS-/actions/runs/38049278138/job/114204960290) | success |

Both Validate jobs report success for install, formatting, lint, pytest,
installed CLI help/list/validate and cleanup. The wheel job reports success
for build and the clean installed-wheel smoke check. `gh pr checks 1` independently
reported all three passing. These are observed step conclusions, not locally
executed Python 3.12 tests or a claim to have read unavailable redirected logs.

Historical runs, not used as proof of the final correction:

- Audited head `aaa325e`: [38044380459](https://github.com/gm-prog/NEXUS-/actions/runs/38044380459), success.
- Intermediate `558c4bd`: [38047759013](https://github.com/gm-prog/NEXUS-/actions/runs/38047759013), success.
- Intermediate report `39ceb40`: [38047913023](https://github.com/gm-prog/NEXUS-/actions/runs/38047913023), success.

### CI Maintenance and Repository Settings

Official [checkout v7.0.1 release](https://github.com/actions/checkout/releases/tag/v7.0.1)
and [setup-python v7.0.0 release](https://github.com/actions/setup-python/releases/tag/v7.0.0)
were read, and both `action.yml` files declare `node24`. Unsafe-PR checkout
guards do not affect our `pull_request` event; removed `pip-install` input was
not used. Triggers, read-only permissions and validation jobs are preserved.

All three **fresh** run 38049278138 annotation responses were inspected via
`GET /repos/gm-prog/NEXUS-/check-runs/{job-id}/annotations`. Each contains only
the notice that `ubuntu-latest` will migrate to Ubuntu 26 from **2026-10-19**;
none contains a Node 20 deprecation warning. This is not a claim of warning-free
CI: the runner-image notice remains, with the dated maintainer follow-up below.
Full log downloads redirect to a host unavailable in this sandbox; hosted
claims rely on accessible run/job/step conclusions and annotation API responses,
not a claim that the full redirected logs were read.

`master` is unprotected. **Recommendation:** enable required validation/wheel
checks before a future merge, with separate authorisation. No settings were
changed and PR #1 was not merged.

## 9. Remaining Risks, Deferred Work and Unverified Checks

| Item | Honest status / owner / trigger |
|------|--------------------------------|
| INC-016 arithmetic and target consistency | **Open semantic review.** Metric is said to rise 0.5%→8%, but double counting implies ~4% actual, conflicting with normal-volume claims. Owner: benchmark authors; resolve before benchmark sign-off/model evaluation. Not silently rewritten or detected by shape validation |
| INC-019 lock mechanism | **Open semantic review.** Its plain SELECT does not specify the lock mode/transaction that explains blocking all PostgreSQL writes. Owner: benchmark authors; clarify before benchmark sign-off/model evaluation. No live database validation performed |
| Dependency lockfile | **Absent, pre-Phase-1 prerequisite.** Owner: NEXUS maintainers; reviewed tooling and enforced locked/hashed installs required before Phase 1 implementation begins. No pinned/reproducible supply-chain claim |
| Private vulnerability reporting | **Disabled.** Advisory workflow retained, no verified public email configured. Owner: repository maintainer; enable private reporting/provide verified contact through a separately authorised settings decision |
| Required branch checks | **Not protected.** Owner: repository maintainer; authorise required checks before any future merge |
| Action SHA pinning / runner-image migration | Action release versions upgraded, not immutable SHA pins. Owner: CI maintainers; review pinning before future merge and runner migration on/after 2026-10-19 |
| Tool implementation permissions | Registry describes metadata only. Future runtime must enforce capabilities, argument constraints and credentials at execution boundary; not implemented here |
| Opaque prose/answer leakage | Typed times and standalone timestamp literals are checked; arbitrary prose/URLs and paraphrased answers still require review. Value scan is a heuristic, not a formal contamination proof |
| Realism / accuracy | Fixtures remain synthetic. No model evaluation, diagnosis-accuracy measurement, production telemetry, fault injection or live database safety checks were performed |
| External Phase 1 prerequisites | Team scope alignment, working local Docker environment and OpenTelemetry SDK selection were not verified. No Phase 1 work was begun |

## 10. Stop / Sign-Off Boundary

The requested correction pass stops here after verification and the existing
branch push. This report does **not** grant a Phase 1 GO or merge permission.
Remaining semantic/prerequisite findings need separate author sign-off.
No force-push, history rewrite, branch deletion, master commit, merge or settings
change occurred. **PR #1 stays open/unmerged; Phase 1 has not started.**
