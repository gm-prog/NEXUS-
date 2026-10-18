# Expected Results Directory

This directory is reserved for versioned results produced by the future evaluation runner. **No evaluation result files or versioned baseline currently exist.** Valid fixtures and the result schema do not mean evaluation has run.

## Structure (planned)

```
expected-results/
├── baseline/       # created after a real, reviewed baseline run
├── regression/     # optional run-to-baseline reports
└── README.md
```

## Result Format

Completed results must conform to `benchmarks/schema/evaluation-result.schema.json`. That JSON Schema is a **result-format contract only**; it does not implement a scorer, define all scoring semantics, run an evaluator, or constitute a baseline.

## Evaluation Lifecycle and Current Status

| Artifact / stage | Status at Phase 0 | Planned home / gate |
|---|---|---|
| Result schema | **Present** | Phase 0; format validation only |
| Evaluation contract / scorer specification | **Not implemented** | Design checkpoint at or before Phase 4 entry; separate explicit authorization required. Evaluation Contract v0 remains unauthorized until approval. |
| Evaluation runner and scorer | **Not implemented** | Phase 4, after a contract is separately specified and authorized |
| Stored results and versioned baseline | **Absent** | Phase 4, after an actual successful run across all current benchmark cases |
| Regression comparator / CI automation | **Not implemented** | Phase 6; future automation, not an active Phase 0 gate |

The schema, contract, runner, result files, versioned baseline, and regression comparator are separate artifacts. Do not describe a later stage as present merely because an earlier stage exists.

## Baseline Establishment (planned Phase 4)

After the contract and runner have been separately authorized and implemented:

1. Run the evaluator across **all current cases** listed in [the canonical benchmark inventory](../README.md) (22 cases at the 2026-10-19 baseline; recheck the inventory when running).
2. Validate each output against `evaluation-result.schema.json`.
3. Store results under `baseline/` with run timestamp, source commit, evaluator/contract version, corpus identity, and enough provenance to reproduce the run.
4. Review and version the baseline before Phase 5 claims score improvement.
5. Preserve failed/incomplete runs as diagnostic artifacts where useful, but never label them the accepted baseline.

No result files are created by this documentation change, and no baseline is claimed.

## Regression Detection (planned Phase 6)

Future CI may compare valid evaluation runs against the reviewed baseline:

- Score degradation greater than 5% on a metric: candidate regression alert.
- Invalid evidence references or specified hallucination failures: evaluation failure.
- Latency/cost increase greater than 20%: candidate performance regression.

These are **future thresholds**, not active CI checks or measured outcomes. Final semantics must be specified before enforcement.
