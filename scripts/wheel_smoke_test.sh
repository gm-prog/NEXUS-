#!/usr/bin/env bash
# Build the wheel, install it into a clean virtual environment, and run the
# console script from a working directory outside the repository.
#
# This proves the packaged benchmark assets (schemas and incident fixtures)
# travel with the distribution, which an editable install cannot demonstrate.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/nexus-wheel-smoke-XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> Building wheel and sdist from ${REPO_ROOT}"
python -m build --outdir "${WORKDIR}/dist" "${REPO_ROOT}"

echo "==> Wheel contents (benchmark assets must be present)"
SMOKE_DIST_DIR="${WORKDIR}/dist" SMOKE_REPO_ROOT="${REPO_ROOT}" python - <<'PY'
import os
import sys
import zipfile
from pathlib import Path

root = Path(os.environ["SMOKE_REPO_ROOT"])
wheel = next(Path(os.environ["SMOKE_DIST_DIR"]).glob("*.whl"))
fixture_prefix = "nexus_benchmarks/benchmarks/incidents/"
expected = {
    fixture_prefix + path.name: path
    for path in sorted((root / "benchmarks" / "incidents").glob("INC-*.json"))
}
required = {
    "nexus_benchmarks/cli.py",
    "nexus_benchmarks/agent_view.py",
    "nexus_benchmarks/execution_policy.py",
    "nexus_benchmarks/temporal.py",
    "nexus_benchmarks/benchmarks/schema/incident-case.schema.json",
    "nexus_benchmarks/benchmarks/schema/evaluation-result.schema.json",
}
with zipfile.ZipFile(wheel) as archive:
    names = set(archive.namelist())
    missing = sorted(required - names)
    packaged = {name for name in names if name.startswith(fixture_prefix) and name.endswith(".json")}
    mismatched = sorted(
        name for name, path in expected.items()
        if name in names and archive.read(name) != path.read_bytes()
    )
    print(f"    {len(packaged)} incident fixtures packaged (expected {len(expected)})")
    if missing or packaged != set(expected) or mismatched:
        print(f"    MISSING: {missing}")
        print(f"    FIXTURE MANIFEST DIFFERENCE: {sorted(packaged ^ set(expected))}")
        print(f"    FIXTURE BYTE DIFFERENCE: {mismatched}")
        sys.exit(1)
print("    Manifest and fixture bytes match the checkout: OK")
PY

echo "==> Creating a clean virtual environment"
python -m venv "${WORKDIR}/venv"
"${WORKDIR}/venv/bin/python" -m pip install --quiet --upgrade pip
"${WORKDIR}/venv/bin/python" -m pip install --quiet "${WORKDIR}"/dist/*.whl

echo "==> Running the installed CLI from ${WORKDIR} (outside the repository)"
cd "${WORKDIR}"
"${WORKDIR}/venv/bin/nexus-benchmark" --help
"${WORKDIR}/venv/bin/nexus-benchmark" list
"${WORKDIR}/venv/bin/nexus-benchmark" validate

echo "==> Wheel smoke test PASSED"
