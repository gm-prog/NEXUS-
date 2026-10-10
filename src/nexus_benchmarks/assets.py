"""Locating the benchmark schema and incident fixture directories.

The benchmark assets live at the repository root in ``benchmarks/``. For the
installed CLI to work from a built wheel (not just from an editable checkout)
the same directory is also shipped as package data under
``nexus_benchmarks/benchmarks/`` — see ``[tool.hatch.build.targets.wheel]`` in
``pyproject.toml``. Resolution order:

1. ``NEXUS_BENCHMARKS_DIR`` environment variable (explicit, authoritative
   override),
2. packaged data next to this module (wheel / non-editable install),
3. ``benchmarks/`` next to any ancestor of this module (editable install or
   source checkout).
"""

import os
from pathlib import Path

from nexus_benchmarks.errors import BenchmarkAssetsNotFoundError

BENCHMARK_DIR_NAME = "benchmarks"
SCHEMA_DIR_NAME = "schema"
INCIDENTS_DIR_NAME = "incidents"
INCIDENT_SCHEMA_NAME = "incident-case.schema.json"
EVALUATION_SCHEMA_NAME = "evaluation-result.schema.json"

ENV_OVERRIDE_VAR = "NEXUS_BENCHMARKS_DIR"


def candidate_roots() -> list[Path]:
    """Directories that may hold the benchmark assets, in priority order."""
    roots: list[Path] = []
    override = os.environ.get(ENV_OVERRIDE_VAR)
    if override:
        roots.append(Path(override))

    package_root = Path(__file__).resolve().parent
    roots.append(package_root / BENCHMARK_DIR_NAME)
    roots.extend(parent / BENCHMARK_DIR_NAME for parent in package_root.parents)
    return roots


def find_benchmarks_root() -> Path:
    """Return the directory that holds ``schema/`` and ``incidents/``.

    If ``NEXUS_BENCHMARKS_DIR`` is set it is authoritative: a wrong override is
    reported rather than silently falling back to another location.
    """
    candidates = candidate_roots()
    override = os.environ.get(ENV_OVERRIDE_VAR)
    searched = [Path(override)] if override else candidates
    for candidate in searched:
        if (candidate / SCHEMA_DIR_NAME / INCIDENT_SCHEMA_NAME).is_file():
            return candidate
    raise BenchmarkAssetsNotFoundError(searched, ENV_OVERRIDE_VAR)
