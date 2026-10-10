"""Schema loading, fixture validation, format enforcement and composition checks."""

import uuid
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from nexus_benchmarks.cli import (
    MIN_TOTAL_CASES,
    check_composition,
    discover_cases,
    load_case,
    load_schema,
    validate_case,
)
from nexus_benchmarks.errors import CaseLoadError, SchemaLoadError
from nexus_benchmarks.execution_policy import check_execution_policy

INCIDENT_SCHEMA_FILE = (
    Path(__file__).parent.parent / "benchmarks" / "schema" / "incident-case.schema.json"
)
EVALUATION_SCHEMA_FILE = (
    Path(__file__).parent.parent / "benchmarks" / "schema" / "evaluation-result.schema.json"
)

MALFORMED_TIMESTAMPS = [
    "not-a-timestamp",
    "2024-01-27 10:00:00",
    "2024-13-45T99:00:00Z",
    "27/01/2024T10:00:00Z",
    "2024-01-27T10:00:00",
]


def test_incident_schema_loads_and_is_a_draft_2020_12_schema(incident_schema):
    assert incident_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema#"
    Draft202012Validator.check_schema(incident_schema)


def test_evaluation_schema_loads_and_is_a_draft_2020_12_schema(evaluation_schema):
    assert evaluation_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema#"
    Draft202012Validator.check_schema(evaluation_schema)


def test_case_discovery_is_deterministic_and_minimally_sized(case_paths):
    assert len(case_paths) >= MIN_TOTAL_CASES
    assert discover_cases() == case_paths
    for path in case_paths:
        assert path.name.startswith("INC-")
        assert path.suffix == ".json"


def test_all_committed_cases_validate(incident_validator, case_paths):
    errors = []
    for path in case_paths:
        errors.extend(validate_case(load_case(path), incident_validator, path))
    assert errors == []


def test_schema_declares_slug_identifiers_not_uuids(incident_schema):
    """Finding 3: the schema and the fixtures must agree on one ID contract."""
    affected = incident_schema["properties"]["affected_services"]["items"]["properties"]
    evidence = incident_schema["properties"]["evidence_catalog"]["items"]["properties"]
    ground_truth = incident_schema["properties"]["ground_truth"]["properties"]

    for field in (
        affected["service_id"],
        evidence["service_id"],
        evidence["environment_id"],
        incident_schema["properties"]["changes"]["items"]["properties"]["service_id"],
        ground_truth["primary_service_id"],
    ):
        assert field["$ref"] in {"#/$defs/service_id", "#/$defs/environment_id"}
        assert "format" not in field

    assert incident_schema["$defs"]["service_id"]["pattern"] == ("^svc-[a-z0-9]+(?:-[a-z0-9]+)*$")
    assert incident_schema["$defs"]["environment_id"]["pattern"] == (
        "^env-[a-z0-9]+(?:-[a-z0-9]+)*$"
    )


def test_every_fixture_identifier_is_a_slug(corpus):
    for case in corpus:
        case_id = case["case_id"]
        for service in case["affected_services"]:
            assert service["service_id"].startswith("svc-"), case_id
        for evidence in case["evidence_catalog"]:
            assert evidence["service_id"].startswith("svc-"), case_id
            assert evidence["environment_id"].startswith("env-"), case_id
        for change in case["changes"]:
            assert change["service_id"].startswith("svc-"), case_id


def test_validator_actually_enables_format_checking(incident_validator):
    """A Draft 2020-12 validator with no FormatChecker silently ignores `format`."""
    checker = incident_validator.format_checker
    assert checker is not None
    assert "date-time" in checker.checkers, (
        "rfc3339-validator must be installed for date-time format checking"
    )
    assert "uuid" in checker.checkers


@pytest.mark.parametrize("timestamp", MALFORMED_TIMESTAMPS)
def test_malformed_event_time_is_rejected(incident_validator, sample_case, timestamp):
    sample_case["evidence_catalog"][0]["event_time"] = timestamp
    assert validate_case(sample_case, incident_validator, Path("test.json"))


