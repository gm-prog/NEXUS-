"""Verification-step execution policy (audit §3).

Classification is a **positive registry**, not a name heuristic: a tool that is
not registered fails closed instead of defaulting to read-only. Mutating steps
must be labelled as staging experiments or human-gated, and may never be
executable automatically.
"""

from copy import deepcopy

import pytest

from nexus_benchmarks.cli import build_validator
from nexus_benchmarks.errors import MalformedCaseError
from nexus_benchmarks.execution_policy import (
    EXECUTION_CLASSES,
    HUMAN_APPROVAL_REQUIRED,
    NON_PRODUCTION_ENVIRONMENTS,
    READ_ONLY,
    STAGING_EXPERIMENT,
    TOOL_REGISTRY,
    ToolSideEffect,
    check_case_execution_policy,
    check_execution_policy,
    classify_tool,
    is_mutating_tool,
    registered_tools,
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


def mutating_step(**overrides) -> dict:
    step = valid_step(
        tool="toggle_feature_flag",
        execution_class=STAGING_EXPERIMENT,
        target_environment="staging",
        mutates_state=True,
        automated_execution_allowed=False,
    )
    step.update(overrides)
    return step


# --- Corpus invariants ---------------------------------------------------


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


def test_mutating_tools_are_never_classified_read_only(corpus):
    """Retain the corpus-level name defence as well as registry assertions."""
    for case in corpus:
        for step in case["required_checks"]:
            if is_mutating_tool(step["tool"]):
                assert step["execution_class"] != READ_ONLY, (
                    f"{case['case_id']}: {step['tool']} must not be read_only"
                )


def test_staging_experiments_target_non_production(corpus):
    for case in corpus:
        for step in case["required_checks"]:
            if step["execution_class"] == STAGING_EXPERIMENT:
                assert step["target_environment"] in NON_PRODUCTION_ENVIRONMENTS


def test_committed_corpus_passes_the_policy_check(corpus):
    assert check_execution_policy(corpus) == []


# --- Positive registry ---------------------------------------------------


def test_every_tool_used_by_the_corpus_is_registered(corpus):
    """Fail-closed requirement: no fixture may rely on an unregistered tool."""
    unregistered = sorted({
        step["tool"]
        for case in corpus
        for step in case["required_checks"]
        if step["tool"] not in TOOL_REGISTRY
    })
    assert unregistered == []


def test_registry_and_fixtures_cover_the_same_tool_set(corpus):
    seen = {step["tool"] for case in corpus for step in case["required_checks"]}
    assert seen == set(TOOL_REGISTRY), "registry and fixtures must cover the same tool set"


@pytest.mark.parametrize("tool", sorted(registered_tools(ToolSideEffect.READ_ONLY)))
def test_every_registered_read_only_tool_is_accepted_as_read_only(tool):
    """Each of the 18 observation tools gets an independently reported positive test."""
    errors = check_execution_policy([case_with_steps("INC-900", valid_step(tool=tool))])
    assert errors == [], f"{tool}: {errors}"


def test_every_registered_mutating_tool_is_rejected_as_read_only():
    for tool in sorted(registered_tools(ToolSideEffect.MUTATING)):
        errors = check_execution_policy([case_with_steps("INC-900", valid_step(tool=tool))])
        assert errors and "registered as mutating" in errors[0], f"{tool}: {errors}"


def test_every_registered_mutating_tool_passes_as_a_staging_experiment():
    for tool in sorted(registered_tools(ToolSideEffect.MUTATING)):
        step = mutating_step(tool=tool)
        assert check_execution_policy([case_with_steps("INC-900", step)]) == [], f"{tool}"


def test_registered_read_only_tool_declaring_mutation_is_rejected():
    errors = check_execution_policy([case_with_steps("INC-900", valid_step(mutates_state=True))])
    assert any("registered read-only" in error for error in errors)


def test_registered_mutating_tool_marked_read_only_is_rejected():
    errors = check_execution_policy([
        case_with_steps("INC-900", valid_step(tool="toggle_feature_flag"))
    ])
    assert errors and "registered as mutating" in errors[0]


@pytest.mark.parametrize("tool", ["set_feature_flag", "promote_deployment", "run_migration"])
def test_novel_mutating_name_is_not_implicitly_read_only(tool):
    """Audit §3.5: a new mutating name must fail closed, not default to read-only."""
    errors = check_execution_policy([case_with_steps("INC-900", valid_step(tool=tool))])
    assert errors
    assert any("not registered in TOOL_REGISTRY" in error for error in errors)


@pytest.mark.parametrize("tool", ["set_feature_flag", "promote_deployment", "run_migration"])
def test_novel_mutating_name_is_rejected_once_registered_as_mutating(tool, monkeypatch):
    """Registering the tool explicitly converts silence into a precise error."""
    assert classify_tool(tool) is None
    monkeypatch.setitem(TOOL_REGISTRY, tool, ToolSideEffect.MUTATING)
    assert classify_tool(tool) is ToolSideEffect.MUTATING
    errors = check_execution_policy([case_with_steps("INC-900", valid_step(tool=tool))])
    assert any("registered as mutating" in error for error in errors)


def test_unknown_tool_cannot_become_an_automatable_read_only_step():
    """An unregistered tool must not be silently treated as safe to automate."""
    step = valid_step(tool="do_something_new")
    assert step["automated_execution_allowed"] is True
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("not registered" in error for error in errors)


def test_registry_and_name_heuristic_disagreement_is_reported(monkeypatch):
    """Defence in depth: a mutating-looking name registered read-only is flagged."""
    monkeypatch.setitem(TOOL_REGISTRY, "promote_deployment", ToolSideEffect.READ_ONLY)
    errors = check_execution_policy([
        case_with_steps("INC-900", valid_step(tool="promote_deployment"))
    ])
    assert any("registry entry is wrong" in error for error in errors)


def test_unregistered_tool_name_is_caught_by_the_registry_not_the_heuristic():
    """The heuristic is defence in depth; the registry is the boundary."""
    assert is_mutating_tool("frobnicate_widget") is False
    assert classify_tool("frobnicate_widget") is None
    errors = check_execution_policy([
        case_with_steps("INC-900", valid_step(tool="frobnicate_widget"))
    ])
    assert any("not registered in TOOL_REGISTRY" in error for error in errors)


def test_known_mutating_tool_names_are_recognised():
    for tool in ("toggle_feature_flag", "execute_db_command", "cache_warmup", "restart_service"):
        assert is_mutating_tool(tool)
    for tool in ("query_metrics", "get_trace", "query_database", "get_commit", "query_logs"):
        assert not is_mutating_tool(tool)


# --- Cross-field invariants ----------------------------------------------


def test_mutating_step_allowing_automation_is_rejected():
    step = mutating_step(execution_class=HUMAN_APPROVAL_REQUIRED, automated_execution_allowed=True)
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("must not allow automated execution" in error for error in errors)


def test_automated_production_mutation_is_rejected():
    step = mutating_step(
        execution_class=HUMAN_APPROVAL_REQUIRED,
        target_environment="production",
        automated_execution_allowed=True,
    )
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert errors


def test_experiment_targeting_production_is_rejected():
    step = mutating_step(target_environment="production")
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("must target staging or sandbox" in error for error in errors)


def test_missing_execution_class_is_rejected():
    step = valid_step()
    del step["execution_class"]
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("missing or unknown execution_class" in error for error in errors)


def test_read_only_step_that_mutates_is_rejected():
    errors = check_execution_policy([case_with_steps("INC-900", valid_step(mutates_state=True))])
    assert any("read_only step must declare mutates_state=false" in error for error in errors)


def test_human_approval_step_that_is_automated_is_rejected():
    step = mutating_step(execution_class=HUMAN_APPROVAL_REQUIRED, automated_execution_allowed=True)
    errors = check_execution_policy([case_with_steps("INC-900", step)])
    assert any("automated_execution_allowed=false" in error for error in errors)


def test_error_messages_identify_the_case_and_step():
    errors = check_execution_policy([
        case_with_steps("INC-901", valid_step(execution_class="YOLO"))
    ])
    assert "INC-901" in errors[0] and "chk-001-example" in errors[0]


# --- Structural robustness -----------------------------------------------


@pytest.mark.parametrize("steps", ["nope", None, {"a": 1}, [None], ["nope"]])
def test_malformed_required_checks_are_controlled(steps):
    errors = check_case_execution_policy({"case_id": "INC-900", "required_checks": steps})
    assert errors
    assert all(isinstance(error, str) for error in errors)
    assert not any("Traceback" in error for error in errors)


def test_missing_tool_field_is_reported():
    step = valid_step()
    del step["tool"]
    errors = check_case_execution_policy({"case_id": "INC-900", "required_checks": [step]})
    assert any("tool must be a non-empty string" in error for error in errors)


def test_malformed_root_reports_the_expected_message():
    assert check_case_execution_policy(None) == [
        MalformedCaseError.case_not_an_object(None).message
    ]


# --- Schema-level enforcement --------------------------------------------


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


@pytest.mark.parametrize(
    "execution_class", [READ_ONLY, STAGING_EXPERIMENT, HUMAN_APPROVAL_REQUIRED]
)
def test_unknown_tools_fail_closed_in_every_class(execution_class):
    step = (
        valid_step(tool="unknown_observation")
        if execution_class == READ_ONLY
        else mutating_step(tool="unknown_mutation", execution_class=execution_class)
    )
    errors = check_case_execution_policy(case_with_steps("INC-900", step))
    assert any("not registered in TOOL_REGISTRY" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_class", []),
        ("execution_class", {}),
        ("target_environment", []),
        ("target_environment", {}),
    ],
)
def test_malformed_policy_enum_shapes_are_controlled(field, value):
    step = mutating_step(**{field: value})
    errors = check_case_execution_policy(case_with_steps("INC-900", step))
    assert errors and all(isinstance(error, str) for error in errors)


@pytest.mark.parametrize(
    "tool", ["set_feature_flag", "promote_deployment", "run_migration", "flip_switch"]
)
def test_installed_cli_rejects_a_new_tool_falsely_declared_read_only(run_cli, sample_case, tool):
    sample_case["case_id"] = "INC-900"
    sample_case["required_checks"][0]["tool"] = tool
    result = run_cli({"INC-900-unsafe-tool.json": sample_case}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert tool in output and "not registered in TOOL_REGISTRY" in output
    assert "Traceback" not in output
