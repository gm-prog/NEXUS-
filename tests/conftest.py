"""Shared fixtures for the NEXUS benchmark test-suite."""

import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

import nexus_benchmarks.cli as cli_module
from nexus_benchmarks.cli import discover_cases, load_case, load_schema

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "benchmarks" / "schema"


@pytest.fixture(scope="session")
def incident_schema():
    return load_schema(cli_module.INCIDENT_SCHEMA_FILE)


@pytest.fixture(scope="session")
def evaluation_schema():
    return load_schema(cli_module.EVALUATION_SCHEMA_FILE)


@pytest.fixture(scope="session")
def incident_validator(incident_schema):
    """Validator used across tests — built the same way the CLI builds it."""
    return cli_module.build_validator(incident_schema)


@pytest.fixture(scope="session")
def case_paths():
    return discover_cases()


@pytest.fixture(scope="session")
def corpus(case_paths):
    return [load_case(path) for path in case_paths]


@pytest.fixture
def sample_case(corpus):
    """A deep copy of the first fixture, safe for tests to mutate."""
    return deepcopy(corpus[0])


def _locate_console_script() -> str | None:
    """Find the installed ``nexus-benchmark`` executable.

    Prefers ``PATH``; falls back to the script directory of the interpreter
    running pytest so subprocess tests also work when the virtualenv is not on
    ``PATH``.
    """
    candidate = Path(sys.executable).parent / "nexus-benchmark"
    if candidate.is_file():
        return str(candidate)
    return shutil.which("nexus-benchmark")


INSTALLER = _locate_console_script()


class BenchmarkWorkspace:
    """A throwaway ``benchmarks/`` tree plus helpers to populate and check it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.incidents = root / "incidents"
        self.incidents.mkdir(parents=True, exist_ok=True)

    def write_case(self, name: str, case: object) -> Path:
        path = self.incidents / name
        path.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_raw(self, name: str, text: str) -> Path:
        path = self.incidents / name
        path.write_text(text, encoding="utf-8")
        return path


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """An isolated ``benchmarks/`` tree that the CLI is pointed at."""
    root = tmp_path / "benchmarks"
    shutil.copytree(SCHEMA_DIR, root / "schema")
    monkeypatch.setattr(cli_module, "BENCHMARKS_ROOT", root)
    monkeypatch.setattr(cli_module, "SCHEMA_DIR", root / "schema")
    monkeypatch.setattr(cli_module, "INCIDENTS_DIR", root / "incidents")
    monkeypatch.setattr(
        cli_module, "INCIDENT_SCHEMA_FILE", root / "schema" / "incident-case.schema.json"
    )
    monkeypatch.setattr(
        cli_module, "EVALUATION_SCHEMA_FILE", root / "schema" / "evaluation-result.schema.json"
    )
    return BenchmarkWorkspace(root)


@pytest.fixture
def run_cli(tmp_path):
    """Run the installed console script against a throwaway benchmarks tree."""

    def _run(cases: dict[str, object], *args: str) -> subprocess.CompletedProcess:
        assert INSTALLER is not None, 'Install the CLI first: python -m pip install -e ".[dev]"'
        root = tmp_path / "benchmarks"
        shutil.copytree(SCHEMA_DIR, root / "schema")
        incidents = root / "incidents"
        incidents.mkdir(parents=True)
        for name, case in cases.items():
            (incidents / name).write_text(
                json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            [INSTALLER, "validate", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env={
                "PATH": str(Path(INSTALLER).parent),
                "NEXUS_BENCHMARKS_DIR": str(root),
                "HOME": str(tmp_path),
            },
        )

    return _run
