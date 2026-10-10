"""Benchmark answer-leakage boundary (finding 4).

The benchmark files colocate agent-visible evidence with the evaluator-only
answer key. These tests pin down the allowlisted projection that separates
them, and prove the projection is non-vacuous by injecting leaks.
"""

import re
from copy import deepcopy

import pytest

from nexus_benchmarks.agent_view import (
    AGENT_VISIBLE_NESTED_KEYS,
    AGENT_VISIBLE_ROOT_KEYS,
    EVALUATOR_ONLY_NESTED_KEYS,
    EVALUATOR_ONLY_ROOT_KEYS,
    REVIEWED_OBSERVATION_OVERLAPS,
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


@pytest.mark.parametrize("description_key", ["from_description", "to_description"])
@pytest.mark.parametrize(
    "visible_path",
    [
        "initial_symptoms[0]",
        "evidence_catalog[0].summary",
        "environment.cluster",
        "changes[0].summary",
    ],
)
def test_causal_description_copy_is_detected(corpus, description_key, visible_path):
    case = deepcopy(corpus[0])
    hidden_path = f"ground_truth.causal_chain[0].{description_key}"
    hidden = case["ground_truth"]["causal_chain"][0][description_key]
    _set_at_path(case, visible_path, hidden)
    assert any(hidden_path in finding and visible_path in finding for finding in find_leaks(case))


@pytest.mark.parametrize("description_key", ["from_description", "to_description"])
def test_causal_copy_with_quotes_and_newlines_is_detected(corpus, description_key):
    case = deepcopy(corpus[0])
    hidden = 'Evaluator-only conclusion: "the counter is the sole cause"\nwithout proof'
    case["ground_truth"]["causal_chain"][0][description_key] = hidden
    case["evidence_catalog"][0]["summary"] = hidden
    assert any(description_key in finding for finding in find_leaks(case))


def test_copy_into_free_form_object_key_is_detected(corpus):
    case = deepcopy(corpus[0])
    hidden = case["ground_truth"]["causal_chain"][0]["to_description"]
    case["changes"][0]["details"] = {hidden: True}
    assert any("to_description" in finding and ".<key>" in finding for finding in find_leaks(case))


def test_check_outcome_copy_is_detected(corpus):
    case = deepcopy(corpus[0])
    case["environment"]["cluster"] = case["required_checks"][0]["expected_outcome"]
    assert any("required_checks[0].expected_outcome" in finding for finding in find_leaks(case))


def test_causal_descriptions_and_check_outcomes_are_all_scanned(corpus):
    for case in corpus:
        values = dict(evaluator_only_values(case))
        for index, link in enumerate(case["ground_truth"]["causal_chain"]):
            for key in ("from_description", "to_description"):
                assert values[f"ground_truth.causal_chain[{index}].{key}"] == link[key]
        for index, step in enumerate(case["required_checks"]):
            assert values[f"required_checks[{index}].expected_outcome"] == step["expected_outcome"]


@pytest.mark.parametrize("overlap", sorted(REVIEWED_OBSERVATION_OVERLAPS))
def test_reviewed_observation_overlap_is_exact_and_still_scanned_elsewhere(corpus, overlap):
    case_id, hidden_path, visible_path, hidden_value, visible_value = overlap
    case = deepcopy(next(case for case in corpus if case["case_id"] == case_id))
    assert (hidden_path, hidden_value) in evaluator_only_values(case)
    assert _get_at_path(build_agent_view(case), visible_path) == visible_value
    assert find_leaks(case) == []
    case["environment"]["cluster"] = hidden_value
    assert any(
        hidden_path in finding and "environment.cluster" in finding for finding in find_leaks(case)
    )


@pytest.mark.parametrize("overlap", sorted(REVIEWED_OBSERVATION_OVERLAPS))
def test_reviewed_paths_do_not_exempt_changed_answer_text(corpus, overlap):
    case_id, hidden_path, visible_path, _, _ = overlap
    case = deepcopy(next(case for case in corpus if case["case_id"] == case_id))
    novel = "Novel evaluator-only causal conclusion not established by the observations"
    _set_at_path(case, hidden_path, novel)
    _set_at_path(case, visible_path, novel)
    assert any(hidden_path in finding and visible_path in finding for finding in find_leaks(case))


@pytest.mark.parametrize("overlap", sorted(REVIEWED_OBSERVATION_OVERLAPS))
def test_reviewed_paths_do_not_exempt_added_copies(corpus, overlap):
    case_id, hidden_path, visible_path, hidden_value, visible_value = overlap
    case = deepcopy(next(case for case in corpus if case["case_id"] == case_id))
    _set_at_path(case, visible_path, visible_value + " Evaluator says: " + hidden_value)
    assert any(hidden_path in finding and visible_path in finding for finding in find_leaks(case))


def test_legitimate_evidence_paraphrase_is_not_a_verbatim_leak(corpus):
    case = deepcopy(next(case for case in corpus if case["case_id"] == "INC-019"))
    case["ground_truth"]["causal_chain"][0]["to_description"] = (
        "The explicit table lock blocks INSERT and UPDATE until the owning transaction ends"
    )
    observation = "INSERT and UPDATE wait on the analytics transaction's SHARE table lock"
    case["initial_symptoms"].append(observation)
    assert observation in build_agent_view(case)["initial_symptoms"]
    assert find_leaks(case) == []


@pytest.mark.parametrize("description_key", ["from_description", "to_description"])
def test_installed_cli_rejects_causal_description_copy(corpus, run_cli, description_key):
    case = deepcopy(corpus[0])
    case["evidence_catalog"][0]["summary"] = case["ground_truth"]["causal_chain"][0][
        description_key
    ]
    result = run_cli({"INC-001-causal-copy.json": case}, "--case", "INC-001")
    assert result.returncode == 1
    assert f"ground_truth.causal_chain[0].{description_key}" in result.stderr
    assert "Traceback" not in result.stdout + result.stderr


def _get_at_path(case, path):
    value = case
    for part in re.findall(r"[^.\[\]]+", path):
        value = value[int(part)] if part.isdecimal() else value[part]
    return value


def _set_at_path(case, path, value):
    parts = re.findall(r"[^.\[\]]+", path)
    parent = _get_at_path(case, ".".join(parts[:-1]))
    key = int(parts[-1]) if parts[-1].isdecimal() else parts[-1]
    parent[key] = value


@pytest.mark.parametrize("description_key", ["from_description", "to_description"])
def test_every_corpus_causal_description_copy_is_detected(corpus, description_key):
    for source_case in corpus:
        for index, link in enumerate(source_case["ground_truth"]["causal_chain"]):
            case = deepcopy(source_case)
            hidden_path = f"ground_truth.causal_chain[{index}].{description_key}"
            case["evidence_catalog"][0]["summary"] = link[description_key]
            assert any(hidden_path in finding for finding in find_leaks(case)), (
                case["case_id"],
                hidden_path,
            )
