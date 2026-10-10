# Contributing to NEXUS

## Development Environment

- **Python:** 3.11+ (tested on 3.12)
- **Package Manager:** `pip` (standard) or `uv` (recommended for speed)
- **OS:** Linux, macOS, Windows (WSL2 recommended on Windows)

## Dependency Installation

```bash
# Standard pip
pip install -e ".[dev]"

# With uv (faster)
uv sync --dev
```

**Lockfile: none is committed.** `pyproject.toml` declares minimum version
bounds only (for example `jsonschema>=4.23.0`); it does not pin exact versions
and there is no `uv.lock`, `requirements.txt` or `poetry.lock` in the
repository. Repeatable installs are therefore *not* guaranteed today. Adopting
a lockfile and installing with `--require-hashes` / `uv sync --locked` is a
tracked Phase 1 follow-up (see [SECURITY.md](SECURITY.md#supply-chain)).

## Running Checks

All quality gates must pass before submitting changes:

```bash
# Format check
ruff format --check .

# Lint
ruff check .

# Type check (if mypy added later)
# mypy src/

# Tests
pytest

# Benchmark validation
nexus-benchmark validate
```

# Packaging: build a wheel, install it in a clean environment and run the CLI
# from a directory outside the checkout
./scripts/wheel_smoke_test.sh
```

CI runs the same commands. Do not skip checks locally.

## File & Schema Conventions

### Benchmark Incident Cases

- Location: `benchmarks/incidents/INC-XXX-descriptive-name.json`
- Must validate against `benchmarks/schema/incident-case.schema.json`
- `case_id` must match filename prefix (`INC-XXX`)
- `schema_version` must be current (see schema)
- All timestamps: ISO 8601 UTC (`2024-01-15T10:30:00Z`). They are really
  validated — `rfc3339-validator` is a runtime dependency and the CLI enables
  `jsonschema.FormatChecker`.
- Identifiers are **stable slugs**, not UUIDs: services match
  `^svc-[a-z0-9]+(?:-[a-z0-9]+)*$` (e.g. `svc-001-payment`), environments match
  `^env-[a-z0-9]+(?:-[a-z0-9]+)*$` (e.g. `env-prod-us-east-1`).
- Ground truth is kept out of the agent-visible projection — see below.

### Agent-Visible vs Evaluator-Only Data

An incident case file deliberately mixes two audiences. Only the allowlist in
`src/nexus_benchmarks/agent_view.py` (`AGENT_VISIBLE_ROOT_KEYS` plus the
per-object allowlists) may be shown to an investigator:

| Agent-visible | Evaluator-only (never shown) |
|---------------|------------------------------|
| `schema_version`, `case_id`, `environment`, `incident_window`, `initial_symptoms`, `affected_services` (`service_id`, `service_name` only), `evidence_catalog` (minus `synthetic_fixture_note`), `changes` | `title`, `category`, `scenario_type`, `difficulty`, `description`, `ground_truth`, `expected_diagnosis`, `misleading_or_confounding_signals`, `acceptable_alternatives`, `required_checks`, `remediation_guidance`, `tags` |

The projection **fails closed**: an unclassified top-level key aborts the
projection instead of being forwarded. `tests/test_agent_view.py` pins this
boundary and proves it is non-vacuous by injecting leaks.

### Verification Steps (`required_checks[]`)

Every entry must declare `execution_class`, `target_environment`,
`mutates_state` and `automated_execution_allowed`:

| `execution_class` | Meaning | `mutates_state` | `automated_execution_allowed` | `target_environment` |
|-------------------|---------|-----------------|-------------------------------|----------------------|
| `read_only` | Observation only | `false` | `true` | any |
| `staging_experiment` | Proposed controlled experiment | `true` | `false` | `staging` / `sandbox` |
| `human_approval_required` | Needs an explicit human gate | `true` | `false` | any |

A tool whose name implies mutation (`toggle_feature_flag`,
`execute_db_command`, `cache_warmup`, ...) may never be classified
`read_only`. The registry lives in `src/nexus_benchmarks/execution_policy.py`
and is enforced by `nexus-benchmark validate`.

### Adding a New Incident Case

1. Copy an existing case as template
2. Assign next sequential `INC-XXX` ID
3. Fill all required fields per schema
4. Ensure `scenario_type` is accurate (`single_cause`, `multi_factor`, `ambiguous`, `insufficient_evidence`)
5. Classify every `required_checks[]` entry (see the table above)
6. Keep at least 20% of the suite ambiguous/insufficient-evidence — the CLI
   enforces the ratio over the whole benchmark, not a fixed count of five
7. Run `nexus-benchmark validate` — must pass
8. Run `pytest` — all tests must pass

### Modifying an Existing Case

**Never silently change scenario meaning.** If a case's ground truth, evidence, or expected diagnosis changes:

1. Increment `schema_version` in the case file if structure changes
2. Document the change in an ADR (see below)
3. Update any affected evaluation baselines
4. Ensure `nexus-benchmark validate` still passes
5. CI will catch composition regressions (count, ambiguity coverage)

## Branch / Commit / PR Conventions

- Branch: `feat/short-description`, `fix/short-description`, `docs/short-description`
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- PR title: Same format as commit
- PR description: What, why, testing done, any benchmark impact

## When an ADR Is Required

Create an Architecture Decision Record (in `docs/decisions/`) when:

- Adding/removing a major dependency or infrastructure component
- Changing the benchmark schema version
- Changing the CLI interface or output format
- Introducing a new evaluation metric
- Changing the incident lifecycle or evidence model
- Any decision with significant trade-offs or future impact

Use the template in `docs/decisions/README.md`.

## Code Style

- Ruff handles formatting and linting (see `pyproject.toml`)
- Line length: 100
- Double quotes
- Type hints on public functions
- No unnecessary comments — code should be self-documenting

## Security

- Never commit secrets, API keys, tokens, or production data
- `.env` files are gitignored; use `.env.example` for templates
- Report security issues via SECURITY.md process