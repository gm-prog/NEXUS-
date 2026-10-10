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
SMOKE_DIST_DIR="${WORKDIR}/dist" python - <<'PY'
import glob
import os
import sys
import zipfile

wheel = glob.glob(os.environ["SMOKE_DIST_DIR"] + "/*.whl")[0]
names = zipfile.ZipFile(wheel).namelist()
required = [
    "nexus_benchmarks/cli.py",
    "nexus_benchmarks/benchmarks/schema/incident-case.schema.json",
    "nexus_benchmarks/benchmarks/schema/evaluation-result.schema.json",
]
missing = [name for name in required if name not in names]
incidents = [name for name in names if name.startswith("nexus_benchmarks/benchmarks/incidents/")]
print(f"    {len(incidents)} incident fixtures packaged")
if missing or len(incidents) != 21:
    print(f"    MISSING: {missing}")
    sys.exit(1)
print("    OK")
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
