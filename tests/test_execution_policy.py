"""Verification-step execution policy (finding 5).

Mutating verification steps must be classified and must never be executable
automatically against production.
"""

from copy import deepcopy

import pytest

from nexus_benchmarks.cli import build_validator
from nexus_benchmarks.execution_policy import (
    EXECUTION_CLASSES,
    HUMAN_APPROVAL_REQUIRED,
    NON_PRODUCTION_ENVIRONMENTS,
    READ_ONLY,
    STAGING_EXPERIMENT,
    check_execution_policy,
    is_mutating_tool,
)

REQUIRED_STEP_FIELDS = (
    "execution_class",
    "target_environment",
    "mutates_state",
    "automated_execution_allowed",
)


def valid_step(**overrides) -> dict:
    step = {
        "check_id": "chk-001-example",
        "description": "Inspect the latest error rate",
        "tool": "query_metrics",
        "expected_outcome": "Error rate is elevated",
        "execution_class": READ_ONLY,
        "target_environment": "production",
        "mutates_state": False,
        "automated_execution_allowed": True,
    }
    step.update(overrides)
    return step


def case_with_steps(case_id: str, *steps) -> dict:
    return {"case_id": case_id, "required_checks": list(steps)}


def test_every_fixture_step_declares_all_policy_fields(corpus):
    for case in corpus:
        for step in case["required_checks"]:
            for field in REQUIRED_STEP_FIELDS:
                assert field in step, f"{case['case_id']}: {step['check_id']} missing {field}"


def test_every_fixture_step_uses_a_known_execution_class(corpus):
    for case in corpus:
        for step in case["required_checks"]:
            assert step["execution_class"] in EXECUTION_CLASSES


def test_no_fixture_step_mutates_production_automatically(corpus):
    for case in corpus:
        for step in case["required_checks"]:
            assert not (step["mutates_state"] and step["automated_execution_allowed"]), (
                f"{case['case_id']}: {step['check_id']} mutates state automatically"
            )
            assert not (
                step["automated_execution_allowed"]
                and step["mutates_state"]
                and step["target_environment"] == "production"
            )


def test_mutating_tools_are_never_classified_read_only(corpus):
    for case in corpus:
        for step in case["required_checks"]:
            if is_mutating_tool(step["tool"]):
                assert step["execution_class"] != READ_ONLY, (
                    f"{case['case_id']}: {step['check_id']} ({step['tool']}) is read_only"
                )


def test_staging_experiments_target_non_production(corpus):
    for case in corpus:
        for step in case["required_checks"]:
            if step["execution_class"] == STAGING_EXPERIMENT:
                assert step["target_environment"] in NON_PRODUCTION_ENVIRONMENTS


def test_known_mutating_tool_names_are_recognised():
    for tool in ("toggle_feature_flag", "execute_db_command", "cache_warmup", "restart_service"):
        assert is_mutating_tool(tool)
    for tool in ("query_metrics", "get_trace", "query_database", "get_commit", "query_logs"):
        assert not is_mutating_tool(tool)


def test_mutating_tool_marked_read_only_is_rejected():
    errors = check_execution_policy([
        case_with_steps("INC-900", valid_step(tool="toggle_feature_flag"))
    ])
    assert errors and "classified read_only" in errors[0]


def test_mutating_step_allowing_automation_is_rejected():
    step = valid_step(
        execution_class=HUMAN_APPROVAL_REQUIRED,
        mutates_state=True,
        automated_execution_allowed=True,
    )
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("must not allow automated execution" in error for error in errors)


def test_automated_production_mutation_is_rejected_even_without_a_class():
    step = valid_step(
        execution_class=HUMAN_APPROVAL_REQUIRED,
        target_environment="production",
        mutates_state=True,
        automated_execution_allowed=True,
    )
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert errors


def test_experiment_targeting_production_is_rejected():
    step = valid_step(
        execution_class=STAGING_EXPERIMENT,
        target_environment="production",
        mutates_state=True,
        automated_execution_allowed=False,
    )
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("must target staging or sandbox" in error for error in errors)


def test_missing_execution_class_is_rejected():
    step = valid_step()
    del step["execution_class"]
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("missing or unknown execution_class" in error for error in errors)


def test_read_only_step_that_mutates_is_rejected():
    errors = check_execution_policy([case_with_steps("INC-900", valid_step(mutates_state=True))])
    assert any("read_only step must declare mutates_state=false" in e for e in errors)


def test_human_approval_step_that_is_automated_is_rejected():
    step = valid_step(
        execution_class=HUMAN_APPROVAL_REQUIRED,
        mutates_state=True,
        automated_execution_allowed=True,
    )
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("automated_execution_allowed=false" in e for e in errors)


def test_error_messages_identify_the_case_and_step():
    step = valid_step(execution_class="YOLO")
    errors = check_execution_policy([case_with_steps("INC-901", step)])
    assert "INC-901" in errors[0] and "chk-001-example" in errors[0]


def test_committed_corpus_passes_the_policy_check(corpus):
    assert check_execution_policy(corpus) == []


@pytest.mark.parametrize("field", REQUIRED_STEP_FIELDS)
def test_schema_requires_every_policy_field(incident_schema, corpus, field):
    validator = build_validator(incident_schema)
    case = deepcopy(corpus[0])
    del case["required_checks"][0][field]
    errors = [str(error.message) for error in validator.iter_errors(case)]
    assert any(field in error for error in errors)


def test_schema_rejects_read_only_step_that_mutates(incident_schema, corpus):
    validator = build_validator(incident_schema)
    case = deepcopy(corpus[0])
    case["required_checks"][0]["mutates_state"] = True
    assert list(validator.iter_errors(case))


def test_schema_rejects_automated_mutating_step(incident_schema, corpus):
    validator = build_validator(incident_schema)
    case = deepcopy(corpus[0])
    case["required_checks"][0].update(
        execution_class=HUMAN_APPROVAL_REQUIRED,
        mutates_state=True,
        automated_execution_allowed=True,
    )
    assert list(validator.iter_errors(case))


def test_schema_rejects_experiment_targeting_production(incident_schema, corpus):
    validator = build_validator(incident_schema)
    case = deepcopy(corpus[0])
    case["required_checks"][0].update(
        execution_class=STAGING_EXPERIMENT,
        target_environment="production",
        mutates_state=True,
        automated_execution_allowed=False,
    )
    assert list(validator.iter_errors(case))
