"""Execution-class policy for benchmark verification steps.

Benchmark fixtures list the verification steps a thorough investigation is
expected to take. Several of those steps *mutate* the system under
investigation — toggling a feature flag, cancelling a migration, warming a
cache. Modelling a mutating step as an ordinary read-only tool call would let a
future tool registry execute it autonomously against production, which
contradicts ADR-0004 (Read-Only Investigation & Isolated Remediation).

Every ``required_checks[]`` entry must therefore declare all four of:

* ``execution_class`` — ``read_only`` | ``staging_experiment`` |
  ``human_approval_required``
* ``target_environment`` — ``production`` | ``staging`` | ``sandbox`` |
  ``not_applicable``
* ``mutates_state`` — does performing the step change system state?
* ``automated_execution_allowed`` — may an autonomous agent run it un-gated?

Classification of a tool is a **positive registry**, not a name heuristic:
:data:`TOOL_REGISTRY` names every tool the benchmark knows about and its side
effect class. An unregistered tool name fails closed — it is reported and is
never implicitly treated as read-only. The prefix/exact-name patterns in
:data:`MUTATING_TOOL_PREFIXES` and :data:`MUTATING_TOOL_NAMES` are retained
only as defence in depth, to catch a *mis-registered* tool (a name that looks
mutating but is registered read-only).

**This is a fixture/metadata validator, not a runtime security control.** It
checks what the benchmark *claims* about a tool. A future agent must still
enforce capability permissions at the tool-execution boundary; nothing here
grants, denies or executes anything.
"""

from enum import StrEnum

from nexus_benchmarks.errors import MalformedCaseError

READ_ONLY = "read_only"
STAGING_EXPERIMENT = "staging_experiment"
HUMAN_APPROVAL_REQUIRED = "human_approval_required"

EXECUTION_CLASSES: frozenset[str] = frozenset({
    READ_ONLY,
    STAGING_EXPERIMENT,
    HUMAN_APPROVAL_REQUIRED,
})

PRODUCTION = "production"
NON_PRODUCTION_ENVIRONMENTS: frozenset[str] = frozenset({"staging", "sandbox"})
TARGET_ENVIRONMENTS: frozenset[str] = NON_PRODUCTION_ENVIRONMENTS | {PRODUCTION, "not_applicable"}


class ToolSideEffect(StrEnum):
    """Whether performing a tool call changes the state of the target system."""

    READ_ONLY = "read_only"
    MUTATING = "mutating"


#: Every verification tool the benchmark currently knows about, with its
#: side-effect class. A tool that is not listed here is not recognised: it is
#: reported as unregistered and may not be classified ``read_only``.
TOOL_REGISTRY: dict[str, ToolSideEffect] = {
    # --- Read-only observation tools -------------------------------------
    "get_api_schema": ToolSideEffect.READ_ONLY,
    "get_commit": ToolSideEffect.READ_ONLY,
    "get_config": ToolSideEffect.READ_ONLY,
    "get_config_audit": ToolSideEffect.READ_ONLY,
    "get_contract_test": ToolSideEffect.READ_ONLY,
    "get_dependency_status": ToolSideEffect.READ_ONLY,
    "get_deployment": ToolSideEffect.READ_ONLY,
    "get_process_info": ToolSideEffect.READ_ONLY,
    "get_thread_dump": ToolSideEffect.READ_ONLY,
    "get_trace": ToolSideEffect.READ_ONLY,
    "inspect_kafka_message": ToolSideEffect.READ_ONLY,
    "inspect_queue": ToolSideEffect.READ_ONLY,
    "network_diagnostic": ToolSideEffect.READ_ONLY,
    "query_database": ToolSideEffect.READ_ONLY,
    "query_deployments": ToolSideEffect.READ_ONLY,
    "query_logs": ToolSideEffect.READ_ONLY,
    "query_metrics": ToolSideEffect.READ_ONLY,
    "query_traces": ToolSideEffect.READ_ONLY,
    # --- Tools that change system state ----------------------------------
    "cache_warmup": ToolSideEffect.MUTATING,
    "execute_db_command": ToolSideEffect.MUTATING,
    "toggle_feature_flag": ToolSideEffect.MUTATING,
}

MUTATING_TOOL_PREFIXES: tuple[str, ...] = (
    "apply_",
    "cancel_",
    "delete_",
    "disable_",
    "enable_",
    "execute_",
    "kill_",
    "promote_",
    "purge_",
    "restart_",
    "rollback_",
    "run_",
    "scale_",
    "set_",
    "terminate_",
    "toggle_",
    "update_",
    "write_",
)

MUTATING_TOOL_NAMES: frozenset[str] = frozenset({"cache_warmup", "flip_switch", "shell_exec"})


def classify_tool(tool: str) -> ToolSideEffect | None:
    """Side-effect class of ``tool``, or ``None`` if it is not registered."""
    return TOOL_REGISTRY.get(tool)


