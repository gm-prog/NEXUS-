#!/usr/bin/env python3
"""
NEXUS Benchmark Validation CLI

Validates incident case fixtures against JSON schemas and checks cross-file
invariants (unique IDs, minimum counts, ambiguity coverage, verification-step
execution policy, and agent-view separation from ground truth).
"""

import json
import math
import sys
from pathlib import Path

import click
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from nexus_benchmarks.agent_view import find_leaks
from nexus_benchmarks.assets import (
    EVALUATION_SCHEMA_NAME,
    INCIDENT_SCHEMA_NAME,
    INCIDENTS_DIR_NAME,
    SCHEMA_DIR_NAME,
    find_benchmarks_root,
)
from nexus_benchmarks.errors import CaseLoadError, SchemaLoadError
from nexus_benchmarks.execution_policy import check_case_execution_policy
from nexus_benchmarks.temporal import check_case_temporal_integrity

BENCHMARKS_ROOT = find_benchmarks_root()
SCHEMA_DIR = BENCHMARKS_ROOT / SCHEMA_DIR_NAME
INCIDENTS_DIR = BENCHMARKS_ROOT / INCIDENTS_DIR_NAME

INCIDENT_SCHEMA_FILE = SCHEMA_DIR / INCIDENT_SCHEMA_NAME
EVALUATION_SCHEMA_FILE = SCHEMA_DIR / EVALUATION_SCHEMA_NAME

MIN_TOTAL_CASES = 20
MIN_AMBIGUITY_CASES = 5
MIN_AMBIGUITY_RATIO = 0.20
SUPPORTED_SCHEMA_VERSION = "1.0.0"

AMBIGUOUS_TYPES = {"ambiguous", "insufficient_evidence"}


def load_schema(path: Path) -> dict:
    """Load a JSON schema file and meta-validate it."""
    try:
        with Path(path).open(encoding="utf-8") as handle:
            schema = json.load(handle)
        Draft202012Validator.check_schema(schema)
    except (json.JSONDecodeError, SchemaError, OSError) as error:
        raise SchemaLoadError(path, str(error)) from error
    return schema


def load_case(filepath: Path) -> dict:
    """Load an incident case file."""
    try:
        with Path(filepath).open(encoding="utf-8") as handle:
            case = json.load(handle)
    except (json.JSONDecodeError, OSError) as error:
        raise CaseLoadError(filepath, str(error)) from error
    return case


def build_validator(schema: dict) -> Draft202012Validator:
    """Build a Draft 2020-12 validator with real format checking enabled.

    ``jsonschema`` does not assert ``format`` unless a ``FormatChecker`` is
    supplied, so without this the declared ``date-time`` and ``uuid`` formats
    would be documentation only.
    """
    return Draft202012Validator(schema, format_checker=FormatChecker())


def discover_cases() -> list[Path]:
    """Discover all incident case files in deterministic order."""
    return sorted(INCIDENTS_DIR.glob("INC-*.json"))


def validate_case(case: dict, validator: Draft202012Validator, filepath: Path) -> list[str]:
    """Validate a single case against the schema. Returns list of error messages."""
    errors = []
    try:
        validator.validate(case)
    except ValidationError as error:
        location = (
            " -> ".join(str(part) for part in error.absolute_path)
            if error.absolute_path
            else "root"
        )
        errors.append(f"{filepath.name}: {location}: {error.message}")
    return errors


def required_ambiguous_cases(total_count: int) -> int:
    """Minimum ambiguous/insufficient-evidence cases for a benchmark of this size.

    The documented policy is "at least 20% of the suite", with an absolute floor
    so that a small suite still carries ambiguous cases. Expressing it as a
    ratio keeps the invariant true as the benchmark grows: 5 ambiguous cases is
    25% of 20 but only 8% of 60.
    """
    return max(MIN_AMBIGUITY_CASES, math.ceil(total_count * MIN_AMBIGUITY_RATIO))


def check_composition(cases: list[dict]) -> list[str]:
    """Check cross-file invariants. Returns list of error messages."""
    errors = []
    case_ids: dict[str, str] = {}
    schema_versions: set[str] = set()
    ambiguous_count = 0
    total_count = len(cases)

    for i, case in enumerate(cases):
        case_id = case.get("case_id")
        schema_version = case.get("schema_version")
        scenario_type = case.get("scenario_type")

        if not case_id:
            errors.append(f"Case at index {i}: missing case_id")
            continue

        if case_id in case_ids:
            errors.append(
                f"Duplicate case_id: {case_id} (in {case_ids[case_id]} and case index {i})"
            )
        else:
            case_ids[case_id] = f"index {i}"

        if schema_version:
            schema_versions.add(schema_version)

        if scenario_type in AMBIGUOUS_TYPES:
            ambiguous_count += 1

    if total_count < MIN_TOTAL_CASES:
        errors.append(f"Insufficient total cases: {total_count} < {MIN_TOTAL_CASES}")

    required_ambiguous = required_ambiguous_cases(total_count)
    if ambiguous_count < required_ambiguous:
        errors.append(
            f"Insufficient ambiguous/insufficient_evidence cases: {ambiguous_count} < "
            f"{required_ambiguous} (needs at least {MIN_AMBIGUITY_RATIO:.0%} of "
            f"{total_count} cases, floor {MIN_AMBIGUITY_CASES})"
        )

    if len(schema_versions) > 1:
        errors.append(f"Multiple schema versions found: {sorted(schema_versions)}")

    if schema_versions and SUPPORTED_SCHEMA_VERSION not in schema_versions:
        errors.append(
            f"Unsupported schema version(s): {sorted(schema_versions)}. "
            f"Expected: {SUPPORTED_SCHEMA_VERSION}"
        )

    return errors


