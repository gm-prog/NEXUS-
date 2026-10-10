"""Shared fixtures for the NEXUS benchmark test-suite."""

from copy import deepcopy
from pathlib import Path

import pytest

from nexus_benchmarks.cli import (
    EVALUATION_SCHEMA_FILE,
    INCIDENT_SCHEMA_FILE,
    build_validator,
    discover_cases,
    load_case,
    load_schema,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def incident_schema():
    return load_schema(INCIDENT_SCHEMA_FILE)


@pytest.fixture(scope="session")
def evaluation_schema():
    return load_schema(EVALUATION_SCHEMA_FILE)


@pytest.fixture(scope="session")
def incident_validator(incident_schema):
    """Validator used across tests — built the same way the CLI builds it."""
    return build_validator(incident_schema)


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
