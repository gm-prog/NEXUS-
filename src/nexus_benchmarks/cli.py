#!/usr/bin/env python3
"""
NEXUS Benchmark Validation CLI

Validates incident case fixtures against JSON schemas and checks
cross-file invariants (unique IDs, minimum counts, ambiguity coverage).
"""

import json
import sys
from pathlib import Path

import click
from jsonschema import Draft202012Validator, ValidationError
from jsonschema.exceptions import SchemaError

SCHEMA_DIR = Path(__file__).parent.parent.parent / "benchmarks" / "schema"
INCIDENTS_DIR = Path(__file__).parent.parent.parent / "benchmarks" / "incidents"

INCIDENT_SCHEMA_FILE = SCHEMA_DIR / "incident-case.schema.json"
EVALUATION_SCHEMA_FILE = SCHEMA_DIR / "evaluation-result.schema.json"

MIN_TOTAL_CASES = 20
MIN_AMBIGUITY_CASES = 5
SUPPORTED_SCHEMA_VERSION = "1.0.0"

AMBIGUOUS_TYPES = {"ambiguous", "insufficient_evidence"}


def load_schema(path: Path) -> dict:
    """Load and validate a JSON schema file."""
    try:
        with Path(path).open() as f:
            schema = json.load(f)
        Draft202012Validator.check_schema(schema)
        return schema
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in schema {path}: {e}")
    except SchemaError as e:
        raise click.ClickException(f"Invalid schema {path}: {e}")


def load_case(filepath: Path) -> dict:
    """Load a case file."""
    try:
        with Path(filepath).open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in {filepath}: {e}")


def discover_cases() -> list[Path]:
    """Discover all incident case files in deterministic order."""
    return sorted(INCIDENTS_DIR.glob("INC-*.json"))


def validate_case(case: dict, validator: Draft202012Validator, filepath: Path) -> list[str]:
    """Validate a single case against the schema. Returns list of error messages."""
    errors = []
    try:
        validator.validate(case)
    except ValidationError as e:
        path_str = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        errors.append(f"{filepath.name}: {path_str}: {e.message}")
    return errors


def check_composition(cases: list[dict]) -> list[str]:
    """Check cross-file invariants. Returns list of error messages."""
    errors = []
    case_ids = {}
    schema_versions = set()
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

    if ambiguous_count < MIN_AMBIGUITY_CASES:
        errors.append(
            f"Insufficient ambiguous/insufficient_evidence cases: {ambiguous_count} < {MIN_AMBIGUITY_CASES}"
        )

    if len(schema_versions) > 1:
        errors.append(f"Multiple schema versions found: {sorted(schema_versions)}")

    if SUPPORTED_SCHEMA_VERSION not in schema_versions and schema_versions:
        errors.append(
            f"Unsupported schema version(s): {sorted(schema_versions)}. Expected: {SUPPORTED_SCHEMA_VERSION}"
        )

    return errors


def validate_all(
    incident_schema: dict, selected_case_id: str | None = None
) -> tuple[bool, list[str]]:
    """Validate all cases or a specific case. Returns (success, errors)."""
    all_errors = []
    case_files = discover_cases()

    if not case_files:
        return False, ["No incident case files found"]

    incident_validator = Draft202012Validator(incident_schema)

    cases_to_validate = []
    for filepath in case_files:
        case = load_case(filepath)
        if selected_case_id:
            if case.get("case_id") == selected_case_id:
                cases_to_validate.append((filepath, case))
        else:
            cases_to_validate.append((filepath, case))

    if selected_case_id and not cases_to_validate:
        return False, [f"Case not found: {selected_case_id}"]

    if selected_case_id and len(cases_to_validate) > 1:
        return False, [f"Multiple cases claim ID: {selected_case_id}"]

    for filepath, case in cases_to_validate:
        all_errors.extend(validate_case(case, incident_validator, filepath))

    if not selected_case_id:
        cases = [case for _, case in cases_to_validate]
        all_errors.extend(check_composition(cases))

    return len(all_errors) == 0, all_errors


def list_cases() -> list[dict]:
    """List all cases with key metadata."""
    results = []
    for filepath in discover_cases():
        case = load_case(filepath)
        results.append({
            "case_id": case.get("case_id", "UNKNOWN"),
            "title": case.get("title", ""),
            "category": case.get("category", ""),
            "scenario_type": case.get("scenario_type", ""),
            "difficulty": case.get("difficulty", ""),
        })
    return results


@click.group()
def cli():
    """NEXUS Benchmark Validation CLI"""
    pass


@cli.command()
@click.option("--case", "case_id", help="Validate specific case by ID")
def validate(case_id: str | None):
    """Validate benchmark case files against schema."""
    click.echo("Loading schemas...")
    incident_schema = load_schema(INCIDENT_SCHEMA_FILE)
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

    click.echo("\nNote: This validator checks schema compliance and benchmark hygiene only.")
    click.echo("It does NOT evaluate AI diagnosis quality or accuracy.")

    sys.exit(0 if success else 1)


@cli.command()
def list():
    """List all incident cases."""
    cases = list_cases()
    if not cases:
        click.echo("No cases found")
        return

    click.echo(f"{'CASE_ID':<12} {'TITLE':<50} {'CATEGORY':<25} {'TYPE':<20} {'DIFFICULTY'}")
    click.echo("-" * 120)
    for case in cases:
        click.echo(
            f"{case['case_id']:<12} {case['title']:<50} {case['category']:<25} {case['scenario_type']:<20} {case['difficulty']}"
        )


if __name__ == "__main__":
    cli()
