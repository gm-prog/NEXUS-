#!/usr/bin/env bash
# Install only the committed runtime/dev/build closure. Stage the locked build
# backend first so the editable install never uses an isolated resolver.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
# The guard/build below intentionally use this fixed project environment.
export UV_PROJECT_ENVIRONMENT="${REPO_ROOT}/.venv"
uv lock --check
uv sync --locked --extra dev --no-install-project --no-build
# uv locks project dependency metadata, not build-system.requires. Require
# exact mirrored constraints so build-only edits cannot evade lock checking.
.venv/bin/python - <<'PYTHON'
import tomllib
from pathlib import Path

manifest = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
build = set(manifest["build-system"]["requires"])
dev = set(manifest["project"]["optional-dependencies"]["dev"])
unlocked = sorted(build - dev)
if unlocked:
    raise SystemExit(
        f"Build requirements must also be declared in the locked dev extra: {unlocked}. "
        "Update both constraints and run uv lock."
    )
PYTHON
uv sync --locked --extra dev --no-build-isolation