def registered_tools(side_effect: ToolSideEffect | None = None) -> frozenset[str]:
    """Names of registered tools, optionally filtered by side-effect class."""
    return frozenset(
        name
        for name, effect in TOOL_REGISTRY.items()
        if side_effect is None or effect == side_effect
    )


def is_mutating_tool(tool: str) -> bool:
    """Whether the tool *name* implies a state change (defence in depth only)."""
    return tool in MUTATING_TOOL_NAMES or tool.startswith(MUTATING_TOOL_PREFIXES)


def check_execution_policy(cases: list[object]) -> list[str]:
    """Return policy violations for every verification step in ``cases``."""
    errors: list[str] = []
    for case in cases:
        errors.extend(check_case_execution_policy(case))
    return errors


def check_case_execution_policy(case: object) -> list[str]:
    """Return policy violations for the verification steps of one case."""
    if not isinstance(case, dict):
        return [MalformedCaseError.case_not_an_object(case).message]

    case_id = str(case.get("case_id", "<unknown case>"))
    steps = case.get("required_checks", [])
    if not isinstance(steps, list):
        return [
            MalformedCaseError.wrong_type(case_id, "required_checks", "an array", steps).message
        ]

    errors: list[str] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(
                MalformedCaseError.wrong_type(
                    case_id, f"required_checks[{index}]", "an object", step
                ).message
            )
            continue
        errors.extend(_check_step(case_id, index, step))
    return errors


def _check_step(case_id: str, index: int, step: dict) -> list[str]:
    tool = step.get("tool")
    where = f"{case_id}: required_checks[{index}] ({step.get('check_id', '?')})"

    execution_class = step.get("execution_class")
    environment = step.get("target_environment")
    mutates_state = step.get("mutates_state")
    automated = step.get("automated_execution_allowed")

    errors: list[str] = []
    if not isinstance(tool, str) or not tool:
        errors.append(f"{where}: tool must be a non-empty string")
        return errors
    if not isinstance(execution_class, str) or execution_class not in EXECUTION_CLASSES:
        return [f"{where}: missing or unknown execution_class {execution_class!r}"]

    registered = classify_tool(tool)
    if registered is None:
        errors.append(
            f"{where}: tool {tool!r} is not registered in TOOL_REGISTRY — register its "
            "side-effect class explicitly; unregistered tools must not default to read_only"
        )
    elif registered is ToolSideEffect.MUTATING and execution_class == READ_ONLY:
        errors.append(f"{where}: tool {tool!r} is registered as mutating but the step is read_only")
    elif registered is ToolSideEffect.READ_ONLY and mutates_state is True:
        errors.append(
            f"{where}: tool {tool!r} is registered read-only but the step declares "
            "mutates_state=true"
        )
    elif registered is ToolSideEffect.READ_ONLY and is_mutating_tool(tool):
        # Defence in depth: the name and the registry disagree.
        errors.append(
            f"{where}: tool {tool!r} is registered read-only but its name implies mutation — "
            "the registry entry is wrong"
        )

    if not isinstance(environment, str) or environment not in TARGET_ENVIRONMENTS:
        errors.append(f"{where}: missing or unknown target_environment {environment!r}")

    if mutates_state and automated:
        errors.append(f"{where}: mutating step must not allow automated execution")

    if execution_class == READ_ONLY:
        errors.extend(_check_read_only(where, mutates_state, automated))
    elif execution_class == STAGING_EXPERIMENT:
        errors.extend(_check_staging_experiment(where, environment, mutates_state, automated))
    else:
        errors.extend(_check_human_approval(where, mutates_state, automated))
    return errors


def _check_read_only(where: str, mutates_state: object, automated: object) -> list[str]:
    errors = []
    if mutates_state is not False:
        errors.append(f"{where}: read_only step must declare mutates_state=false")
    if automated is not True:
        errors.append(f"{where}: read_only step must declare automated_execution_allowed=true")
    return errors


def _check_staging_experiment(
    where: str, environment: object, mutates_state: object, automated: object
) -> list[str]:
    errors = []
    if not isinstance(environment, str) or environment not in NON_PRODUCTION_ENVIRONMENTS:
        errors.append(
            f"{where}: staging_experiment must target staging or sandbox, not {environment!r}"
        )
    if mutates_state is not True:
        errors.append(f"{where}: staging_experiment must declare mutates_state=true")
    if automated is not False:
        errors.append(f"{where}: staging_experiment must declare automated_execution_allowed=false")
    return errors


def _check_human_approval(where: str, mutates_state: object, automated: object) -> list[str]:
    errors = []
    if mutates_state is not True:
        errors.append(f"{where}: human_approval_required step must declare mutates_state=true")
    if automated is not False:
        errors.append(
            f"{where}: human_approval_required step must declare automated_execution_allowed=false"
        )
    return errors
