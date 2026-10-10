# ADR-0010: Allowlisted Agent-View Projection for Benchmark Cases

- Status: Accepted
- Date: 2026-10-10

## Context

Each incident case file colocates agent-visible evidence with the
evaluator-only answer key (`ground_truth`, `expected_diagnosis`,
`acceptable_alternatives`, `required_checks`, `remediation_guidance`,
`misleading_or_confounding_signals`, `category`, `scenario_type`,
`difficulty`, `tags`). Passing a whole case object to an agent leaks the answer
and silently inflates every score.

The existing test suite did not actually guard that boundary:

- `test_ground_truth_not_in_evidence_catalog` looped over ground-truth *field
  names* and asserted the name (e.g. `root_cause_type`) was not a substring of
  `str(evidence_catalog)`. It never looked at a ground-truth *value* and never
  looked at the agent input boundary.
- `test_must_not_claim_not_in_evidence` built `evidence_text`, looped over
  `must_not_claim` and executed `pass`.

Both tests passed vacuously.

## Decision

**The agent-visible representation is a strict allowlist projection, defined
once in `src/nexus_benchmarks/agent_view.py`.**

Allowed at the top level:

`schema_version`, `case_id`, `environment`, `incident_window`,
`initial_symptoms`, `affected_services`, `evidence_catalog`, `changes`.

Everything else is evaluator-only and never forwarded. Two nested fields are
additionally dropped because they carry answer signal or benchmark
infrastructure:

- `affected_services[].impact` — labelling a service `primary` hands over the
  localisation answer that `expected_diagnosis.service_localization_match`
  exists to measure.
- `evidence_catalog[].synthetic_fixture_note` — fixture-authoring metadata, not
  incident evidence.

**The projection fails closed.** An unclassified top-level key raises
`AgentViewError` rather than being silently forwarded, so adding a field to the
schema forces an explicit decision. `tests/test_agent_view.py` asserts the
allowlists match the schema properties exactly, which catches drift in both
directions.

Leak detection combines two independent checks:

1. No evaluator-only *key* survives the projection.
2. No evaluator-only *value* (≥ 8 characters) appears in the serialised
   projection. Two categories are excluded from the value scan because they
   legitimately restate agent-visible observations and produced false
   positives on the current corpus: `required_checks[].expected_outcome` (often
   quotes a log line that is itself evidence) and
   `ground_truth.causal_chain[].*_description` (paraphrases symptoms). Both
   remain covered by the key-level allowlist.

The tests prove the checks are non-vacuous by injecting leaks (ground-truth
values copied into evidence summaries, `must_not_claim` appended to symptoms,
remediation text placed in `environment`) and asserting they are reported.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Split evaluator-only data into separate files | Correct but a much larger change: it breaks the one-file-per-incident review model, the cross-reference checks and every doc reference |
| Blocklist of evaluator-only keys | Fails open — a new answer-revealing field is forwarded until someone notices |
| Keep the file split but rely on evaluator discipline | Exactly the discipline that produced two passing no-op tests |

## Trade-offs and Consequences

**Pros:**

- One place defines the boundary; the evaluator, the CLI and the tests all use
  it.
- Fails closed on schema evolution.
- Tests demonstrate detection of injected leaks, so the guard cannot rot into
  another vacuous assertion.

**Cons:**

- The allowlist must be updated whenever the schema gains a top-level property
  (a test fails loudly if it is not).
- The value scan is a heuristic string match; a paraphrased leak is not
  detected automatically and needs review.
- The projection currently lives in the same package as the CLI, so the
  eventual Phase 4 evaluator imports it rather than re-deriving a boundary.

## Validation / Reversal Criteria

- **Validate:** `nexus-benchmark validate` reports agent-view separation
  failures; `tests/test_agent_view.py` covers the allowlist, the fail-closed
  behaviour and injected leaks.
- **Reverse if:** a later phase separates the files physically — then the
  projection should be deleted and replaced by a loader that only ever reads
  the agent-visible file.
