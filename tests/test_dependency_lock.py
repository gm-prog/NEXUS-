"""Exercise the real lock checker and the no-isolation build-closure guard.

These tests require the pinned uv tool; absence is a failure, never a skip.
All subprocess checks are offline and operate on disposable manifest copies.
"""

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def uv_path():
    executable = shutil.which("uv")
    assert executable is not None, "Install uv 0.13.0 and put it on PATH (see CONTRIBUTING.md)"
    return executable


@pytest.fixture
def locked_project(tmp_path):
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(REPO_ROOT / name, tmp_path / name)
    return tmp_path


def test_lock_is_current_without_network_or_updates(uv_path, locked_project):
    before = (locked_project / "uv.lock").read_bytes()
    result = _check_lock(uv_path, locked_project)
    assert result.returncode == 0, result.stderr
    assert (locked_project / "uv.lock").read_bytes() == before


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("click>=8.1.0", "click>=8.2.0"),
        ("ruff>=0.6.0", "ruff>=0.7.0"),
        ("hatchling>=1.25.0", "hatchling>=1.26.0"),
    ],
)
def test_lock_rejects_runtime_lint_and_build_manifest_drift(uv_path, locked_project, old, new):
    manifest = locked_project / "pyproject.toml"
    text = manifest.read_text(encoding="utf-8")
    assert old in text
    manifest.write_text(text.replace(old, new, 1), encoding="utf-8")
    before = (locked_project / "uv.lock").read_bytes()
    result = _check_lock(uv_path, locked_project)
    assert result.returncode == 1, result.stderr
    assert "lockfile" in result.stderr and "needs to be updated" in result.stderr
    assert (locked_project / "uv.lock").read_bytes() == before


def test_build_system_only_drift_cannot_bypass_locked_setup(uv_path, locked_project):
    manifest = locked_project / "pyproject.toml"
    text = manifest.read_text(encoding="utf-8")
    old = 'requires = ["hatchling>=1.25.0"]'
    new = 'requires = ["hatchling>=1.26.0"]'
    assert old in text
    manifest.write_text(text.replace(old, new), encoding="utf-8")
    # uv itself does not lock build-system.requires; the explicit mirrored
    # dev-constraint guard closes this real bypass before the editable build.
    assert _check_lock(uv_path, locked_project).returncode == 0
    scripts = locked_project / "scripts"
    scripts.mkdir()
    shutil.copyfile(REPO_ROOT / "scripts" / "locked_sync.sh", scripts / "locked_sync.sh")
    env = _offline_env() | {"PATH": str(Path(uv_path).parent) + os.pathsep + os.environ["PATH"]}
    result = subprocess.run(
        ["bash", str(scripts / "locked_sync.sh")],
        cwd=locked_project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Build requirements must also be declared in the locked dev extra" in result.stderr


def test_lock_contains_complete_versioned_hashed_closure():
    manifest = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    assert manifest["tool"]["uv"]["required-version"] == "==0.13.0"
    assert set(manifest["build-system"]["requires"]) <= set(
        manifest["project"]["optional-dependencies"]["dev"]
    )
    packages = lock["package"]
    names = {package["name"] for package in packages}
    assert {"build", "pytest", "pytest-cov", "ruff", "hatchling", "editables"} <= names
    for package in packages:
        assert package["version"]
        for dependency in package.get("dependencies", []):
            assert dependency["name"] in names
        for dependencies in package.get("optional-dependencies", {}).values():
            assert all(dependency["name"] in names for dependency in dependencies)
        if package["source"] == {"editable": "."}:
            continue  # This checkout is built locally, not fetched from an index.
        artifacts = package.get("wheels", []) + [package["sdist"]]
        assert artifacts
        assert all(re.fullmatch(r"sha256:[0-9a-f]{64}", item["hash"]) for item in artifacts)
        assert all(item["url"].startswith("https://files.pythonhosted.org/") for item in artifacts)


def _check_lock(uv_path, project):
    return subprocess.run(
        [
            uv_path,
            "lock",
            "--check",
            "--offline",
            "--directory",
            str(project),
            "--python",
            sys.executable,
        ],
        cwd=project,
        env=_offline_env(),
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _offline_env():
    return os.environ | {
        "UV_OFFLINE": "true",
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_PYTHON": sys.executable,
    }
