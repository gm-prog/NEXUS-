"""Pin the observed-incident target, especially INC-013 versus genuine ambiguity.

These are fixture-consistency assertions, not model evaluation. General prose
reasoning and realism still require author review; the focused arithmetic
and lock-snapshot checks below prevent the reviewed INC-016/019 contradictions.
No live database execution or model evaluation is performed.
"""

import re
from datetime import datetime
from decimal import Decimal

MAX_UNRESOLVED_RATE_CONFIDENCE = 0.6


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


def test_inc_016_conditional_arithmetic_does_not_call_four_percent_normal(corpus):
    case = _case(corpus, "INC-016")
    metric = _evidence(case, "ev-001-metric-5xx-spike")
    baseline, displayed = map(Decimal, re.findall(r"(\d+(?:\.\d+)?)%", metric["summary"]))
    details = case["changes"][0]["details"]
    increments = details["error_counter_increments_per_error"]
    assert (baseline, displayed, increments) == (Decimal("0.5"), Decimal("8"), 2)
    conditional_rate = displayed / increments
    assert conditional_rate == Decimal("4")
    assert conditional_rate / baseline == Decimal("8")
    assert displayed / baseline == Decimal("16")
    assert conditional_rate > baseline
    assert details["counter_validation_evidence_id"] == "ev-004-commit-instrumentation-bug"
    assert details["rate_denominator_alignment"] == "not_established"
    assert details["aligned_request_totals_available"] is False


def test_inc_016_scores_uncertainty_not_a_high_confidence_false_positive(corpus):
    case = _case(corpus, "INC-016")
    truth = case["ground_truth"]
    diagnosis = case["expected_diagnosis"]
    assert case["scenario_type"] == truth["root_cause_type"] == "insufficient_evidence"
    assert truth["insufficient_evidence_note"]
    assert not truth["trigger_change_id"]
    assert diagnosis["root_cause_type_match"] is False
    assert diagnosis["change_attribution_match"] is False
    assert diagnosis["service_localization_match"] is True
    assert diagnosis["min_confidence"] == 0.0
    assert "false-positive" not in case["tags"]
    assert all(
        max(alt["confidence_range"]) <= MAX_UNRESOLVED_RATE_CONFIDENCE
        for alt in case["acceptable_alternatives"]
    )
    prohibited = " ".join(diagnosis["must_not_claim"]).casefold()
    assert all(word in prohibited for word in ("normal", "false positive", "sole", "fleet-wide"))
    assert {
        "ev-001-metric-5xx-spike",
        "ev-002-log-actual-errors",
        "ev-004-commit-instrumentation-bug",
        "ev-005-trace-normal",
    } <= set(diagnosis["must_include_evidence_ids"])


def test_inc_016_known_prose_contradictions_do_not_return(corpus):
    case = _case(corpus, "INC-016")
    # Check specific unsupported assertions, not paragraph snapshots. Negative
    # must_not_claim examples are intentionally outside this asserted prose.
    text = " ".join([
        case["title"],
        case["description"],
        case["ground_truth"]["insufficient_evidence_note"],
        *(
            link[key]
            for link in case["ground_truth"]["causal_chain"]
            for key in ("from_description", "to_description")
        ),
        *(alt["description"] for alt in case["acceptable_alternatives"]),
        *(item["summary"] for item in case["evidence_catalog"]),
        *(step["expected_outcome"] for step in case["required_checks"]),
    ])
    unsupported = r"actual error rate (?:is|appears) normal|actual errors normal|no real incident"
    assert re.search(unsupported, text, re.IGNORECASE) is None
    assert "~100" not in text, "the metric supplies a percentage, not an error count"


