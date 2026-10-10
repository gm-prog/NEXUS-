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
- `affected_services[].impact`, `evidence_catalog[].synthetic_fixture_note`
  and `incident_window.end` are intentionally excluded
- No evaluator-only value reaches the projection (value-level scan)
- An unclassified top-level key **fails closed** (`AgentViewError`)
- Injected leaks are detected: ground-truth values in evidence summaries,
  `must_not_claim` text in symptoms, remediation text in `environment`,
  alternative-diagnosis text in a change summary
- Allowlists match the schema properties (drift guard in both directions)

### Execution Policy Tests (`tests/test_execution_policy.py`)
- Every fixture step declares all four classification fields
- No step mutates state automatically; no automated production mutation
- All 21 current tool names are in a positive side-effect registry; each of the
  18 read-only tools has a positive test
- Unknown names fail closed in every class; novel mutating names
  (`set_feature_flag`, `promote_deployment`, `run_migration`, `flip_switch`)
  fail the installed CLI when falsely declared read-only
- Name heuristics are defence in depth, not runtime authorization
- `staging_experiment` steps target staging/sandbox only
- Negative cases: missing class, read-only mutation, automated mutation,
  production experiment, misclassified mutating tool
- JSON Schema rejects the same violations independently

### Temporal Integrity (`tests/test_temporal_integrity.py`)
- `incident_window.end` never appears in a view, including when before cutoff
- Every typed projected time is at/before cutoff in all current fixtures
- Independent negative tests for future start, event, collection, both interval
  endpoints and change timestamps at helper, projection and installed CLI boundaries
- Timezone-aware RFC 3339 parsing, equal instants at different offsets, and both
  offset cases where text ordering gives the wrong answer
- Malformed/naive timestamps, invalid offset components, UTC overflow, paired
  and reversed intervals, and exact sub-microsecond comparisons
- Schema timestamp drift guard requires every new typed time to be classified

### Malformed Input (`tests/test_malformed_input.py`)
- Valid JSON with array/string/null/number root, invalid arrays/objects/scalars,
  null elements, missing nested structures and invalid identity/enum shapes
- Schema-invalid cases are diagnosed; dependent policy checks are NOT RUN
- Composition checks do not crash on invalid shapes; valid cases still get policy checks
- Installed subprocesses exit exactly 1 with field/file diagnostics, no traceback

### Fixture Semantics (`tests/test_fixture_semantics.py`)
- INC-013 scores the observed dependency failure, not an untested latent defect
- Its comparison traces remain required; optional experiments are not assumed performed
- INC-022 retains genuine observed-error ambiguity because failure-location and
  flag-off comparison evidence are missing
- This does not evaluate AI accuracy or prove realism of arbitrary causal prose

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
- Telemetry up to `incident_window.investigation_cutoff`
- Code at `incident_window.investigation_cutoff` (no future commits)
- Deployments up to `incident_window.investigation_cutoff`
- Runbooks/docs as they existed at cutoff

> **Correction (2026-10-10, Phase 0 audit).** This list previously read
> "`incident_window.end`". That was a contradiction: `investigation_cutoff` is
> the boundary of the frozen snapshot, and in every fixture `end` is *later*
> than the cutoff (the investigation happens mid-incident). Passing `end` to
> the agent would tell it when the incident resolved. The bullets now say
> `investigation_cutoff`, matching the invariant already listed below and the
> validator in `src/nexus_benchmarks/temporal.py`.

### Implementation
```python
# Future evaluator pseudo-code; no agent/evaluator is implemented in Phase 0.
from nexus_benchmarks.agent_view import build_agent_view


def evaluate_case(case, agent):
    agent_input = build_agent_view(case)  # allowlist + fail-closed temporal checks
    result = agent.investigate(agent_input)
    return score(result, case["ground_truth"])  # answer key stays evaluator-only
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

## Evaluation Metrics (Future Targets, Not Measured Results)

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
- Timestamps in evidence are ≤ investigation_cutoff (**enforced** by
  `check_temporal_integrity`; `incident_window.end` is always evaluator-only).
  Collection time and both interval endpoints are also bounded by the cutoff

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
- ./scripts/locked_sync.sh        # uv 0.13.0; --locked, no build isolation
- Ruff format check
- Ruff lint                       # lint.ignore = []
- Pytest (schema, ambiguity, causal-text leakage, temporal, tool policy, malformed input, semantics, lock drift, CLI)
- nexus-benchmark --help / list / validate      # installed console script
- ./scripts/wheel_smoke_test.sh   # --no-isolation build; hash-locked clean runtime venv
```
Runs on Python 3.11 and 3.12, triggered by pushes and pull requests against
`master`. Actions are full-SHA pinned. Tests exercise the real offline uv
lock checker, plus the build-system-only drift guard. The installed wheel's
fixture manifest and all fixture bytes must match the checkout; its runtime
closure is exported from the same lock and installed with required hashes,
without a second dependency resolver. Local versus exact-head hosted evidence
is recorded in [Phase 0 Status](phase-0-status.md) and PR #1.

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
├── test_temporal_integrity.py   # Cutoff, RFC 3339, offsets, windows, CLI negatives
├── test_malformed_input.py      # Controlled shape diagnostics, no tracebacks
├── test_fixture_semantics.py    # Incident target, ambiguity, arithmetic and lock evidence
├── test_dependency_lock.py      # Real offline drift rejection + complete hashed closure
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

# Schema/fixture tests
pytest tests/test_schema_validation.py -v
```