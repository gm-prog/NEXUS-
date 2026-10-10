# Contributing to NEXUS

## Development Environment

- **Python:** 3.11 or 3.12 (CI tests both)
- **Dependency tool:** `uv` **0.13.0**, enforced by `tool.uv.required-version`
- **OS:** Linux/macOS with Bash; Windows via WSL2

## Dependency Installation

Install the pinned uv release in a **separate tooling environment**, not in the
project `.venv` (sync intentionally removes undeclared packages). For example,
using an existing tooling virtualenv:

```bash
python -m pip install --only-binary=:all: --no-deps "uv==0.13.0"
uv --version
```

CI instead uses a verified full-SHA `setup-uv` action with this exact version
and its release checksums. Bootstrap uv is tooling, not an independently
resolved application environment.

```bash
./scripts/locked_sync.sh
source .venv/bin/activate
uv lock --check                # fails on manifest/lock drift; never rewrites
```

`uv.lock` commits the full runtime/dev/build closure with versions and artifact
SHA-256 hashes. The setup script stages locked third-party wheels with
`uv sync --locked --extra dev --no-install-project --no-build`, then installs
this project with `--locked --no-build-isolation`. `hatchling`, the `build`
frontend and the PEP 660 helper `editables` are in the locked dev closure.
No isolated build environment or unbounded pip upgrade is used.

**Build requirements must be mirrored verbatim in the dev extra.** uv does not
include `build-system.requires` in its project dependency metadata check; the
setup script rejects build-only changes that evade `uv lock --check`. Update
both declarations together, then regenerate the lock. A real subprocess
regression covers this bypass. Runtime/lint/build drift integration probes
retain explicit uv mismatch/no-rewrite assertions and may read PyPI index
metadata on a cold cache; an additional empty-cache test proves current-lock
acceptance and stale-lock fail-closed behavior offline. These probes operate
only on temporary copies and never install a differently resolved environment.

### Deliberate Lock Updates

```bash
# After a manifest edit (including mirrored build constraints):
uv lock

# For an intentional, scoped upgrade instead:
uv lock --upgrade-package PACKAGE_NAME
# Or an explicitly reviewed full refresh: uv lock --upgrade

./scripts/locked_sync.sh
# Run every quality gate below, including wheel smoke on the updated closure.
git diff -- pyproject.toml uv.lock
```

Commit the manifest and lock changes together. CI never regenerates the lock
for you, and uses `--locked` rather than `--frozen` to detect metadata drift.
Use `.venv/bin/python -m build --no-isolation` for a manual build; the wheel
smoke script additionally exports hash-locked runtime requirements, rejects
source builds, and installs the local wheel `--no-deps --no-index` in a fresh
venv before checking it from outside the checkout.

These pins improve dependency repeatability, not OS/Python-patch reproducibility
or a guarantee of vulnerability-free packages. See [SECURITY.md](SECURITY.md#supply-chain).

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
  a UTC-normalised instant for cutoff comparison, preserving fractional seconds
  beyond `datetime`'s six-digit precision.
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
| `schema_version`, `case_id`, `environment`, `incident_window` (`start`, `investigation_cutoff` only), `initial_symptoms`, `affected_services` (`service_id`, `service_name` only), `evidence_catalog` (minus `synthetic_fixture_note`), `changes` | `incident_window.end`, `title`, `category`, `scenario_type`, `difficulty`, `description`, `ground_truth`, `expected_diagnosis`, `misleading_or_confounding_signals`, `acceptable_alternatives`, `required_checks`, `remediation_guidance`, `tags` |

The projection **fails closed**: an unclassified top-level key aborts the
projection instead of being forwarded. `tests/test_agent_view.py` pins this
boundary and proves it is non-vacuous by injecting leaks.

The value scan includes **all causal-chain descriptions and check outcomes**,
case-insensitively against actual projected strings (including free-form keys).
Only two reviewed case/hidden-path/visible-path/**complete-text** tuples are
exempt: an observed INC-021 symptom and an INC-006 log quotation. Copies at
other locations, changed answers and appended copies still fail. See
[ADR-0014](docs/decisions/ADR-0014-phase-0-sign-off-corrections.md).
The minimum eight-character match and paraphrase limitation remain heuristics;
manual review is required, not blanket exclusion of any answer-text category.

### Temporal Cutoff (frozen snapshot)

An investigator may only see what was known at
`incident_window.investigation_cutoff`. Two rules enforce this:

1. `incident_window.end` is **always evaluator-only**, including when it is at
   or before the cutoff. It denotes eventual resolution/observation completion,
   not the investigator's frozen input boundary.
2. Every exposed typed time is parsed as a timezone-aware RFC 3339 instant:
   `incident_window.start`, `investigation_cutoff`, evidence `event_time`,
   `collection_time`, `time_window_start`, `time_window_end`, and change
   `timestamp`. All except the cutoff itself must be at or before it. Offsets
   are normalised to UTC, never ordered as strings; fractional seconds are
   compared exactly. Naive or malformed values are errors, not silently skipped.
3. Optional aggregate/trace windows may be absent, but a supplied interval
   requires **both** endpoints in order. Both endpoints must be at/before the
   cutoff. `incident_window.start > end` is also rejected.
4. Future records are **rejected, not filtered**. `evidence_catalog` describes
   available investigation input. Both `nexus-benchmark validate` and direct
   `build_agent_view()` calls enforce this rule, so callers cannot bypass it
   by skipping schema validation.

For example, `2024-01-15T09:16:00-01:00` sorts before
`2024-01-15T10:15:00Z` as text but is a later instant. A lexicographic check
would let that record through. `tests/test_temporal_integrity.py` pins both
offset directions and equivalent instants.

Standalone timestamp-like values in projected configuration are also checked.
Free-form summaries, configuration `details`, and references still require
manual temporal/answer-leakage review. A schema drift test requires any new
**typed** date-time field to have an explicit cutoff/evaluator disposition;
this is not a claim that the validator understands arbitrary prose.

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
9. Run `pytest` — all tests must pass

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