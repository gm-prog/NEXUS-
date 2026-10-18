"""Malformed-input robustness (audit §4).

A fixture that is valid JSON but structurally invalid must produce a
deterministic diagnostic and a non-zero exit — never a Python traceback.
"""

from copy import deepcopy

import pytest
from click.testing import CliRunner

import nexus_benchmarks.cli as cli_module
from nexus_benchmarks.agent_view import build_agent_view, find_leaks
from nexus_benchmarks.cli import check_composition, cli, list_cases, validate_all
from nexus_benchmarks.errors import NexusBenchmarkError
from nexus_benchmarks.execution_policy import check_case_execution_policy
from nexus_benchmarks.temporal import check_case_temporal_integrity

TRACEBACK_MARKERS = ("Traceback (most recent call last)", "AttributeError", "TypeError")


def valid_case(corpus) -> dict:
    return deepcopy(corpus[0])


@pytest.fixture
def runner():
    return CliRunner()


MALFORMED_ROOTS = {
    "top-level array": [],
    "top-level string": "not-a-case",
    "top-level null": None,
    "top-level number": 42,
}


@pytest.mark.parametrize("root", list(MALFORMED_ROOTS.values()), ids=list(MALFORMED_ROOTS))
def test_malformed_root_is_controlled(root):
    for check in (
        check_case_execution_policy,
        check_case_temporal_integrity,
        find_leaks,
    ):
        errors = check(root)
        assert errors and all("must be a JSON object" in error for error in errors)
    with pytest.raises(NexusBenchmarkError) as excinfo:
        build_agent_view(root)
    assert "must be a JSON object" in str(excinfo.value)


