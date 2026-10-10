"""Benchmark answer-leakage boundary (finding 4).

The benchmark files colocate agent-visible evidence with the evaluator-only
answer key. These tests pin down the allowlisted projection that separates
them, and prove the projection is non-vacuous by injecting leaks.
"""

from copy import deepcopy

import pytest

from nexus_benchmarks.agent_view import (
    AGENT_VISIBLE_NESTED_KEYS,
    AGENT_VISIBLE_ROOT_KEYS,
    EVALUATOR_ONLY_NESTED_KEYS,
    EVALUATOR_ONLY_ROOT_KEYS,
    build_agent_view,
    evaluator_only_values,
    find_leaks,
)
from nexus_benchmarks.errors import AgentViewError

EVALUATOR_ONLY_KEYS = [
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
]


def test_agent_view_contains_exactly_the_allowlisted_keys(corpus):
    for case in corpus:
        view = build_agent_view(case)
        assert set(view) <= AGENT_VISIBLE_ROOT_KEYS
        assert set(view) == AGENT_VISIBLE_ROOT_KEYS & set(case)


@pytest.mark.parametrize("key", EVALUATOR_ONLY_KEYS)
def test_evaluator_only_keys_never_reach_the_agent_view(corpus, key):
    for case in corpus:
        assert key not in build_agent_view(case), f"{case['case_id']} leaked {key}"


def test_service_impact_labels_are_not_agent_visible(corpus):
    """`impact: primary` hands the agent the localisation answer."""
    for case in corpus:
        for service in build_agent_view(case)["affected_services"]:
            assert set(service) == {"service_id", "service_name"}


def test_synthetic_fixture_notes_are_not_agent_visible(corpus):
    for case in corpus:
        for evidence in build_agent_view(case)["evidence_catalog"]:
            assert "synthetic_fixture_note" not in evidence


def test_evidence_content_itself_stays_agent_visible(corpus):
    """The projection must strip metadata without stripping the evidence."""
    for case in corpus:
        view = build_agent_view(case)
        assert len(view["evidence_catalog"]) == len(case["evidence_catalog"])
        expected = keep_only_agent_visible_fields(case["evidence_catalog"][0])
        assert view["evidence_catalog"][0] == expected


def test_no_case_leaks(corpus):
    assert [leak for case in corpus for leak in find_leaks(case)] == []


def test_projection_does_not_mutate_the_source(corpus):
    case = corpus[0]
    before = deepcopy(case)
    build_agent_view(case)
    assert case == before


def test_unclassified_top_level_key_fails_closed(corpus):
    case = deepcopy(corpus[0])
    case["new_unclassified_field"] = "surprise"
    with pytest.raises(AgentViewError) as excinfo:
        build_agent_view(case)
    assert "new_unclassified_field" in str(excinfo.value)
    assert find_leaks(case)


def test_evaluator_only_key_injected_into_an_agent_visible_object_is_dropped(corpus):
    case = deepcopy(corpus[0])
    case["evidence_catalog"][0]["ground_truth"] = case["ground_truth"]
    view = build_agent_view(case)
    assert "ground_truth" not in view["evidence_catalog"][0]


def test_ground_truth_value_injected_into_evidence_is_detected(corpus):
    """Guard against a vacuous check: an injected leak must be reported."""
    case = deepcopy(corpus[0])
    case["evidence_catalog"][0]["summary"] = "secret " + case["ground_truth"]["root_cause_type"]
    assert find_leaks(case)


def test_must_not_claim_injected_into_symptoms_is_detected(corpus):
    case = deepcopy(corpus[0])
    case["initial_symptoms"].append(case["expected_diagnosis"]["must_not_claim"][0])
    assert find_leaks(case)


def test_remediation_guidance_injected_into_environment_is_detected(corpus):
    case = deepcopy(corpus[0])
    case["environment"]["cluster"] = case["remediation_guidance"]["suggestion"]
    assert find_leaks(case)


def test_acceptable_alternative_injected_into_a_change_summary_is_detected(corpus):
    # INC-013 no longer has hypothetical alternatives; choose a case with an
    # actual change to inject into, without weakening the leakage assertion.
    case = next(c for c in corpus if c["acceptable_alternatives"] and c["changes"])
    case = deepcopy(case)
    case["changes"][0]["summary"] = case["acceptable_alternatives"][0]["description"]
    assert find_leaks(case)


def test_evaluator_only_values_covers_the_answer_key(corpus):
    for case in corpus:
        paths = {path for path, _ in evaluator_only_values(case)}
        assert "ground_truth.root_cause_type" in paths
        assert "expected_diagnosis.must_not_claim[0]" in paths
        assert "remediation_guidance.suggestion" in paths


def keep_only_agent_visible_fields(evidence: dict) -> dict:
    """Evidence item reduced to the fields the agent view is allowed to keep."""
    allowed = AGENT_VISIBLE_NESTED_KEYS["evidence_catalog"]
    return {key: value for key, value in evidence.items() if key in allowed}


def test_allowlists_match_the_schema(incident_schema):
    """Drift guard: a new schema property must be classified one way or the other."""
    declared_root_keys = set(incident_schema["properties"])
    assert declared_root_keys == AGENT_VISIBLE_ROOT_KEYS | EVALUATOR_ONLY_ROOT_KEYS
    assert not AGENT_VISIBLE_ROOT_KEYS & EVALUATOR_ONLY_ROOT_KEYS

    for name, allowed in AGENT_VISIBLE_NESTED_KEYS.items():
        spec = incident_schema["properties"][name]
        declared = set((spec.get("items") or spec)["properties"])
        assert allowed <= declared, f"{name}: allowlist cites unknown properties"
        excluded = EVALUATOR_ONLY_NESTED_KEYS.get(name, frozenset())
        assert not allowed & excluded, f"{name}: a property cannot be both visible and excluded"
        assert declared == allowed | excluded, f"{name}: unclassified nested properties"


def test_resolution_time_is_intentionally_excluded_from_schema_projection():
    """Explicitly classify end; do not loosen the drift guard for all nested fields."""
    assert EVALUATOR_ONLY_NESTED_KEYS["incident_window"] == {"end"}
    assert AGENT_VISIBLE_NESTED_KEYS["incident_window"] == {"start", "investigation_cutoff"}
