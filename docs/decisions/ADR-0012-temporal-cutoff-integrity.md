# ADR-0012: Fail-Closed Temporal Cutoff Integrity

- Status: Accepted
- Date: 2026-10-10

## Context

At the audited PR head `aaa325e`, all 21 cases expose `incident_window.end`
after `investigation_cutoff`. `end` describes eventual resolution or observation
completion, so it is future outcome metadata. Evidence happened to precede the
cutoff (112 records, 17 changes), but the validator did not enforce availability
by event/collection/window time. Timestamp-string ordering would also give
incorrect results across offsets.

An intermediate correction conditionally excluded `end` and skipped malformed
evidence times inside its temporal helper. The final contract is stronger and
simpler: the resolution field is never an input and malformed/future records
are errors at both the CLI and direct projection boundary.

## Decision

- `incident_window.end` is always evaluator-only, not renamed or conditionally
  forwarded. The agent-visible window contains `start` and `investigation_cutoff`.
- Reject future records, rather than filter them. `evidence_catalog` and
  `changes` describe available investigator input; filtering would hide an
  authoring defect and change the scored evidence coverage silently.
- Validate every typed exposed time: `start`, `investigation_cutoff`, evidence
  `event_time`, `collection_time`, both optional interval endpoints, and each
  change `timestamp`. Exposed values other than the cutoff must be at/before it.
- Optional evidence intervals require **both** endpoints, in chronological
  order. `incident_window.start > end` is also invalid.
- Use the declared RFC 3339 backend plus full matching, timezone-aware UTC
  normalisation and exact fractional-second comparison. Reject malformed/naive
  timestamps and out-of-range UTC conversion, never silently skip them. Leap
  seconds are unsupported by the existing backend and fail closed.
- CLI schema-invalid cases have dependent checks explicitly marked NOT RUN.
  Direct `build_agent_view()` calls also run temporal validation and raise a
  controlled `TemporalIntegrityError` before returning any future input.
- Standalone timestamp-like literals in projected configuration context also
  cannot hide future or naive values.
- The nested allowlist drift guard classifies `end` as an intentional exclusion.
  A second drift guard enumerates all schema date-time paths and requires an
  explicit cutoff/evaluator disposition for new typed time-bearing fields.

## Trade-offs and Consumers

This tightens the draft `1.0.0` incident schema with paired interval endpoints.
All existing intervals already have both endpoints, so no original fixture
records or timestamps need changing. There is no released schema consumer or
model-evaluation baseline to migrate in this pre-alpha repository. A future
published schema would require a versioned migration for this tightening.

The correction updates schema descriptions, `temporal.py`, the CLI, the agent
projection, tests, benchmark/contributor documentation and the frozen-snapshot
pseudo-code. A wheel ships the corrected schema and projection together.

Always excluding `end` loses some harmless context for a completed incident,
but avoids a conditional answer signal and keeps the boundary reviewable.
Prose, references and free-form configuration details still require author
review; these checks do not understand arbitrary natural-language future or
causal claims.

## Validation / Reversal Criteria

`tests/test_temporal_integrity.py` covers each future field through the helper,
projection and installed CLI; collection-time availability; missing/reversed
intervals; equivalent and oppositely ordered offsets; malformed/naive forms;
UTC overflow; and sub-microsecond precision. `nexus-benchmark validate` enforces
this invariant in hosted CI. Revisit only if a later, versioned schema explicitly
separates future/evaluator records from the investigator snapshot.
