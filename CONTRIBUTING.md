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
tracked Phase 1 follow-up, not started (owner: NEXUS maintainers; trigger:
start of Phase 1 — see [SECURITY.md](SECURITY.md#supply-chain)).

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
- All timestamps: **strict** RFC 3339 with a mandatory UTC designator or
  numeric offset (`2024-01-15T10:30:00Z`, `2024-01-15T16:00:00+05:30`). They
  are really validated twice: `rfc3339-validator` (a runtime dependency, so
  `jsonschema.FormatChecker` actually enforces `format: date-time`) checks the
  *string shape*, and `src/nexus_benchmarks/temporal.py` parses each value into
  a timezone-aware `datetime` for the cutoff comparisons below.
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

### Temporal Cutoff (frozen snapshot)

An investigator may only see what was known at
`incident_window.investigation_cutoff`. Two rules enforce this:

1. `incident_window.end` is **conditionally excluded** from the projection. It
   is dropped unless it can be *proved* to be at or before the cutoff; if the
   cutoff or the end is missing, unparseable or naive, the field is dropped.
   "Cannot prove it is in the past" must never become "assume it is in the
   past". In all 21 current fixtures `end` is after the cutoff, so today the
   field is never model-visible.
2. No agent-visible timestamp may be after the cutoff:
   `evidence_catalog[].event_time`, `.collection_time`, `.time_window_end`,
   `changes[].timestamp` and `incident_window.start`. Reversed windows
   (`start` after `end`, `time_window_start` after `time_window_end`) are also
   rejected.

Comparisons are made between timezone-aware `datetime`s in UTC, never between
strings: `2024-01-15T09:16:00-01:00` sorts *before*
`2024-01-15T10:15:00Z` as text but is a *later* instant, and a lexicographic
check would have let that future record through.
`tests/test_temporal_integrity.py` pins both directions.

This is metadata validation of what the fixture *claims*, not a runtime
control: nothing here grants, denies or executes a tool call.

### Verification Steps (`required_checks[]`)

Every entry must declare `execution_class`, `target_environment`,
`mutates_state` and `automated_execution_allowed`:

| `execution_class` | Meaning | `mutates_state` | `automated_execution_allowed` | `target_environment` |
|-------------------|---------|-----------------|-------------------------------|----------------------|
| `read_only` | Observation only | `false` | `true` | any |
| `staging_experiment` | Proposed controlled experiment | `true` | `false` | `staging` / `sandbox` |
| `human_approval_required` | Needs an explicit human gate | `true` | `false` | any |

Tool side effects come from a **positive registry**, `TOOL_REGISTRY` in
`src/nexus_benchmarks/execution_policy.py`, which names every tool the
benchmark knows about and classifies it `read_only` or `mutating`. A step may
not be `read_only` if its tool is registered mutating, and a tool registered
`read_only` may not declare `mutates_state: true`.

An **unregistered** tool name is reported and never defaults to `read_only` —
adding `set_feature_flag`, `promote_deployment` or `run_migration` to a fixture
fails `nexus-benchmark validate` until it is explicitly registered. The
prefix/exact-name patterns (`MUTATING_TOOL_PREFIXES`, `MUTATING_TOOL_NAMES`)
are kept only as defence in depth, to catch a name that is registered
`read_only` but looks mutating.

**Registering a tool is a metadata declaration, not runtime authorisation.**
A future agent must still enforce capability permissions at the tool-execution
boundary.

### Adding a New Incident Case

1. Copy an existing case as template
2. Assign next sequential `INC-XXX` ID
3. Fill all required fields per schema
4. Ensure `scenario_type` is accurate (`single_cause`, `multi_factor`, `ambiguous`, `insufficient_evidence`)
5. Classify every `required_checks[]` entry (see the table above)
6. Keep at least 20% of the suite ambiguous/insufficient-evidence — the CLI
   enforces the ratio over the whole benchmark, not a fixed count of five
7. Register any new `required_checks[].tool` in `TOOL_REGISTRY`; unregistered
   tools fail closed
8. Run `nexus-benchmark validate` — must pass
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