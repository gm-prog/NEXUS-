# Expected Results Directory

This directory will contain expected evaluation results for benchmark runs.

## Structure

```
expected-results/
├── baseline/
│   ├── INC-001.result.json
│   ├── INC-002.result.json
│   └── ...
├── regression/
│   └── ...
└── README.md
```

## Result Format

Results follow `benchmarks/schema/evaluation-result.schema.json`.

Each result represents a completed evaluation run against a benchmark scenario, containing:
- Detection, localization, root-cause accuracy scores
- Evidence grounding and reference validity
- Supporting/contradicting evidence coverage
- Uncertainty behavior assessment
- Tool efficiency metrics
- Latency and cost measurements

## Status

**Phase 0:** No evaluation results exist yet. This directory is reserved for Phase 4+ when the AI investigator is implemented and benchmark runs produce measurable results.

## Baseline Establishment

When the investigator is implemented (Phase 4+):
1. Run evaluation on all benchmark cases
2. Store results in `baseline/` with evaluator version tag
3. Future runs compare against baseline for regression detection

## Regression Detection

CI will compare new evaluation runs against baseline:
- Score degradation > 5% on any metric = regression alert
- New failure modes (invalid evidence refs, hallucinations) = failure
- Latency/cost increase > 20% = performance regression