def test_inc_019_has_explicit_transaction_sql_not_a_plain_select_blocker(corpus):
    case = _case(corpus, "INC-019")
    activity = _evidence(case, "ev-003-pg-stat-activity")["summary"]
    sql = r"\bBEGIN;\s*LOCK\s+TABLE\s+(?:public\.)?orders\s+IN\s+SHARE\s+MODE;\s*SELECT\b"
    assert re.search(sql, activity, re.IGNORECASE)
    assert "state=active" in activity
    assert re.search(r";\s*(?:COMMIT|ROLLBACK)\s*;", activity, re.IGNORECASE) is None
    xact_start = re.search(r"xact_start=([^\s;]+)", activity)[1]
    assert datetime.fromisoformat(xact_start) <= datetime.fromisoformat(
        case["incident_window"]["investigation_cutoff"]
    )
    blocker = int(re.search(r"pid=(\d+)", activity)[1])
    origin = _evidence(case, "ev-004-query-origin")["summary"]
    assert int(re.search(r"pid=(\d+)", origin)[1]) == blocker
    assert "analytics-tool" in origin


def test_inc_019_lock_modes_grants_and_blocking_pids_explain_both_writes(corpus):
    case = _case(corpus, "INC-019")
    activity = _evidence(case, "ev-003-pg-stat-activity")["summary"]
    blocker = re.search(r"pid=(\d+)", activity)[1]
    snapshot = _evidence(case, "ev-006-lock-wait-snapshot")
    assert snapshot["integrity_status"] == "verified"
    assert snapshot["data_provenance"] == "verification_result"
    rows = {
        (pid, mode, granted == "true")
        for pid, mode, granted in re.findall(
            r"pid=(\d+)\s+mode=(\w+)\s+granted=(true|false)", snapshot["summary"]
        )
    }
    assert (blocker, "ShareLock", True) in rows
    # SELECT also acquires a compatible read lock; its presence is not the
    # explanation for DML waits. One backend can hold multiple lock modes.
    assert (blocker, "AccessShareLock", True) in rows
    waiters = {pid for pid, mode, granted in rows if mode == "RowExclusiveLock" and not granted}
    write_kinds = ("INSERT", "UPDATE")
    assert len(waiters) >= len(write_kinds)
    for waiter in waiters:
        assert re.search(rf"pg_blocking_pids\({waiter}\)\s*=\s*\[{blocker}\]", snapshot["summary"])
    for write_kind in write_kinds:
        assert f"order-service {write_kind}" in snapshot["summary"]
    assert "wait_event_type=Lock" in snapshot["summary"]


def test_inc_019_causal_target_requires_transaction_and_lock_evidence(corpus):
    case = _case(corpus, "INC-019")
    assert case["category"] == "db_lock_contention"
    assert case["scenario_type"] == "single_cause"
    assert case["ground_truth"]["root_cause_type"] == "design_flaw"
    assert not case["ground_truth"]["trigger_change_id"]
    assert case["expected_diagnosis"]["change_attribution_match"] is False
    decisive = {"ev-003-pg-stat-activity", "ev-004-query-origin", "ev-006-lock-wait-snapshot"}
    assert decisive <= set(case["expected_diagnosis"]["must_include_evidence_ids"])
    assert decisive <= set(case["ground_truth"]["causal_chain"][0]["evidence_ids"])
    assert "ev-006-lock-wait-snapshot" in case["ground_truth"]["causal_chain"][1]["evidence_ids"]
    errors = _evidence(case, "ev-002-log-lock-timeout")["summary"]
    assert "55P03" in errors and "lock timeout" in errors
    assert "40P01" not in errors
    assert "Deadlock found when trying to get lock" not in errors
    assert "A deadlock cycle was observed" in case["expected_diagnosis"]["must_not_claim"]


def test_inc_019_remediation_ends_transaction_with_a_human_gate(corpus):
    case = _case(corpus, "INC-019")
    step = next(step for step in case["required_checks"] if step["tool"] == "execute_db_command")
    assert step["execution_class"] == "human_approval_required"
    assert step["target_environment"] == "production"
    assert step["mutates_state"] is True
    assert step["automated_execution_allowed"] is False
    assert step["critical"] is False, "diagnosis does not require executing remediation"
    assert "transaction" in step["description"]
    assert "No remediation result is assumed" in step["expected_outcome"]
    assert case["remediation_guidance"]["risk_level"] == "medium"
    assert "immediate recovery" not in case["remediation_guidance"]["rollback_plan"]


def _evidence(case, evidence_id):
    return next(item for item in case["evidence_catalog"] if item["evidence_id"] == evidence_id)
