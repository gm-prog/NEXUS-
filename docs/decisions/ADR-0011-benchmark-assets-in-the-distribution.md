# ADR-0011: Benchmark Assets Ship Inside the Distribution

- Status: Accepted
- Date: 2026-10-10

## Context

The CLI located schemas and fixtures by walking up from
`src/nexus_benchmarks/cli.py` to a repository-root `benchmarks/` directory.
That works for an editable install (`pip install -e .`), which is what CI used,
and hides the fact that a non-editable install cannot find its data:
inside a wheel the module lives at `site-packages/nexus_benchmarks/cli.py`, so
the same walk-up looks for `site-packages/../benchmarks` and finds nothing.

The project nevertheless publishes a console script
(`nexus-benchmark = "nexus_benchmarks.cli:main"`), so "install the package and
run the command" is part of the product contract, not just a developer
convenience.

## Decision

**The `benchmarks/` directory is shipped as package data inside the wheel**, at
`nexus_benchmarks/benchmarks/`, in addition to remaining at the repository
root.

- Build backend: **hatchling** (replacing `setuptools.build_meta`), using
  `[tool.hatch.build.targets.wheel.force-include]` to map the root
  `benchmarks/` directory into the package. This needs no duplicated copy of
  the fixtures and no build script.
- Runtime resolution lives in `src/nexus_benchmarks/assets.py` and tries, in
  order: `NEXUS_BENCHMARKS_DIR` (authoritative if set), packaged data next to
  the module, then `benchmarks/` beside any ancestor of the module (editable
  installs and source checkouts).
- `./scripts/wheel_smoke_test.sh` builds a wheel, installs it into a clean
  virtual environment and runs `nexus-benchmark --help | list | validate` from
  a temporary directory outside the checkout. It runs in CI and asserts the
  wheel contains all 21 fixtures and both schemas.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Keep setuptools and copy `benchmarks/` into `src/` at build time with a custom `build_py` | Requires a bespoke build hook; more machinery than a three-line `force-include` |
| Move the canonical fixtures into `src/nexus_benchmarks/data/` and symlink the root directory | Symbolic links in git are fragile on Windows and across archive formats |
| Document the CLI as repository-local only and drop the console script | The README and CI already document installing and running `nexus-benchmark` |

## Trade-offs and Consequences

**Pros:**

- `pip install nexus-benchmarks && nexus-benchmark validate` works from any
  directory.
- No duplicated fixture data, so the two locations cannot drift.
- The wheel smoke test makes the contract executable in CI.

**Cons:**

- Wheel size grows by the fixture corpus (~150 KB at 21 cases).
- The build backend changed, so contributors must have hatchling available
  (`pip`/`build` handle this via build isolation).
- The sdist/wheel now embed a snapshot of `benchmarks/`; a wheel built from a
  dirty working tree can differ from the committed fixtures.

## Validation / Reversal Criteria

- **Validate:** `./scripts/wheel_smoke_test.sh` passes locally and in CI.
- **Reverse if:** the CLI becomes a repository-local developer tool — then
  remove the console script, the `force-include` mapping and the packaging job,
  and say so explicitly in the README.
