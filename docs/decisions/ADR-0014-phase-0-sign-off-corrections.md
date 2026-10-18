# ADR-0014: Phase 0 Sign-Off — Evidence, Causal-Text Leakage and Locked Dependencies

- Status: Accepted
- Date: 2026-10-10
- Scope: explicitly authorized Phase 0 corrections only; Phase 1 is unstarted

## Context

The previous correction deliberately left INC-016's rate/target contradiction,
INC-019's unsupported PostgreSQL locking mechanism and the dependency lock as
open blockers. The causal-description value scan also had a blanket exclusion.
Passing schema validation did not resolve any of these semantic/supply-chain
issues. This decision records the narrowly authorized changes, not model
accuracy or production observations.

## Decision — INC-016

Retain `insufficient_evidence`. The target is the **underlying HTTP failure
rate and alert validity**, not whether the code contains duplicate counter
updates. The supplied display remains 0.5% baseline / 8% current, the counter
updates twice, and the alert remains the original >5% condition.

Only with aligned numerator/denominator definitions, population and window:

- 8% / 2 = 4%;
- 4% / 0.5% = **8 times baseline**, not normal;
- 8% / 0.5% = **16 times baseline**.

There is no aligned request denominator in the frozen evidence. Unchanged
~50/min error counts and a sampled 200-OK trace do not establish a request rate
or fleet-wide health. No request totals, new thresholds or coverage windows are
invented. The existing `changes.details` object records the code-evidenced
factor two and explicitly unavailable denominator alignment for structured
regression checks.

High confidence in the instrumentation defect is separate from uncertain
service health. Remove sole-cause attribution and confirmed false-positive
alternatives, leave the incident trigger unassigned, require the conflicting
artifacts, and do not require high confidence in an unestablished rate.
Correct the old invented ~100/min check outcome. Checks seek alignment rather
than assume it; remediation proposes instrumentation validation without
silencing investigation of a possible concurrent real fault.

## Decision — INC-019

Replace the unsupported plain-SELECT/deadlock story with an explicit synthetic
transaction:

```sql
BEGIN;
LOCK TABLE orders IN SHARE MODE;
SELECT * FROM orders WHERE created_at > '2024-02-01';
-- Still open at the investigation cutoff; no transaction completion assumed.
```

The activity evidence gives backend/owner identity, SQL and transaction start.
A new **authored synthetic** lock/wait snapshot at the cutoff supplies:

- the analytics owner's granted `ShareLock`;
- its ordinary SELECT's also-granted `AccessShareLock` (not the blocker);
- distinct order INSERT/UPDATE waiters requesting `RowExclusiveLock`;
- `pg_blocking_pids` linking both writers to that same analytics owner.

PostgreSQL's [official lock-conflict table](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/storage/lmgr/lock.c)
confirms Share/RowExclusive conflict and AccessShare/RowExclusive compatibility.
No live database was run and no actual telemetry is claimed. Timeouts use
PostgreSQL `55P03`, not the old MySQL-style deadlock log; no wait cycle, CPU,
connection exhaustion, revenue measurement or recovery result is invented.

Keep category `db_lock_contention` and `single_cause`. Use the existing
`design_flaw` taxonomy for the observed write-blocking **analytics workflow**
(explicit table locking on the writer primary), not an unevidenced capacity
failure. Require transaction, owner and lock/wait evidence in the answer key.

Remediation is non-critical to diagnosis and human/DBA-gated: safely end the
owning transaction or consider approved backend termination, then verify lock
release and writer progress. Merely canceling a statement is not proof of
transaction completion or guaranteed recovery. Account for possible rollback;
remove the old low-risk/immediate-recovery promise. No SQL is executed here.

Both legacy filenames remain stable. Existing fixture timestamps are preserved;
only the new lock snapshot adds times, at the original cutoff. Evidence IDs
that falsely named deadlocks are corrected together with every cross-reference.
There is no schema structure/version change or new incident case.

