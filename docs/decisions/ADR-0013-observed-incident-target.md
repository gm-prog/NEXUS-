# ADR-0013: Score the Observed Incident, Not a Hypothetical Latent Defect

- Status: Accepted
- Date: 2026-10-10

## Context

INC-013 contained conflicting instructions. Both old and new feature-flag paths
fail at a degraded external recommendation engine, and its answer note said
that degradation fully explains the observed symptoms. Nevertheless, it was
labelled `ambiguous`, accepted an unproven new-code defect as a diagnosis, and
recommended a flag rollback to discover a cause already supported by the
retained comparison traces.

Uncertainty about whether the new code would work against a healthy dependency
is not uncertainty about the cause of the **observed** outage. An intermediate
commit's rationale about high-confidence alternatives did not resolve that
target mismatch and is superseded by this decision.

## Decision

- INC-013 is `single_cause`, category `dependency_regression`, ground-truth type
  `dependency_failure`. Require the dependency evidence and both path traces;
  do not require local-change attribution.
- Remove the hypothetical code-defect alternative from its answer key. Forbid
  claims that the flag caused the outage **or** that its code is proven
  defect-free against a healthy dependency.
- Make its staging toggle a non-critical, optional post-diagnosis resilience
  experiment. No future result is assumed or required to support the diagnosis.
- Align its symptoms, expected diagnosis, causal chain and remediation guidance
  with that observed-incident target. Preserve every original evidence item,
  change and synthetic timestamp. Retain the legacy filename for stable links.

Reclassification leaves four uncertainty cases in the original 21. Do **not**
weaken `max(5, ceil(total * 0.20))` or relabel another scenario for a green result.
Instead, add INC-022 as a genuinely ambiguous contrasting frozen snapshot:
regional provider degradation, partial root traces lacking failure origins, no
flag-off holdout, and changed response handling. Both hypotheses can explain
its observed errors; the decisive comparison is genuinely missing. All of its
records precede or equal its cutoff, and no experiment result is fabricated.

The suite becomes 22 cases: 16 single-cause, 1 multi-factor, 3 ambiguous and
2 insufficient-evidence (5/22 = 22.7% uncertainty). No model-evaluation baseline
exists; future consumers must version scenario semantics rather than comparing
these revised cases with an earlier answer key silently.

## Trade-offs and Scope

Adding one reviewed ambiguity scenario is slightly larger than reclassification
alone, but preserves the useful coverage policy without corrupting another
label. The correction remains fixture work, not an evaluator, runtime or fault
injection implementation.

Manual review also identified material questions outside this targeted fix:
INC-016's double-count arithmetic versus its stated baseline, and INC-019's
plain SELECT versus its claimed write-blocking lock mechanism. They are recorded
in the phase status report, not silently rewritten or claimed validated by
passing JSON Schema checks. INC-017's populated trigger and optional attribution
are not contradictory by themselves: attribution is not required when the
relative primary contribution is unresolved.

## Validation / Reversal Criteria

`tests/test_fixture_semantics.py` pins the observed-incident target, discriminating
path evidence, lack of latent-defect alternatives and non-critical experiment
in INC-013; it contrasts INC-022's missing comparison and unknown future result.
General confidence/evidence-reference checks remain in schema tests. These are
consistency assertions, not measured AI diagnosis accuracy. Revisit with fixture
author sign-off or a separately versioned change of benchmark question.
