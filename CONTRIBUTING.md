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

Lockfile: `uv.lock` (if using uv) or `requirements.txt` generated via `pip freeze`. The project uses a single `pyproject.toml` for all dependency metadata.

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

CI runs the same commands. Do not skip checks locally.

## File & Schema Conventions

### Benchmark Incident Cases

- Location: `benchmarks/incidents/INC-XXX-descriptive-name.json`
- Must validate against `benchmarks/schema/incident-case.schema.json`
- `case_id` must match filename prefix (`INC-XXX`)
- `schema_version` must be current (see schema)
- All timestamps: ISO 8601 with explicit timezone (e.g., `2024-01-15T10:30:00Z`)
- Ground truth separated from agent-visible evidence

### Adding a New Incident Case

1. Copy an existing case as template
2. Assign next sequential `INC-XXX` ID
3. Fill all required fields per schema
4. Ensure `scenario_type` is accurate (`single_cause`, `multi_factor`, `ambiguous`, `insufficient_evidence`)
5. Run `nexus-benchmark validate` — must pass
6. Run `pytest` — all tests must pass

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