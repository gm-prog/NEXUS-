"""Strict allowlist projection from a benchmark case to the agent-visible view.

A benchmark case file colocalises two very different things:

* the *agent-visible* investigation inputs (symptoms, evidence, recent
  changes, the incident window), and
* the *evaluator-only* answer key (ground truth, expected diagnosis,
  acceptable alternatives, required checks, remediation guidance, misleading
  signals, benchmark labels).

Handing a whole case object to an agent leaks the answer and silently inflates
every score. This module defines the one and only projection that may be shown
to an agent. It is an **allowlist**: a key is visible because it is named here,
never because it happens to be absent from a blocklist.

The projection also fails closed. A top-level key that has not been classified
either way aborts the projection instead of being silently forwarded.
"""

import json
from copy import deepcopy

from nexus_benchmarks.errors import AgentViewError

#: Top-level keys an agent is allowed to see.
AGENT_VISIBLE_ROOT_KEYS: frozenset[str] = frozenset({
    "schema_version",
    "case_id",
    "environment",
    "incident_window",
    "initial_symptoms",
    "affected_services",
    "evidence_catalog",
    "changes",
})

#: Top-level keys that must never reach an agent.
EVALUATOR_ONLY_ROOT_KEYS: frozenset[str] = frozenset({
    "title",
    "category",
    "scenario_type",
    "difficulty",
    "description",
    "ground_truth",
    "expected_diagnosis",
    "misleading_or_confounding_signals",
    "acceptable_alternatives",
    "required_checks",
    "remediation_guidance",
    "tags",
})

#: Per-object key allowlists for nested structures.
#:
#: ``affected_services[]`` deliberately omits ``impact``: labelling a service
#: ``primary`` hands the agent the localisation answer that
#: ``expected_diagnosis.service_localization_match`` is supposed to measure.
#:
#: ``evidence_catalog[]`` omits ``synthetic_fixture_note``: it is benchmark
#: infrastructure metadata for fixture authors, not incident evidence.
AGENT_VISIBLE_NESTED_KEYS: dict[str, frozenset[str]] = {
    "environment": frozenset({"name", "region", "cluster"}),
    "incident_window": frozenset({"start", "end", "investigation_cutoff"}),
    "affected_services": frozenset({"service_id", "service_name"}),
    "changes": frozenset({
        "change_id",
        "change_type",
        "timestamp",
        "service_id",
        "summary",
        "details",
        "commit_sha",
        "deployed_by",
    }),
    "evidence_catalog": frozenset({
        "evidence_id",
        "evidence_type",
        "source",
        "source_reference",
        "event_time",
        "collection_time",
        "time_window_start",
        "time_window_end",
        "service_id",
        "environment_id",
        "summary",
        "query_reference",
        "data_provenance",
        "integrity_status",
        "availability_status",
        "raw_data_ref",
    }),
}

#: Shortest evaluator-only string worth scanning for in the agent view. The
#: current corpus stays leak-free even down to 4 characters, so 8 leaves margin
#: for new fixtures while still filtering incidental word overlap.
_MIN_LEAK_TOKEN_LENGTH = 8


def build_agent_view(case: dict) -> dict:
    """Return the agent-visible projection of ``case``.

    Raises:
        AgentViewError: if ``case`` contains an unclassified top-level key.
    """
    unknown = sorted(set(case) - AGENT_VISIBLE_ROOT_KEYS - EVALUATOR_ONLY_ROOT_KEYS)
    if unknown:
        raise AgentViewError(str(case.get("case_id", "<unknown case>")), unknown)

    view: dict = {}
    for key, value in case.items():
        if key not in AGENT_VISIBLE_ROOT_KEYS:
            continue
        view[key] = _project(value, AGENT_VISIBLE_NESTED_KEYS.get(key))
    return view


def _project(value: object, allowed: frozenset[str] | None) -> object:
    if allowed is None:
        return deepcopy(value)
    if isinstance(value, dict):
        return {key: deepcopy(item) for key, item in value.items() if key in allowed}
    return [
        {key: deepcopy(item) for key, item in entry.items() if key in allowed} for entry in value
    ]


