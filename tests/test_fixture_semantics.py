"""Pin the observed-incident target, especially INC-013 versus genuine ambiguity.

These are fixture-consistency assertions, not model evaluation. General prose
reasoning and realism (e.g. database lock modes) still require author review.
"""


def _case(corpus, case_id):
    return next(case for case in corpus if case["case_id"] == case_id)


def test_inc_013_scores_the_observed_dependency_failure(corpus):
    case = _case(corpus, "INC-013")
    assert case["scenario_type"] == "single_cause"
    assert case["category"] == "dependency_regression"
    assert case["ground_truth"]["root_cause_type"] == "dependency_failure"
    assert not case["ground_truth"]["ambiguity_note"]
    assert not case["ground_truth"]["insufficient_evidence_note"]
    assert not case["ground_truth"]["trigger_change_id"]
    assert case["expected_diagnosis"]["root_cause_type_match"] is True
    assert case["expected_diagnosis"]["change_attribution_match"] is False
    assert case["acceptable_alternatives"] == [], (
        "a latent defect is not an observed-incident answer"
    )


def test_inc_013_requires_both_paths_and_dependency_evidence(corpus):
    case = _case(corpus, "INC-013")
    required = set(case["expected_diagnosis"]["must_include_evidence_ids"])
    discriminating = {"ev-003-dependency-outage", "ev-004-trace-flag-path", "ev-005-trace-old-path"}
    assert discriminating <= required
    referenced = {
        evidence_id
        for link in case["ground_truth"]["causal_chain"]
        for evidence_id in link["evidence_ids"]
    }
    assert discriminating <= referenced
    assert "recommendation-engine failures" in next(
        item["summary"]
        for item in case["evidence_catalog"]
        if item["evidence_id"] == "ev-005-trace-old-path"
    )


def test_inc_013_does_not_score_latent_defects_or_future_experiment_results(corpus):
    case = _case(corpus, "INC-013")
    experiment = next(
        step for step in case["required_checks"] if step["tool"] == "toggle_feature_flag"
    )
    assert experiment["critical"] is False, "the observed cause does not depend on a future toggle"
    assert experiment["execution_class"] == "staging_experiment"
    assert experiment["automated_execution_allowed"] is False
    assert "No experiment result is assumed" in experiment["expected_outcome"]
    assert (
        "The new code is proven defect-free against a healthy dependency"
        in case["expected_diagnosis"]["must_not_claim"]
    )


def test_inc_022_retains_genuine_observed_error_ambiguity(corpus):
    case = _case(corpus, "INC-022")
    assert case["scenario_type"] == case["ground_truth"]["root_cause_type"] == "ambiguous"
    assert not case["ground_truth"]["trigger_change_id"]
    assert case["expected_diagnosis"]["root_cause_type_match"] is False
    ids = {item["evidence_id"] for item in case["evidence_catalog"]}
    assert "ev-005-no-comparison-cohort" in ids
    assert "ev-005-trace-old-path" not in ids
    trace = next(item for item in case["evidence_catalog"] if item["evidence_type"] == "trace")
    assert trace["integrity_status"] == trace["availability_status"] == "partial"
    assert {"ev-004-partial-root-trace", "ev-005-no-comparison-cohort"} <= set(
        case["expected_diagnosis"]["must_include_evidence_ids"]
    )
    for step in case["required_checks"]:
        if step["mutates_state"]:
            assert step["automated_execution_allowed"] is False
            assert "No result is assumed" in step["expected_outcome"]