## Decision — Answer-Text Scan

Scan every causal-chain `from_description` and `to_description`, plus every
check `expected_outcome`. Match actual projected strings, including dictionary
keys, case-insensitively rather than against JSON-escaped text. Preserve the
allowlist, temporal validation and identifier-cross-reference exclusions.

A corpus audit found exactly two legitimate observation overlaps. The
`REVIEWED_OBSERVATION_OVERLAPS` registry pins **case, hidden path, visible path,
complete hidden text and complete visible text**, not an entire category:

| Case | Hidden path | Visible path | Author-reviewed observation |
|---|---|---|---|
| INC-021 | `ground_truth.causal_chain[1].to_description` | `initial_symptoms[2]` | Both exactly `Thread pools exhausted in payment, checkout, order, user services`; a symptom, not the root-cause answer |
| INC-006 | `required_checks[0].expected_outcome` | `evidence_catalog[1].summary` | `Logs show 'Rate limit exceeded: 100 req/min'` is the log quotation within exactly `Gateway logs show 'Rate limit exceeded: 100 req/min' for all incoming requests` |

A copy elsewhere, changed answer or extended visible text is **not** exempt.
Tests cover both reviewed observations, changed/appended copies, legitimate
paraphrases, every corpus causal description copied into evidence, multiple
visible destinations, quotes/newlines, dictionary-key copies, and rejection by
the installed CLI. No new general exemption may be inferred from visible text
already containing an answer. The eight-character heuristic is unchanged;
short/incidental overlap and semantic/paraphrased leaks still require review.

## Decision — Dependency Enforcement

Commit `uv.lock` for the complete runtime/dev/build closure (27 third-party
packages plus this checkout), including resolved versions and artifact hashes.
Use exactly uv 0.13.0. Full-SHA action pins were verified against official
release refs for checkout v7.0.1, setup-python v7.0.0 and setup-uv v10.3.0;
all use Node 24. Tool bootstrap uses setup-uv's release checksums.

- Strict `uv lock --check` and `uv sync --locked` reject dependency metadata
  drift. CI does not rewrite the lock or silently upgrade pip/packages.
- Stage the locked backend/helper before building editable without isolation.
  `hatchling`, `build` and `editables` are explicit locked dev requirements.
- uv does not track build-system-only constraint edits. The setup script
  requires exact mirrored dev constraints before the editable build; updating
  both makes uv's normal metadata check enforce the change. A real offline
  subprocess regression demonstrates and closes this bypass. The three
  dependency-drift integration probes permit read-only index metadata access:
  uv re-resolves changed constraints before emitting its specific --check
  mismatch. They assert rejection and lock immutability, never install or
  rewrite anything. A separate empty-cache regression proves offline
  current-lock acceptance and stale-lock fail-closed behavior.
- Build wheel/sdist with `--no-isolation`. Export the locked runtime closure
  with hashes, require binary/hash-matching artifacts in a clean venv, then
  install the local wheel `--no-deps --no-index`. Check installed dependencies,
  the exact fixture manifest/bytes and the installed CLI outside the checkout.

Library metadata's minimum bounds remain appropriate for downstream consumers;
only the documented repository/CI path is the locked environment. Python patch
releases and the OS image are not locked and byte-identical builds or security
absence are not claimed. Update/enforcement commands are in CONTRIBUTING.md.

## Validation / Scope

Focused fixture, leakage and real lock-drift regressions complement (not replace)
full pytest, strict Ruff, full corpus validation and wheel smoke. Hosted Python
3.11/3.12 and wheel checks must be verified against the **last pushed SHA**;
PR #1's body is the final-head attestation without a self-referential document
commit ID. See [Phase 0 Status](../development/phase-0-status.md).

No tests are skipped, no lint/schema rules weakened, no repository settings,
secrets, branch protection or PR merge state changed. No Phase 1 implementation,
model call, telemetry ingestion, database, UI or tool executor is introduced.
