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

Invariants enforced here:

1. ``automated_execution_allowed`` is true **only** for non-mutating steps.
2. ``read_only`` steps never mutate state and are always automatable.
3. ``staging_experiment`` steps mutate state, target staging/sandbox only, and
   are never automatable.
4. ``human_approval_required`` steps mutate state and are never automatable.
5. A tool whose name implies mutation (see :data:`MUTATING_TOOL_PREFIXES` and
   :data:`MUTATING_TOOL_NAMES`) may never be classified ``read_only``.

The single source of truth for the tool-name classification is this module; the
JSON Schema carries the field-level ``allOf`` constraints only.
"""

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
TARGET_ENVIRONMENTS: frozenset[str] = NON_PRODUCTION_ENVIRONMENTS | {
    PRODUCTION,
    "not_applicable",
}

MUTATING_TOOL_PREFIXES: tuple[str, ...] = (
    "apply_",
    "cancel_",
    "delete_",
    "disable_",
    "enable_",
    "execute_",
    "kill_",
    "purge_",
    "restart_",
    "rollback_",
    "scale_",
    "terminate_",
    "toggle_",
    "update_",
    "write_",
)

MUTATING_TOOL_NAMES: frozenset[str] = frozenset({"cache_warmup", "run_command", "shell_exec"})


def is_mutating_tool(tool: str) -> bool:
    """Whether the tool name implies a state change in the target system."""
    return tool in MUTATING_TOOL_NAMES or tool.startswith(MUTATING_TOOL_PREFIXES)


def check_execution_policy(cases: list[dict]) -> list[str]:
    """Return policy violations for every verification step in ``cases``."""
    errors: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id", "<unknown case>"))
        for index, step in enumerate(case.get("required_checks", [])):
            errors.extend(_check_step(case_id, index, step))
    return errors


def _check_step(case_id: str, index: int, step: dict) -> list[str]:
    tool = str(step.get("tool", ""))
    where = f"{case_id}: required_checks[{index}] ({step.get('check_id', '?')})"

    execution_class = step.get("execution_class")
    environment = step.get("target_environment")
    mutates_state = step.get("mutates_state")
    automated = step.get("automated_execution_allowed")

    if execution_class not in EXECUTION_CLASSES:
        return [f"{where}: missing or unknown execution_class {execution_class!r}"]

    errors: list[str] = []
    if is_mutating_tool(tool) and execution_class == READ_ONLY:
        errors.append(f"{where}: tool {tool!r} implies a state change but is classified read_only")
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
    if environment not in NON_PRODUCTION_ENVIRONMENTS:
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