@pytest.mark.parametrize("root", list(MALFORMED_ROOTS.values()), ids=list(MALFORMED_ROOTS))
def test_malformed_root_via_cli(runner, workspace, root):
    """The CLI must report it and exit non-zero without a traceback."""
    workspace.write_case("INC-900-broken.json", root)
    success, errors = validate_all(cli_module.load_schema(cli_module.INCIDENT_SCHEMA_FILE))
    assert not success
    assert any("root value must be a JSON object" in error for error in errors)

    result = runner.invoke(cli, ["validate"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert "root value must be a JSON object" in result.output
    for marker in TRACEBACK_MARKERS:
        assert marker not in result.output


MALFORMED_FIELDS = {
    "evidence_catalog is a string": ("evidence_catalog", "not-an-array"),
    "evidence_catalog is null": ("evidence_catalog", None),
    "evidence_catalog contains null": ("evidence_catalog", [None]),
    "evidence_catalog contains a string": ("evidence_catalog", ["nope"]),
    "incident_window is a string": ("incident_window", "nope"),
    "incident_window is null": ("incident_window", None),
    "required_checks is a string": ("required_checks", "nope"),
    "required_checks contains null": ("required_checks", [None]),
    "changes is null": ("changes", None),
    "changes contains null": ("changes", [None]),
    "affected_services is null": ("affected_services", None),
    "initial_symptoms is an object": ("initial_symptoms", {"symptom": "x"}),
    "required_checks is null": ("required_checks", None),
    "required_checks contains an array": ("required_checks", [[]]),
    "required_checks missing nested fields": ("required_checks", [{}]),
    "incident_window is an array": ("incident_window", []),
    "incident_window missing nested fields": ("incident_window", {}),
    "evidence_catalog missing nested fields": ("evidence_catalog", [{}]),
    "changes missing nested fields": ("changes", [{}]),
    "ground_truth is null": ("ground_truth", None),
    "expected_diagnosis is null": ("expected_diagnosis", None),
    "case_id is an array": ("case_id", ["INC-900"]),
    "schema_version is an array": ("schema_version", ["1.0.0"]),
    "scenario_type is an array": ("scenario_type", ["single_cause"]),
}


@pytest.mark.parametrize(
    ("field", "value"), list(MALFORMED_FIELDS.values()), ids=list(MALFORMED_FIELDS)
)
def test_malformed_field_is_controlled(corpus, field, value):
    case = valid_case(corpus)
    case[field] = value
    for check in (
        check_case_execution_policy,
        check_case_temporal_integrity,
        find_leaks,
    ):
        errors = check(case)
        assert isinstance(errors, list)
        assert all(isinstance(error, str) for error in errors)


@pytest.mark.parametrize(
    ("field", "value"), list(MALFORMED_FIELDS.values()), ids=list(MALFORMED_FIELDS)
)
def test_malformed_field_via_cli(runner, workspace, corpus, field, value):
    case = valid_case(corpus)
    case[field] = value
    workspace.write_case("INC-900-broken.json", case)

    result = runner.invoke(cli, ["validate"])
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert field in result.output and "Validation Errors" in result.output
    assert "dependent checks NOT RUN" in result.output
    for marker in TRACEBACK_MARKERS:
        assert marker not in result.output, f"{field}: CLI emitted a traceback"


def test_policy_checks_are_skipped_for_schema_invalid_cases(workspace, corpus):
    """A schema-invalid case must not have dependent checks run on it."""
    case = valid_case(corpus)
    case["evidence_catalog"] = [None]
    workspace.write_case("INC-900-broken.json", case)

    success, errors = validate_all(cli_module.load_schema(cli_module.INCIDENT_SCHEMA_FILE))
    assert not success
    assert any("dependent checks NOT RUN" in error for error in errors)
    assert any("Composition checks: NOT RUN" in error for error in errors)
    # The structural defect is reported once, by the schema layer.
    assert any(
        "None is not of type 'object'" in error or "not of type" in error for error in errors
    )


def test_list_command_survives_a_malformed_case(workspace):
    workspace.write_case("INC-900-broken.json", None)
    cases = list_cases()
    assert cases
    assert any("malformed" in case["title"] for case in cases)


def test_missing_only_case_id_is_reported(workspace, corpus):
    case = valid_case(corpus)
    del case["case_id"]
    workspace.write_case("INC-900-broken.json", case)
    success, errors = validate_all(cli_module.load_schema(cli_module.INCIDENT_SCHEMA_FILE))
    assert not success
    assert errors


def test_empty_incident_directory_is_reported(runner, workspace):
    assert not any(workspace.incidents.iterdir())
    result = runner.invoke(cli, ["validate"])
    assert result.exit_code != 0
    assert "No incident case files found" in result.output


@pytest.mark.parametrize("root", list(MALFORMED_ROOTS.values()), ids=list(MALFORMED_ROOTS))
def test_installed_cli_reports_malformed_root(run_cli, root):
    result = run_cli({"INC-900-malformed.json": root}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "root value must be a JSON object" in output
    assert "dependent checks NOT RUN" in output
    assert not any(marker in output for marker in TRACEBACK_MARKERS)


@pytest.mark.parametrize(
    ("field", "value"), list(MALFORMED_FIELDS.values()), ids=list(MALFORMED_FIELDS)
)
def test_installed_cli_reports_malformed_field(run_cli, sample_case, field, value):
    sample_case["case_id"] = "INC-900"
    sample_case[field] = value
    result = run_cli({"INC-900-malformed.json": sample_case}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert field in output and "Validation Errors" in output
    assert "dependent checks NOT RUN" in output
    assert not any(marker in output for marker in TRACEBACK_MARKERS)


@pytest.mark.parametrize(
    "key", ["environment", "incident_window", "evidence_catalog", "changes", "required_checks"]
)
def test_missing_nested_structure_has_a_useful_cli_diagnostic(run_cli, sample_case, key):
    sample_case["case_id"] = "INC-900"
    del sample_case[key]
    result = run_cli({"INC-900-missing.json": sample_case}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert f"'{key}' is a required property" in output
    assert "dependent checks NOT RUN" in output
    assert "Traceback" not in output


@pytest.mark.parametrize(
    "case",
    [
        None,
        [],
        "string",
        {"case_id": []},
        {"case_id": "INC-900", "schema_version": []},
        {"case_id": "INC-900", "scenario_type": []},
    ],
)
def test_composition_does_not_crash_on_invalid_identity_shapes(case):
    errors = check_composition([case])
    assert errors and all(isinstance(error, str) for error in errors)


def test_one_invalid_case_does_not_skip_a_valid_cases_policy(
    workspace, sample_case, incident_schema
):
    workspace.write_case("INC-900-invalid.json", None)
    sample_case["evidence_catalog"][0]["event_time"] = "2030-01-01T00:00:00Z"
    workspace.write_case("INC-001-future.json", sample_case)
    success, errors = validate_all(incident_schema)
    assert not success
    assert any("is after investigation_cutoff" in error for error in errors)
    assert any("root value must be a JSON object" in error for error in errors)


def test_selected_malformed_file_is_not_hidden_by_case_not_found(runner, workspace):
    workspace.write_case("INC-900-invalid.json", None)
    result = runner.invoke(cli, ["validate", "--case", "INC-900"])
    assert result.exit_code == 1
    assert "root value must be a JSON object" in result.output
    assert "Case not found" not in result.output
