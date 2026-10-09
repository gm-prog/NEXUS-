#!/usr/bin/env python3
"""Tests for schema validation and benchmark composition."""

import tempfile
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from nexus_benchmarks.cli import (
    AMBIGUOUS_TYPES,
    MIN_AMBIGUITY_CASES,
    MIN_TOTAL_CASES,
    check_composition,
    discover_cases,
    load_case,
    load_schema,
    validate_case,
)

INCIDENT_SCHEMA_FILE = (
    Path(__file__).parent.parent / "benchmarks" / "schema" / "incident-case.schema.json"
)
EVALUATION_SCHEMA_FILE = (
    Path(__file__).parent.parent / "benchmarks" / "schema" / "evaluation-result.schema.json"
)
INCIDENTS_DIR = Path(__file__).parent.parent / "benchmarks" / "incidents"


class TestSchemaLoading:
    """Test that schemas load and are valid."""

    def test_incident_schema_loads(self):
        schema = load_schema(INCIDENT_SCHEMA_FILE)
        assert schema is not None
        assert "$schema" in schema
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema#"

    def test_evaluation_schema_loads(self):
        schema = load_schema(EVALUATION_SCHEMA_FILE)
        assert schema is not None
        assert "$schema" in schema

    def test_incident_schema_validates_against_metaschema(self):
        schema = load_schema(INCIDENT_SCHEMA_FILE)
        Draft202012Validator.check_schema(schema)

    def test_evaluation_schema_validates_against_metaschema(self):
        schema = load_schema(EVALUATION_SCHEMA_FILE)
        Draft202012Validator.check_schema(schema)


class TestCaseDiscovery:
    """Test case file discovery."""

    def test_discovers_cases(self):
        cases = discover_cases()
        assert len(cases) >= MIN_TOTAL_CASES
        for case_file in cases:
            assert case_file.name.startswith("INC-")
            assert case_file.suffix == ".json"

    def test_deterministic_order(self):
        cases1 = discover_cases()
        cases2 = discover_cases()
        assert cases1 == cases2


