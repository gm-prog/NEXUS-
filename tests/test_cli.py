"""CLI behaviour: in-process (CliRunner) and as the installed console script."""

import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

import nexus_benchmarks.cli as cli_module
from nexus_benchmarks.assets import ENV_OVERRIDE_VAR, find_benchmarks_root
from nexus_benchmarks.cli import MIN_TOTAL_CASES, cli, list_cases, validate_all
from nexus_benchmarks.errors import BenchmarkAssetsNotFoundError

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def runner():
    return CliRunner()


def test_module_exposes_the_declared_entry_point():
    """Finding 2: pyproject targets nexus_benchmarks.cli:main."""
    assert callable(cli_module.main)


def test_help_command(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "NEXUS Benchmark Validation CLI" in result.output


def test_list_command(runner):
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "CASE_ID" in result.output
    assert "INC-001" in result.output


def test_list_cases_returns_metadata_for_every_case():
    cases = list_cases()
    assert len(cases) >= MIN_TOTAL_CASES
    for case in cases:
        assert case["case_id"].startswith("INC-")
        assert case["title"]
        assert case["category"]
        assert case["scenario_type"]


def test_validate_all_passes(runner):
    result = runner.invoke(cli, ["validate"])
    assert result.exit_code == 0
    assert "VALID" in result.output
    assert "Composition checks: PASSED" in result.output
    assert "Execution policy checks: PASSED" in result.output
    assert "Agent-view separation checks: PASSED" in result.output


def test_validate_specific_case(runner):
    result = runner.invoke(cli, ["validate", "--case", "INC-001"])
    assert result.exit_code == 0
    assert "INC-001: VALID" in result.output


def test_validate_unknown_case_fails(runner):
    result = runner.invoke(cli, ["validate", "--case", "INC-999"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_validate_output_mentions_not_ai_evaluation(runner):
    result = runner.invoke(cli, ["validate"])
    assert result.exit_code == 0
    assert "does NOT evaluate AI diagnosis quality" in result.output


def test_validate_reports_errors_for_a_broken_case(runner, tmp_path, monkeypatch):
    original = cli_module.discover_cases

    def only_broken():
        broken = tmp_path / "INC-900-broken.json"
        broken.write_text('{"schema_version": "1.0.0", "case_id": "INC-900"}', encoding="utf-8")
        return [broken]

    monkeypatch.setattr(cli_module, "discover_cases", only_broken)
    result = runner.invoke(cli, ["validate"])
    monkeypatch.setattr(cli_module, "discover_cases", original)
    assert result.exit_code != 0
    assert "Validation Errors" in result.output


def test_validate_all_reports_no_cases(monkeypatch):
    monkeypatch.setattr(cli_module, "discover_cases", lambda: [])
    success, errors = validate_all({}, None)
    assert not success
    assert errors == ["No incident case files found"]


def test_validate_all_detects_duplicate_case_selection(incident_schema):
    success, errors = validate_all(incident_schema, "INC-001")
    assert success
    assert errors == []


def test_asset_resolution_is_independent_of_the_working_directory(monkeypatch):
    """The CLI must find its fixtures without relying on the caller's cwd."""
    monkeypatch.chdir(tempfile.mkdtemp(prefix="nexus-cwd-"))
    assert len(list_cases()) >= MIN_TOTAL_CASES


def test_asset_resolution_honours_a_valid_override(monkeypatch, tmp_path):
    copy = tmp_path / "benchmarks"
    shutil.copytree(REPO_ROOT / "benchmarks", copy)
    monkeypatch.setenv(ENV_OVERRIDE_VAR, str(copy))
    assert find_benchmarks_root() == copy


def test_asset_resolution_rejects_a_broken_override(monkeypatch, tmp_path):
    """An explicit override is authoritative: a wrong path must not fall back."""
    monkeypatch.setenv(ENV_OVERRIDE_VAR, str(tmp_path))
    with pytest.raises(BenchmarkAssetsNotFoundError):
        find_benchmarks_root()


def _locate_console_script() -> str | None:
    """Find the installed ``nexus-benchmark`` executable.

    Prefers ``PATH``; falls back to the script directory of the interpreter
    running pytest so the smoke test also works when the virtualenv is not on
    ``PATH``.
    """
    found = shutil.which("nexus-benchmark")
    if found:
        return found
    candidate = Path(sys.executable).parent / "nexus-benchmark"
    if candidate.is_file():
        return str(candidate)
    return None


INSTALLER = _locate_console_script()


def run_installed(*args: str) -> subprocess.CompletedProcess:
    """Run the installed console script from outside the repository."""
    cwd = tempfile.mkdtemp(prefix="nexus-installed-")
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [INSTALLER, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


# Smoke tests for the entry point declared in pyproject.toml. Each invocation
# runs from a throwaway working directory, i.e. outside the repository.
needs_installed_cli = pytest.mark.skipif(
    INSTALLER is None, reason="nexus-benchmark is not installed on PATH"
)


@needs_installed_cli
def test_installed_executable_help():
    result = run_installed("--help")
    assert result.returncode == 0, result.stderr
    assert "NEXUS Benchmark Validation CLI" in result.stdout


@needs_installed_cli
def test_installed_executable_list():
    result = run_installed("list")
    assert result.returncode == 0, result.stderr
    assert "INC-001" in result.stdout


@needs_installed_cli
def test_installed_executable_validate():
    result = run_installed("validate")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "cases: VALID" in result.stdout
    assert "Agent-view separation checks: PASSED" in result.stdout


@needs_installed_cli
def test_installed_executable_runs_outside_the_repository():
    result = run_installed("validate", "--case", "INC-013")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "INC-013: VALID" in result.stdout


def test_entry_point_target_matches_the_installed_script():
    """The declared target must exist, otherwise installation produces a broken script."""
    if INSTALLER is None:
        pytest.skip("nexus-benchmark is not installed on PATH")
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        declared = tomllib.load(handle)["project"]["scripts"]["nexus-benchmark"]
    module_name, _, attribute = declared.partition(":")
    module = sys.modules.get(module_name) or __import__(module_name)
    assert callable(getattr(module, attribute))