@pytest.mark.parametrize("timestamp", MALFORMED_TIMESTAMPS)
def test_malformed_incident_window_is_rejected(incident_validator, sample_case, timestamp):
    sample_case["incident_window"]["investigation_cutoff"] = timestamp
    assert validate_case(sample_case, incident_validator, Path("test.json"))


def test_malformed_change_timestamp_is_rejected(incident_validator, sample_case):
    sample_case["changes"][0]["timestamp"] = "yesterday"
    assert validate_case(sample_case, incident_validator, Path("test.json"))


def test_well_formed_timestamp_is_accepted(incident_validator, sample_case):
    sample_case["evidence_catalog"][0]["event_time"] = "2024-01-27T10:00:00Z"
    assert validate_case(sample_case, incident_validator, Path("test.json")) == []


def test_uuid_service_id_is_rejected(incident_validator, sample_case):
    sample_case["affected_services"][0]["service_id"] = str(uuid.uuid4())
    errors = validate_case(sample_case, incident_validator, Path("test.json"))
    assert errors and "service_id" in errors[0]


def test_malformed_environment_id_is_rejected(incident_validator, sample_case):
    sample_case["evidence_catalog"][0]["environment_id"] = "PROD US EAST 1"
    assert validate_case(sample_case, incident_validator, Path("test.json"))


def test_missing_required_properties_fail(incident_validator):
    errors = validate_case(
        {"schema_version": "1.0.0", "case_id": "INC-999"},
        incident_validator,
        Path("test.json"),
    )
    assert errors
    assert any("title" in error or "category" in error for error in errors)


def test_unknown_properties_fail_when_additional_properties_is_false(
    incident_validator, sample_case
):
    sample_case["unknown_field_that_should_fail"] = "value"
    errors = validate_case(sample_case, incident_validator, Path("test.json"))
    assert errors
    assert any("unknown_field" in error for error in errors)


def test_malformed_json_is_reported(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(CaseLoadError) as excinfo:
        load_case(bad_file)
    assert "Invalid JSON" in str(excinfo.value)


def test_missing_schema_file_is_reported(tmp_path):
    with pytest.raises(SchemaLoadError):
        load_schema(tmp_path / "does-not-exist.json")


def test_filename_matches_case_id(case_paths):
    for path in case_paths:
        case = load_case(path)
        assert path.name.startswith(case["case_id"]), (
            f"{path.name}: case_id {case['case_id']} does not match the filename"
        )


def test_unsupported_schema_version_fails_composition(corpus):
    cases = deepcopy(corpus)
    for case in cases:
        case["schema_version"] = "9.9.9"
    assert any("Unsupported schema version" in e for e in check_composition(cases))


def test_duplicate_case_ids_fail(corpus):
    cases = [corpus[0], corpus[0]]
    assert any("Duplicate case_id" in e for e in check_composition(cases))


def test_insufficient_total_cases_fails(corpus):
    assert any(
        "Insufficient total cases" in e for e in check_composition(corpus[: MIN_TOTAL_CASES - 1])
    )


def test_mixed_schema_versions_are_reported(corpus):
    cases = deepcopy(corpus)
    cases[1]["schema_version"] = "2.0.0"
    errors = check_composition(cases)
    assert any("Multiple schema versions" in e for e in errors)
    # A migration in progress still contains supported cases, so the
    # "unsupported" error is reserved for a corpus that dropped support.
    assert not any("Unsupported schema version" in e for e in errors)


def test_corpus_without_the_supported_version_fails(corpus):
    cases = deepcopy(corpus)
    for case in cases:
        case["schema_version"] = "2.0.0"
    assert any("Unsupported schema version" in e for e in check_composition(cases))


def test_committed_corpus_has_no_composition_errors(corpus):
    assert check_composition(corpus) == []


def test_committed_corpus_has_no_execution_policy_errors(corpus):
    assert check_execution_policy(corpus) == []
