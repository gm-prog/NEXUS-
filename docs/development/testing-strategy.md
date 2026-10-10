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

### Schema Validation Tests (`tests/test_schema_validation.py`)
- All committed incident fixtures validate against `incident-case.schema.json`
- Evaluation result schema validates against `evaluation-result.schema.json`
- Malformed JSON reported clearly (`CaseLoadError` / `SchemaLoadError`)
- Missing required properties fail
- Unknown properties fail where `additionalProperties: false`
- Unsupported schema versions fail; mixed versions reported separately
- Duplicate case IDs fail
- Filename/case_id agreement enforced
- Insufficient scenario count fails
- The declared identifier contract is slug-based, not UUID-based
- Every fixture identifier is a slug
- **The validator really enables `jsonschema.FormatChecker`** (`date-time` and
  `uuid` checkers present)
- Malformed `date-time` values are rejected in `evidence_catalog[]`,
  `incident_window` and `changes[]` (parametrised negative tests)
- UUID-shaped `service_id` values are rejected
- CLI `list` is deterministic

### Ambiguity Coverage Tests (`tests/test_ambiguity_coverage.py`)
- `required_ambiguous_cases(total)` tracks 20% of the suite with a floor of 5
- A 60-case synthetic suite with only 5 ambiguous cases **fails**
- A 60-case synthetic suite with 12 ambiguous cases passes
- The error message states the ratio requirement

### Agent-View / Anti-Leakage Tests (`tests/test_agent_view.py`)
- The projection contains exactly the allowlisted keys
- Every evaluator-only key is absent from the projection
- `affected_services[].impact` and `evidence_catalog[].synthetic_fixture_note`
  are dropped
- No evaluator-only value reaches the projection (value-level scan)
- An unclassified top-level key **fails closed** (`AgentViewError`)
- Injected leaks are detected: ground-truth values in evidence summaries,
  `must_not_claim` text in symptoms, remediation text in `environment`,
  alternative-diagnosis text in a change summary
- Allowlists match the schema properties (drift guard in both directions)

### Execution Policy Tests (`tests/test_execution_policy.py`)
- Every fixture step declares all four classification fields
- No step mutates state automatically; no automated production mutation
- Tools that imply mutation are never classified `read_only`
- `staging_experiment` steps target staging/sandbox only
- Negative cases: missing class, read-only mutation, automated mutation,
  production experiment, misclassified mutating tool
- JSON Schema rejects the same violations independently

### CLI Tests (`tests/test_cli.py`)
- `nexus-benchmark validate` exits 0 on success
- `nexus-benchmark validate --case INC-XXX` works
- `nexus-benchmark validate --case UNKNOWN` fails with clear error
- `nexus-benchmark list` produces deterministic output
- Output explicitly states validator does not evaluate AI quality
- Asset resolution is independent of the working directory
- `NEXUS_BENCHMARKS_DIR` override works and a broken override is rejected
- **Installed-executable smoke tests** run `--help`, `list` and `validate` as
  a subprocess from a directory outside the repository
- The `[project.scripts]` target exists and is callable

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

Implemented as an allowlisted projection, not a blocklist — see
[ADR-0010](../decisions/ADR-0010-agent-view-projection.md).

```python
from nexus_benchmarks.agent_view import build_agent_view

agent_input = build_agent_view(case)  # allowlist, fails closed
ground_truth = case["ground_truth"]  # never passed to the agent
score(evaluate(agent_input), ground_truth)
```

CI checks:
- No evaluator-only key survives the projection
- No evaluator-only value appears in the serialised projection
- An unclassified top-level key aborts the projection
- Injected leaks are detected (the tests are non-vacuous by construction)
- `expected_diagnosis.must_not_claim` validated

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
- Install dependencies (pip install -e ".[dev]" build)
- Ruff format check
- Ruff lint                       # lint.ignore = []
- Pytest (schema, ambiguity, agent-view, execution policy, CLI)
- nexus-benchmark --help / list / validate      # installed console script
- python -m build
- ./scripts/wheel_smoke_test.sh   # wheel in a clean venv, outside the checkout
```
Runs on Python 3.11 and 3.12, triggered by pushes and pull requests against
`master`.

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
├── conftest.py                  # Shared fixtures (schemas, corpus)
├── test_schema_validation.py    # Schema + fixtures + format + composition
├── test_ambiguity_coverage.py   # 20% ambiguity ratio invariant
├── test_agent_view.py           # Agent-visible / evaluator-only boundary
├── test_execution_policy.py     # Verification-step execution classes
├── test_cli.py                  # CLI + installed-executable smoke tests
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