def evaluator_only_values(case: dict) -> list[tuple[str, str]]:
    """Yield ``(path, value)`` pairs of evaluator-only free text in ``case``.

    Identifier cross-references (``primary_service_id``, ``trigger_change_id``,
    causal-chain ``evidence_ids``) are excluded: they name objects that are
    legitimately present in the agent view as well.
    """
    found: list[tuple[str, str]] = []
    for key in ("title", "description"):
        if isinstance(case.get(key), str):
            found.append((key, case[key]))
    found.extend(_ground_truth_values(case.get("ground_truth", {})))
    found.extend(_diagnosis_values(case.get("expected_diagnosis", {})))
    found.extend(_list_values("misleading_or_confounding_signals", case))
    found.extend(_alternatives_values(case))
    found.extend(_remediation_values(case.get("remediation_guidance", {})))
    found.extend(_check_values(case))
    return found


def _ground_truth_values(ground_truth: dict) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for key in ("root_cause_type", "ambiguity_note", "insufficient_evidence_note"):
        if isinstance(ground_truth.get(key), str):
            found.append((f"ground_truth.{key}", ground_truth[key]))
    found.extend(_list_values("ground_truth.contributing_factors", ground_truth))
    # causal_chain[].from_description / to_description are deliberately not
    # scanned: they paraphrase observations that are already agent-visible
    # (symptoms, evidence summaries), so matching them reports noise rather
    # than leakage. They remain covered by the key-level allowlist.
    return found


def _diagnosis_values(expected_diagnosis: dict) -> list[tuple[str, str]]:
    return [
        (f"expected_diagnosis.must_not_claim[{index}]", claim)
        for index, claim in enumerate(expected_diagnosis.get("must_not_claim", []))
    ]


def _alternatives_values(case: dict) -> list[tuple[str, str]]:
    return [
        (f"acceptable_alternatives[{index}].description", alternative["description"])
        for index, alternative in enumerate(case.get("acceptable_alternatives", []))
    ]


def _remediation_values(remediation: dict) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for key in ("suggestion", "rollback_plan"):
        if isinstance(remediation.get(key), str):
            found.append((f"remediation_guidance.{key}", remediation[key]))
    return found + _list_values("remediation_guidance.test_plan", remediation)


def _check_values(case: dict) -> list[tuple[str, str]]:
    # Only `description` is scanned. `expected_outcome` frequently quotes a log
    # line or metric that is itself agent-visible evidence, so substring
    # matching it reports noise rather than leakage. It stays covered by the
    # key-level allowlist.
    found: list[tuple[str, str]] = []
    for index, step in enumerate(case.get("required_checks", [])):
        if isinstance(step.get("description"), str):
            found.append((f"required_checks[{index}].description", step["description"]))
    return found


def _list_values(prefix: str, container: dict) -> list[tuple[str, str]]:
    key = prefix.rsplit(".", 1)[-1]
    return [(f"{prefix}[{index}]", item) for index, item in enumerate(container.get(key, []))]


def find_leaks(case: dict) -> list[str]:
    """Return the ways ``case`` leaks evaluator-only data into its agent view.

    Two independent checks:

    1. No evaluator-only *key* survives the projection.
    2. No evaluator-only *value* appears anywhere in the serialised
       projection. See :func:`evaluator_only_values` for the two categories
       (causal-chain descriptions, check expected outcomes) that are excluded
       from the value scan because they legitimately restate agent-visible
       observations.
    """
    case_id = str(case.get("case_id", "<unknown case>"))
    try:
        view = build_agent_view(case)
    except AgentViewError as error:
        return [f"{case_id}: {error.message}"]

    findings = [
        f"{case_id}: evaluator-only key {key!r} is present in the agent view"
        for key in sorted(EVALUATOR_ONLY_ROOT_KEYS & set(view))
    ]

    blob = json.dumps(view, ensure_ascii=False, sort_keys=True).lower()
    for path, value in evaluator_only_values(case):
        token = value.strip().lower()
        if len(token) >= _MIN_LEAK_TOKEN_LENGTH and token in blob:
            findings.append(
                f"{case_id}: evaluator-only value from {path} appears in the agent view"
            )
    return findings
