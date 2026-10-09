# NEXUS Testing Strategy

> **Status:** Documented for Phase 0. Implementation in later phases.

---

## Testing Philosophy

NEXUS testing follows a layered approach aligned with the architecture:

1. **Unit Tests** — Pure functions (deterministic intelligence, correlation, baselines)
2. **Integration Tests** — Component boundaries (ingestion → storage, storage → intelligence)
3. **Contract Tests** — Schema validation (JSON Schema, OpenAPI)
4. **Benchmark Tests** — Frozen scenario evaluation (the core Phase 0 deliverable)
5. **Regression Tests** — Benchmark score comparison across versions
6. **Property-Based Tests** — Invariant checking (evidence reference validity, no hallucination)

---

## Phase 0 Testing (Implemented)

### Schema Validation Tests
- All committed incident fixtures validate against `incident-case.schema.json`
- Evaluation result schema validates against `evaluation-result.schema.json`
- Malformed JSON reported clearly
- Missing required properties fail
- Unknown properties fail where `additionalProperties: false`
- Unsupported schema versions fail
- Duplicate case IDs fail
- Filename/case_id agreement enforced
- Insufficient scenario count fails
- Insufficient ambiguity coverage fails
- CLI `list` is deterministic

### CLI Tests
- `nexus-benchmark validate` exits 0 on success
- `nexus-benchmark validate --case INC-XXX` works
- `nexus-benchmark validate --case UNKNOWN` fails with clear error
- `nexus-benchmark list` produces deterministic output
- Output explicitly states validator does not evaluate AI quality

### Benchmark Hygiene Tests
- Ground truth separated from agent-visible evidence
- Expected diagnosis evidence IDs exist in evidence catalog
- Ambiguous cases have explicit ambiguity notes
- Insufficient evidence cases have explicit notes

---

## Phase 1+ Testing (Planned)

### Unit Tests (Target: >90% coverage)
- Deterministic intelligence functions (time-window alignment, deployment correlation, baselines)
- Evidence bundle assembly
- Schema validation
- Configuration parsing

### Integration Tests
- Ingestion pipeline: validation → normalization → enrichment → storage
- Storage layer: telemetry writes, application state transactions
- Intelligence queries: time-range, service filter, trace lookup
- API contracts: request/response validation

### Contract Tests
- JSON Schema for all data fixtures
- OpenAPI for HTTP APIs (when introduced)
- Protocol buffer schemas (if gRPC used)

### Benchmark Evaluation Tests (Core)
- **Frozen Scenario Evaluation**: Each benchmark case is a frozen snapshot
- **No Answer Leakage**: Evaluator loads ground truth separately, never passes to agent
- **Structured Scoring**: Metrics defined in `evaluation-result.schema.json`
- **Regression Detection**: Compare new run scores against baseline
- **Human Review**: Prose quality assessed separately

---

## Frozen Snapshot Testing (Critical)

### Principle
The investigator sees **only** information available at the investigation cutoff:
- Telemetry up to `incident_window.end`
- Code at `incident_window.end` (no future commits)
- Deployments up to `incident_window.end`
- Runbooks/docs as they existed at cutoff

### Implementation
```python
# Evaluator pseudo-code
def evaluate_case(case, agent):
    # Agent input: ONLY evidence_catalog + incident_window + affected_services + initial_symptoms
    agent_input = {
        "evidence": case["evidence_catalog"],
        "incident_window": case["incident_window"],
        "affected_services": case["affected_services"],
        "initial_symptoms": case["initial_symptoms"],
    }
    
    # Ground truth: NEVER passed to agent
    ground_truth = case["ground_truth"]
    
    # Run investigation
    result = agent.investigate(agent_input)
    
    # Score against ground truth
    return score(result, ground_truth)
```

### Anti-Leakage Checks (CI)
- `ground_truth` keys not present in `evidence_catalog` summaries
- `expected_diagnosis.must_not_claim` validated
- No future commits/deployments in evidence catalog

---

## Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Detection | Incident correctly identified | >0.95 |
| Service Localization | Primary service identified | >0.90 |
| Root Cause Accuracy | Root cause type matches | >0.85 |
| Change Attribution | Correct trigger change | >0.80 |
| Evidence Grounding | Claims reference valid evidence | >0.90 |
| Evidence Reference Validity | No hallucinated evidence IDs | 1.0 |
| Required Evidence Coverage | Key evidence referenced | >0.80 |
| Supporting Evidence Coverage | Supporting evidence acknowledged | >0.70 |
| Contradicting Evidence Coverage | Contradicting evidence acknowledged | >0.70 |
| Causal Chain Correctness | Causal links correct | >0.75 |
| False Attribution Rate | Incorrect attributions | <0.10 |
| Abstention Quality | Appropriate uncertainty expression | >0.80 |
| Investigation Coverage | Required checks performed | >0.80 |
| Tool Efficiency | Minimal redundant calls | >0.80 |

---

## Regression Testing

### Baseline Establishment
1. Run evaluation on all benchmark cases with current implementation
2. Store results in `benchmarks/expected-results/baseline/` with evaluator version
3. Tag baseline with git commit SHA

### Regression Detection
```yaml
# CI check
- Compare new run scores against baseline
- Alert if any metric degrades > 5%
- Alert if new failure modes appear (invalid refs, hallucinations)
- Alert if latency/cost increases > 20%
```

### Versioned Results
- Results include `evaluator_version`, `model_id`, `prompt_version`, `tool_set_version`
- Compare only same-version runs for regression
- Cross-version comparison for improvement tracking

---

## Property-Based Testing

### Invariants to Verify
- Every evidence reference in diagnosis exists in evidence catalog
- No evidence ID referenced more than once for same claim
- Confidence scores in [0.0, 1.0]
- Causal chain forms valid DAG (no cycles)
- Contradicting evidence acknowledged if exists in ground truth
- Agent never invents evidence IDs
- Timestamps in evidence are ≤ investigation_cutoff

### Tools
- Hypothesis (Python) for property-based tests
- QuickCheck-style for other languages

---

## Test Data Management

### Synthetic Fixtures (Phase 0)
- JSON files in `benchmarks/incidents/`
- `synthetic_fixture_note` describes what Phase 1/2 generates
- No real telemetry, no PII, no secrets

### Generated Fixtures (Phase 1+)
- Real OpenTelemetry data from demo app
- Real Git commits, deployments
- Stored in test data bucket, versioned

### Production Data (Never in Tests)
- No production telemetry in tests
- No real user data
- No real credentials

---

## CI Pipeline

### Phase 0 (Current)
```yaml
- Install dependencies
- Ruff format check
- Ruff lint
- Pytest (schema + CLI tests)
- nexus-benchmark validate
```

### Phase 1+ (Planned)
```yaml
- Install dependencies
- Ruff format check
- Ruff lint
- Pytest (unit + integration)
- Contract tests
- Build demo app
- Run demo app + fault injection
- nexus-benchmark validate
```

### Phase 4+ (Planned)
```yaml
- All above
- Run benchmark evaluation
- Compare against baseline
- Regression alert on degradation
- Publish results
```

---

## Test Organization

```
tests/
├── test_schema_validation.py    # Schema + benchmark composition (Phase 0)
├── test_cli.py                  # CLI tests (Phase 0)
├── unit/                        # Unit tests (Phase 1+)
│   ├── test_intelligence.py
│   ├── test_evidence_bundle.py
│   └── ...
├── integration/                 # Integration tests (Phase 1+)
│   ├── test_ingestion.py
│   ├── test_storage.py
│   └── ...
├── contracts/                   # Contract tests (Phase 1+)
│   ├── test_schemas.py
│   └── ...
├── benchmarks/                  # Benchmark evaluation (Phase 4+)
│   ├── test_evaluation.py
│   ├── test_regression.py
│   └── ...
└── property/                    # Property-based tests (Phase 1+)
    ├── test_invariants.py
    └── ...
```

---

## Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_schema_validation.py -v

# With coverage
pytest --cov=nexus_benchmarks --cov-report=html

# Only unit tests (when available)
pytest -m unit

# Only benchmark tests
pytest -m schema
```