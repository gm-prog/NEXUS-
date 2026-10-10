"""Malformed-input robustness (audit §4).

A fixture that is valid JSON but structurally invalid must produce a
deterministic diagnostic and a non-zero exit — never a Python traceback.
"""

from copy import deepcopy

import pytest
from click.testing import CliRunner

import nexus_benchmarks.cli as cli_module
from nexus_benchmarks.agent_view import build_agent_view, find_leaks
from nexus_benchmarks.cli import cli, list_cases, validate_all
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
    with pytest.raises(Exception) as excinfo:
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
    assert result.exit_code != 0
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
    assert result.exit_code != 0
    for marker in TRACEBACK_MARKERS:
        assert marker not in result.output, f"{field}: CLI emitted a traceback"


def test_policy_checks_are_skipped_for_schema_invalid_cases(workspace, corpus):
    """A schema-invalid case must not have dependent checks run on it."""
    case = valid_case(corpus)
    case["evidence_catalog"] = [None]
    workspace.write_case("INC-900-broken.json", case)

    success, errors = validate_all(cli_module.load_schema(cli_module.INCIDENT_SCHEMA_FILE))
    assert not success
    assert any("skipped" in error for error in errors)
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
