# NEXUS Phase 0 — Sign-Off Corrections

Date: **2026-10-10** (original corrections; the starting-state descriptions in
this document are historical observations from that period). Post-merge
verification: **2026-10-18**. Scope: Phase 0 only; **Phase 1 has not started
and requires separate authorization**. [PR #1](https://github.com/gm-prog/NEXUS-/pull/1)
— the correction PR on `arena/eba8dba5-nexus` targeting `master` — was merged
on **2026-10-18**; the merge commit is
[`fad12054dccddde7d6a00e512767f58de1d95f24`](https://github.com/gm-prog/NEXUS-/commit/fad12054dccddde7d6a00e512767f58de1d95f24),
verified at the time of this update. The correction work itself performed no
merge, shared-history rewrite, repository-setting or secret change.

## Sign-Off Record — Pre-Merge and Post-Merge

### Pre-merge sign-off (historical; PR head `073fa21a…`)

**The Phase 0 sign-off is the exact-final-head record in
[PR #1's description](https://github.com/gm-prog/NEXUS-/pull/1), with its
then-current-head checks.** It covers PR head
`073fa21ad6252f64554be8ae60ca99d40033fda3`, validated by the `pull_request`
[run 38059644430](https://github.com/gm-prog/NEXUS-/actions/runs/38059644430)
against that exact head (all three required jobs successful). That record was
assembled after the last push and exact-SHA verification; it is not an earlier
code-head snapshot or an unfiltered "latest CI" result.

### Post-merge verification (2026-10-18; merge commit `fad12054…`)

PR #1 merged into `master` on 2026-10-18 as merge commit
[`fad12054dccddde7d6a00e512767f58de1d95f24`](https://github.com/gm-prog/NEXUS-/commit/fad12054dccddde7d6a00e512767f58de1d95f24).
The post-merge `push` workflow ran on `master` at that exact SHA —
[run 39115811204](https://github.com/gm-prog/NEXUS-/actions/runs/39115811204),
conclusion **success**:

| Required job | Job ID | Result |
|---|---|---|
| [Validate (Python 3.11)](https://github.com/gm-prog/NEXUS-/actions/runs/39115811204/job/117641246173) | 117641246173 | success |
| [Validate (Python 3.12)](https://github.com/gm-prog/NEXUS-/actions/runs/39115811204/job/117641246214) | 117641246214 | success |
| [Wheel smoke test](https://github.com/gm-prog/NEXUS-/actions/runs/39115811204/job/117641246093) | 117641246093 | success |

Each job completed successfully against the same merge SHA. The post-merge run
does not retroactively turn the pre-merge run into post-merge evidence, and
neither run validates any later documentation commit.

This committed document cannot embed the SHA of the commit containing itself.
The recorded merge SHA is a known baseline, not the future docs-PR head; the
PR attestation deliberately lives outside that self-referential commit.
Subsequent edits do not inherit sign-off: the final-head gate must be checked
again at each change's exact PR head, even for a docs-only push.

Read-only reproduction of run/job inspection for any candidate head:

```bash
sha=$(git rev-parse HEAD)   # candidate PR head, or the merge SHA under review
gh api "repos/gm-prog/NEXUS-/actions/runs?head_sha=$sha" \
  --jq '.workflow_runs[] | {id, event, head_sha, status, conclusion, html_url}'
# Select the run whose event/branch match the claim (pull_request vs push);
# for the matching completed run, inspect all three jobs and their steps:
gh api "repos/gm-prog/NEXUS-/actions/runs/RUN_ID/jobs" \
  --jq '.jobs[] | {name, conclusion, steps}'
```

Required hosted jobs: **Validate (Python 3.11)**, **Validate (Python 3.12)** and
**Wheel smoke test**, all successful at that exact final head. Full hosted log
downloads are not claimed: run/job/step API results are the observed evidence.

## Starting State and Preservation

The following starting-state paragraphs are historical observations from the
2026-10-10 correction period.

The local checkout initially had base HEAD
`f1e8f941e174dd8082de774527fda788ae3119ae` plus restored modified/untracked
files. The actual open, unmerged PR head was
`37bdcd0b7af2b5c8d7065468930c08adb9330822`. Before editing, every published
file's bytes/executable mode and the complete staged tree were verified to
match that remote head, then a normal fast-forward preserved the published
history. No reset, rebase, force-push or unrelated work was discarded.

The [previous correction report](https://github.com/gm-prog/NEXUS-/blob/37bdcd0b7af2b5c8d7065468930c08adb9330822/docs/development/phase-0-status.md)
is historical evidence, not the sign-off result for these new changes.

## Corrections and Evidence

| Blocker | Scoped correction | Regression/evidence |
|---|---|---|
| INC-016 | Keep an insufficient-evidence target: instrumentation defect known, actual failure rate/alert validity unestablished | Structured factor/alignment fields; conditional 8/2=4%, 8× baseline and 16× reported arithmetic; uncertainty/attribution/confidence and known-contradiction checks |
| INC-019 | Open explicit SHARE transaction; evidenced conflicting DML waits, PostgreSQL lock timeouts, not a plain-SELECT/deadlock story | SQL/transaction identity, granted Share and compatible AccessShare locks, waiting RowExclusive locks and matching blocking PIDs; human-gated transaction remediation |
| Causal-text leakage | Scan all from/to descriptions and check outcomes against projected strings/keys, including quotes/newlines | Every corpus causal description copied into evidence is caught; multiple destinations and installed-CLI negatives; legitimate paraphrase/overlap tests |
| Dependency lock/build bypasses | Commit `uv.lock`; enforce strict locked runtime/dev/build installs and hash-checked clean wheel installation | Real runtime/lint/build mismatch/no-rewrite checks, plus offline empty-cache rejection and the build-system-only mirrored-dev guard |

Details and authoring decisions:
[ADR-0014](../decisions/ADR-0014-phase-0-sign-off-corrections.md).

### Fixture Semantics

**INC-016:** supplied 0.5% baseline, 8% display and factor-two code defect are
unchanged. Only if populations, numerator/denominator definitions and windows
align does 8%/2 imply 4%; that is elevated, not normal. No aligned denominator
or complete sampling coverage is supplied. Neither normal health, confirmed
real spike, false-positive alert nor sole-cause attribution is scored as a
supported conclusion. Counter-defect confidence is separate from confidence
about actual service health. No invented ~100/min metric count remains.

**INC-019:** the analytics transaction explicitly acquires SHARE on orders;
its normal SELECT also holds the compatible AccessShare lock. The new authored
synthetic snapshot at the original cutoff identifies the granted ShareLock,
INSERT/UPDATE RowExclusive waiters and their analytics blocking PID. PostgreSQL
Share/RowExclusive conflict explains writes waiting; AccessShare alone would
not. Error `55P03` is a lock timeout, not an observed deadlock cycle. Existing
`design_flaw` taxonomy denotes this write-blocking analytics workflow, not
unmeasured capacity exhaustion. Transaction remediation is non-critical to
diagnosis, medium risk and human/DBA-gated, with no recovery result assumed.
**No live PostgreSQL or real telemetry validation was performed.**

### Leak Exceptions and Limits

The broad causal-description and expected-outcome omissions are removed.
There are exactly two explicit observation exceptions: INC-021's thread-pool
symptom and INC-006's rate-limit log quotation. Each pins case ID, hidden path,
visible path and both complete texts; nothing is exempt merely because it
already appears somewhere in visible evidence. Copies elsewhere, changed
answers and appended copies fail. These exact tuples and the reason for each
are documented/tested in ADR-0014 and `tests/test_agent_view.py`.

The scan is a case-insensitive verbatim-copy heuristic with the existing
minimum eight-character filter. It does not prove semantic answer privacy;
paraphrases/free-form prose still require author review. Identifier
cross-references remain legitimate, not answer prose.

### Lock and CI Policy

- uv **0.13.0** enforced; **27 third-party packages plus this project** locked
  with resolved versions and artifact SHA-256 hashes.
- `hatchling`, `build`, `editables`, pytest/coverage and Ruff share the lock.
  Stage locked wheels first, then build editable without isolation.
- `uv lock --check` / `uv sync --locked` reject dependency metadata drift.
  Build requirements must be mirrored exactly in the dev extra; the pre-build
  guard closes uv's otherwise-unchecked build-system-only edits.
- Wheel/sdist build uses `--no-isolation`. Clean runtime installation uses a
  locked hash export, `--require-hashes --only-binary :all: --no-deps`, then
  installs the local wheel `--no-deps --no-index` and checks dependencies.
- Checkout **v7.0.1**, setup-python **v7.0.0** and setup-uv **v10.3.0** execute
  verified full-SHA pins, not mutable tags; Node 24 runtimes are verified.
- No independent pip resolution, unbounded upgrade or build-isolation bypass
  remains in the validation workflow. Update commands are in CONTRIBUTING.md.
- Pins improve dependency repeatability; OS images/Python patch releases are
  not locked. No byte-identical-build or vulnerability-absence claim is made.


The first hosted candidate (`4cc8ec582855f962b5413060bb593904c0e3e943`,
[run 38059076421](https://github.com/gm-prog/NEXUS-/actions/runs/38059076421))
passed wheel smoke but failed both pytest jobs. A fresh local checkout/cache
reproduced three newly added drift probes: offline index metadata was missing,
so uv rejected with a resolution error rather than the asserted stale-lock
message. No production gate or assertion was removed. Those integration probes
now allow read-only index metadata to test the **same specific mismatch** and
lock immutability; a new truly empty-cache test separately verifies offline
current-lock acceptance and stale-lock rejection. No probe installs an unlocked
environment. The earlier failed run is historical, not final-head evidence.

## Executed Local Validation

Python **3.11.2**, uv **0.13.0**, Linux. Raw local logs are in ignored
`test-results/phase-0-sign-off/`, not committed build artifacts.

| Gate | Local outcome |
|---|---|
| `./scripts/locked_sync.sh` | PASS: strict lock, locked backend/helper, no isolated build |
| `.venv/bin/ruff format --check .` | PASS: 49 files already formatted |
| `.venv/bin/ruff check .` | PASS: no lint exemptions added; `lint.ignore = []` |
| `.venv/bin/python -m pytest -v` | PASS: **383 passed, no skips** |
| Targeted agent-view / fixture semantics / dependency lock tests | PASS: **69 passed** |
| Cold checkout / installation-only cache reproduction | PASS: **383 passed**, including explicit empty-cache offline rejection |
| Installed CLI `--help` / `list` / `validate` | PASS: **all 22 cases VALID**, composition/execution/temporal/separation passed |
| `./scripts/wheel_smoke_test.sh` | PASS: no-isolation wheel/sdist build, clean hash-locked runtime install, dependency check, installed CLI outside checkout |
| Wheel fixture integrity | PASS: exact **22-fixture manifest and all source bytes match** |
| `uv lock --check --offline` and drift regressions | PASS: consistency; stale runtime/lint/build metadata rejected; build-only guard tested |
| Shell syntax / `git diff --check` | PASS |

**Python 3.12 was not available/run locally.** Its full tests, lint, corpus and
wheel validation are required hosted evidence in the final-head record above,
not inferred from local Python 3.11 success.

## Corpus Preservation

- **22 cases, 119 evidence records, 18 changes.** Only the new INC-019 lock
  snapshot increases the previous 118 evidence records.
- **16 single-cause, 1 multi-factor, 3 ambiguous, 2 insufficient-evidence**;
  uncertainty remains **5/22 = 22.7%**, satisfying the unchanged ratio gate.
- Every existing incident-window/evidence/change timestamp is unchanged.
  The other **20 incident JSON objects are unchanged** from the starting PR
  head; renamed INC-019 evidence references remain consistent.
- Prior INC-013/022 target fixes, temporal precision/fail-closed boundaries,
  malformed-input diagnostics, positive tool registry and mutation policy
  remain covered. No weakening of schemas, Ruff, ratio or existing tests.

## Maintainer Actions / Verdict Boundary

**Historical observation (2026-10-10):** read-only checks at that time reported
`master` unprotected and private vulnerability reporting disabled; enabling
protection or publishing a verified private contact required a separate
maintainer settings decision, and the correction work changed no settings and
neither merged nor closed PR #1.

**Master protection, verified 2026-10-18:** `master` is covered by the active
repository ruleset
[`protect-master-pr-and-ci`](https://github.com/gm-prog/NEXUS-/rules/25337956)
(ID 25337956), scoped to `refs/heads/master`:

- required status checks under a strict up-to-date policy: **Validate
  (Python 3.11)**, **Validate (Python 3.12)**, **Wheel smoke test**;
- pull requests required (configured required approval count **0**); allowed
  merge methods: merge, rebase, squash;
- branch deletion and non-fast-forward pushes blocked; no bypass actors;
- the conditional extra-approval rule for unattributed Copilot pull requests
  (`require_extra_approval_for_unattributed_changes`) is enabled and was
  intentionally accepted for the current scope; it does **not** mean ordinary
  pull requests require one approval.

Private vulnerability reporting and private security contact status are
**unverified** as of this update; no claim is made about their current state,
and no settings were changed by this documentation work.

The **GO for Phase 0 sign-off** remains the exact-final-head PR record,
conditioned on all three successful hosted jobs plus these scoped corrections
and local gates. It is not benchmark diagnosis accuracy, runtime authorization,
production readiness or permission to start Phase 1. **Phase 0 is the only
implemented phase; Phase 1 remains unstarted and requires a separate
instruction.**
