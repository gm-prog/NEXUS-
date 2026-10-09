#!/usr/bin/env python3
"""Tests for CLI functionality."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from nexus_benchmarks.cli import cli, load_case, load_schema, validate_all


class TestCLICommands:
    """Test CLI commands via CliRunner."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_list_command(self, runner):
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "INC-001" in result.output
        assert "CASE_ID" in result.output

    def test_validate_all_passes(self, runner):
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_validate_specific_case(self, runner):
        result = runner.invoke(cli, ["validate", "--case", "INC-001"])
        assert result.exit_code == 0
        assert "INC-001: VALID" in result.output

    def test_validate_unknown_case_fails(self, runner):
        result = runner.invoke(cli, ["validate", "--case", "INC-999"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_validate_output_mentions_not_ai_evaluation(self, runner):
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 0
        assert "does NOT evaluate AI diagnosis quality" in result.output


class TestCLIInternals:
    """Test internal CLI functions."""

    def test_load_case(self):
        case = load_case(
            Path(__file__).parent.parent
            / "benchmarks"
            / "incidents"
            / "INC-001-null-pointer-payment.json"
        )
        assert case["case_id"] == "INC-001"
        assert case["schema_version"] == "1.0.0"

    def test_validate_all_returns_errors(self):
        incident_schema = load_schema(
            Path(__file__).parent.parent / "benchmarks" / "schema" / "incident-case.schema.json"
        )
        success, errors = validate_all(incident_schema, "INC-999")
        assert not success
        assert len(errors) > 0

    def test_validate_all_succeeds_for_valid(self):
        incident_schema = load_schema(
            Path(__file__).parent.parent / "benchmarks" / "schema" / "incident-case.schema.json"
        )
        success, errors = validate_all(incident_schema, "INC-001")
        assert success
        assert len(errors) == 0


class TestCLIEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_json_file(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ not valid json")
        with pytest.raises(Exception) as exc_info:
            load_case(bad_file)
        assert "Invalid JSON" in str(exc_info.value)

    def test_missing_schema_file(self):
        with pytest.raises(Exception):
            load_schema(Path("/nonexistent/schema.json"))

    def test_case_id_format_validation(self):
        case = load_case(
            Path(__file__).parent.parent
            / "benchmarks"
            / "incidents"
            / "INC-001-null-pointer-payment.json"
        )
        assert case["case_id"] == "INC-001"
        # Should match pattern ^INC-\d{3}$
        import re

        assert re.match(r"^INC-\d{3}$", case["case_id"])

    def test_evidence_id_format(self):
        case = load_case(
            Path(__file__).parent.parent
            / "benchmarks"
            / "incidents"
            / "INC-001-null-pointer-payment.json"
        )
        for evidence in case["evidence_catalog"]:
            import re

            assert re.match(r"^ev-[a-z0-9-]+$", evidence["evidence_id"]), (
                f"Bad evidence_id: {evidence['evidence_id']}"
            )

    def test_change_id_format(self):
        case = load_case(
            Path(__file__).parent.parent
            / "benchmarks"
            / "incidents"
            / "INC-001-null-pointer-payment.json"
        )
        for change in case["changes"]:
            import re

            assert re.match(r"^chg-[a-z0-9-]+$", change["change_id"]), (
                f"Bad change_id: {change['change_id']}"
            )

    def test_check_ids_format(self):
        case = load_case(
            Path(__file__).parent.parent
            / "benchmarks"
            / "incidents"
            / "INC-001-null-pointer-payment.json"
        )
        for check in case["required_checks"]:
            import re

            assert re.match(r"^chk-[a-z0-9-]+$", check["check_id"]), (
                f"Bad check_id: {check['check_id']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