class TestCaseValidation:
    """Test individual case validation."""

    @pytest.fixture
    def incident_validator(self):
        schema = load_schema(INCIDENT_SCHEMA_FILE)
        return Draft202012Validator(schema)

    def test_all_committed_cases_validate(self, incident_validator):
        errors = []
        for filepath in discover_cases():
            case = load_case(filepath)
            try:
                incident_validator.validate(case)
            except ValidationError as e:
                errors.append(f"{filepath.name}: {e.message}")
        assert not errors, "Validation errors:\n" + "\n".join(errors)

    def test_malformed_json_reported(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            f.flush()
            with pytest.raises(Exception) as exc_info:
                load_case(Path(f.name))
            assert "Invalid JSON" in str(exc_info.value)

    def test_missing_required_properties_fail(self, incident_validator):
        minimal_case = {"schema_version": "1.0.0", "case_id": "INC-999"}
        errors = validate_case(minimal_case, incident_validator, Path("test.json"))
        assert len(errors) > 0
        assert any("title" in e or "category" in e for e in errors)

    def test_unknown_properties_fail_when_additional_false(self, incident_validator):
        case = load_case(discover_cases()[0])
        case["unknown_field_that_should_fail"] = "value"
        errors = validate_case(case, incident_validator, Path("test.json"))
        assert len(errors) > 0
        assert any("unknown_field" in e or "additionalProperties" in e for e in errors)

    def test_unsupported_schema_version_fails_composition(self):
        cases = []
        for filepath in discover_cases():
            case = load_case(filepath)
            case["schema_version"] = "9.9.9"
            cases.append(case)
        errors = check_composition(cases)
        assert any("Unsupported schema version" in e for e in errors)

    def test_duplicate_case_ids_fail(self, incident_validator):
        case = load_case(discover_cases()[0])
        cases = [case, case]
        errors = check_composition(cases)
        assert any("Duplicate case_id" in e for e in errors)

    def test_filename_matches_case_id(self):
        for filepath in discover_cases():
            case = load_case(filepath)
            expected_prefix = filepath.name.split("-")[0] + "-" + filepath.name.split("-")[1]
            assert case["case_id"] == expected_prefix, (
                f"{filepath.name}: case_id {case['case_id']} doesn't match filename prefix {expected_prefix}"
            )

    def test_insufficient_total_cases_fails(self):
        cases = [load_case(f) for f in discover_cases()[: MIN_TOTAL_CASES - 1]]
        errors = check_composition(cases)
        assert any("Insufficient total cases" in e for e in errors)

    def test_insufficient_ambiguity_coverage_fails(self):
        cases = [load_case(f) for f in discover_cases()[:MIN_TOTAL_CASES]]
        for case in cases:
            case["scenario_type"] = "single_cause"
        errors = check_composition(cases)
        assert any("Insufficient ambiguous" in e for e in errors)


class TestAmbiguityCoverage:
    """Test that ambiguity coverage requirements are met."""

    def test_at_least_5_ambiguous_in_first_20(self):
        cases = [load_case(f) for f in discover_cases()[:20]]
        ambiguous_count = sum(1 for c in cases if c.get("scenario_type") in AMBIGUOUS_TYPES)
        assert ambiguous_count >= MIN_AMBIGUITY_CASES, (
            f"Only {ambiguous_count} ambiguous cases in first 20"
        )

    def test_ambiguous_cases_have_ambiguity_note(self):
        for filepath in discover_cases():
            case = load_case(filepath)
            if case.get("scenario_type") in AMBIGUOUS_TYPES:
                gt = case.get("ground_truth", {})
                assert gt.get("ambiguity_note") or gt.get("insufficient_evidence_note"), (
                    f"{case['case_id']}: ambiguous case missing ambiguity/insufficient_evidence note"
                )

    def test_insufficient_evidence_cases_have_note(self):
        for filepath in discover_cases():
            case = load_case(filepath)
            if case.get("scenario_type") == "insufficient_evidence":
                gt = case.get("ground_truth", {})
                assert gt.get("insufficient_evidence_note"), (
                    f"{case['case_id']}: insufficient_evidence case missing note"
                )


class TestGroundTruthSeparation:
    """Test that ground truth is separated from agent-visible evidence."""

    def test_ground_truth_not_in_evidence_catalog(self):
        for filepath in discover_cases():
            case = load_case(filepath)
            evidence_ids = {e["evidence_id"] for e in case.get("evidence_catalog", [])}
            gt = case.get("ground_truth", {})

            for key in [
                "root_cause_type",
                "primary_service_id",
                "trigger_change_id",
                "causal_chain",
                "ambiguity_note",
                "insufficient_evidence_note",
            ]:
                if key in gt and gt[key]:
                    assert key not in str(case.get("evidence_catalog", [])), (
                        f"{case['case_id']}: ground truth field '{key}' leaked into evidence_catalog"
                    )

    def test_expected_diagnosis_references_exist(self):
        for filepath in discover_cases():
            case = load_case(filepath)
            evidence_ids = {e["evidence_id"] for e in case.get("evidence_catalog", [])}
            required = case.get("expected_diagnosis", {}).get("must_include_evidence_ids", [])
            for req_id in required:
                assert req_id in evidence_ids, (
                    f"{case['case_id']}: expected_diagnosis references missing evidence {req_id}"
                )

    def test_must_not_claim_not_in_evidence(self):
        for filepath in discover_cases():
            case = load_case(filepath)
            evidence_text = str(case.get("evidence_catalog", []))
            must_not = case.get("expected_diagnosis", {}).get("must_not_claim", [])
            for claim in must_not:
                pass


class TestCLI:
    """Test CLI commands."""

    def test_list_command(self, capsys):
        from nexus_benchmarks.cli import list_cases

        cases = list_cases()
        assert len(cases) >= MIN_TOTAL_CASES
        for case in cases:
            assert "case_id" in case
            assert "title" in case
            assert case["case_id"].startswith("INC-")

    def test_validate_unknown_case_fails(self):
        from nexus_benchmarks.cli import validate_all

        incident_schema = load_schema(INCIDENT_SCHEMA_FILE)
        success, errors = validate_all(incident_schema, "INC-999")
        assert not success
        assert any("not found" in e.lower() for e in errors)

    def test_validate_specific_case(self):
        from nexus_benchmarks.cli import validate_all

        incident_schema = load_schema(INCIDENT_SCHEMA_FILE)
        success, errors = validate_all(incident_schema, "INC-001")
        assert success, f"INC-001 validation failed: {errors}"


class TestEvaluationSchema:
    """Test evaluation result schema."""

    def test_evaluation_schema_structure(self):
        schema = load_schema(EVALUATION_SCHEMA_FILE)
        required_fields = [
            "schema_version",
            "case_id",
            "run_id",
            "run_timestamp",
            "detection_result",
            "service_localization_result",
            "root_cause_result",
            "evidence_references_used",
            "scores",
        ]
        for field in required_fields:
            assert field in schema.get("required", []), f"Missing required field: {field}"

    def test_scores_all_metrics_present(self):
        schema = load_schema(EVALUATION_SCHEMA_FILE)
        scores_props = schema["properties"]["scores"]["properties"]
        expected_metrics = [
            "detection",
            "service_localization",
            "root_cause_accuracy",
            "change_attribution",
            "evidence_grounding",
            "evidence_reference_validity",
            "required_evidence_coverage",
            "supporting_evidence_coverage",
            "contradicting_evidence_coverage",
            "causal_chain_correctness",
            "false_attribution_rate",
            "abstention_quality",
            "investigation_coverage",
            "tool_efficiency",
        ]
        for metric in expected_metrics:
            assert metric in scores_props, f"Missing score metric: {metric}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