def check_benchmark_policy(cases: list[dict]) -> list[str]:
    """Check per-case invariants that are not expressible as JSON Schema alone.

    Each check is called per case and is structurally defensive, so a malformed
    case yields a controlled diagnostic instead of an exception.
    """
    errors: list[str] = []
    for case in cases:
        errors.extend(check_case_execution_policy(case))
        errors.extend(check_case_temporal_integrity(case))
        errors.extend(find_leaks(case))
    return errors


#: Checks that cannot run meaningfully on a case that failed schema validation.
DEPENDENT_CHECKS = "execution policy, temporal integrity and agent-view separation"


def validate_all(
    incident_schema: dict, selected_case_id: str | None = None
) -> tuple[bool, list[str]]:
    """Validate all cases or a specific case. Returns (success, errors)."""
    all_errors: list[str] = []
    case_files = discover_cases()

    if not case_files:
        return False, ["No incident case files found"]

    incident_validator = build_validator(incident_schema)

    cases_to_validate = []
    for filepath in case_files:
        case = load_case(filepath)
        if not isinstance(case, dict):
            all_errors.append(
                f"{filepath.name}: root value must be a JSON object, got {_type_name(case)}"
            )
            continue
        if selected_case_id:
            if case.get("case_id") == selected_case_id:
                cases_to_validate.append((filepath, case))
        else:
            cases_to_validate.append((filepath, case))

    if selected_case_id and not cases_to_validate:
        return False, [f"Case not found: {selected_case_id}"]

    if selected_case_id and len(cases_to_validate) > 1:
        return False, [f"Multiple cases claim ID: {selected_case_id}"]

    schema_valid_cases = []
    for filepath, case in cases_to_validate:
        case_errors = validate_case(case, incident_validator, filepath)
        all_errors.extend(case_errors)
        if case_errors:
            # Policy, temporal and projection checks assume the schema holds.
            # Running them on a structurally invalid case would raise.
            all_errors.append(f"{filepath.name}: skipped {DEPENDENT_CHECKS} checks")
            continue
        schema_valid_cases.append(case)

    all_errors.extend(check_benchmark_policy(schema_valid_cases))

    if not selected_case_id:
        all_errors.extend(check_composition([case for _, case in cases_to_validate]))

    return len(all_errors) == 0, all_errors


def list_cases() -> list[dict]:
    """List all cases with key metadata."""
    results = []
    for filepath in discover_cases():
        case = load_case(filepath)
        if not isinstance(case, dict):
            results.append({
                "case_id": filepath.stem,
                "title": f"<malformed: {_type_name(case)}>",
                "category": "",
                "scenario_type": "",
                "difficulty": "",
            })
            continue
        results.append({
            "case_id": case.get("case_id", "UNKNOWN"),
            "title": case.get("title", ""),
            "category": case.get("category", ""),
            "scenario_type": case.get("scenario_type", ""),
            "difficulty": case.get("difficulty", ""),
        })
    return results


def _type_name(value: object) -> str:
    return "null" if value is None else type(value).__name__


@click.group()
def cli() -> None:
    """NEXUS Benchmark Validation CLI."""


@cli.command()
@click.option("--case", "case_id", help="Validate specific case by ID")
def validate(case_id: str | None) -> None:
    """Validate benchmark case files against schema."""
    click.echo("Loading schemas...")
    incident_schema = load_schema(INCIDENT_SCHEMA_FILE)
    load_schema(EVALUATION_SCHEMA_FILE)
    click.echo(f"Schema version: {incident_schema.get('$id', 'unknown')}")

    click.echo("Validating cases...")
    success, errors = validate_all(incident_schema, case_id)

    if errors:
        click.echo("\nValidation Errors:", err=True)
        for error in errors:
            click.echo(f"  - {error}", err=True)
        click.echo(f"\nTotal errors: {len(errors)}", err=True)
    elif case_id:
        click.echo(f"\nCase {case_id}: VALID")
    else:
        case_count = len(discover_cases())
        click.echo(f"\nAll {case_count} cases: VALID")
        click.echo("Composition checks: PASSED")
        click.echo("Execution policy checks: PASSED")
        click.echo("Temporal integrity checks: PASSED")
        click.echo("Agent-view separation checks: PASSED")

    click.echo("\nNote: This validator checks schema compliance and benchmark hygiene only.")
    click.echo("It does NOT evaluate AI diagnosis quality or accuracy.")

    sys.exit(0 if success else 1)


@cli.command(name="list")
def list_command() -> None:
    """List all incident cases."""
    cases = list_cases()
    if not cases:
        click.echo("No cases found")
        return

    click.echo(f"{'CASE_ID':<12} {'TITLE':<50} {'CATEGORY':<25} {'TYPE':<20} {'DIFFICULTY'}")
    click.echo("-" * 120)
    for case in cases:
        click.echo(
            f"{case['case_id']:<12} {case['title']:<50} {case['category']:<25} "
            f"{case['scenario_type']:<20} {case['difficulty']}"
        )


def main() -> None:
    """Console-script entry point declared in ``[project.scripts]``."""
    cli()


if __name__ == "__main__":
    main()
