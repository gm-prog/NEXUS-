"""Ambiguity coverage invariant (finding 6): enforced as a ratio, not a fixed count."""

import pytest

from nexus_benchmarks.cli import (
    AMBIGUOUS_TYPES,
    MIN_AMBIGUITY_CASES,
    MIN_AMBIGUITY_RATIO,
    check_composition,
    required_ambiguous_cases,
)

LARGE_SUITE = 60
EXPECTED_MIN_RATIO = 0.20


def synthetic_suite(total: int, ambiguous: int) -> list[dict]:
    """A deterministic synthetic benchmark with `ambiguous` ambiguous cases."""
    return [
        {
            "case_id": f"INC-{index + 1:03d}",
            "schema_version": "1.0.0",
            "scenario_type": "ambiguous" if index < ambiguous else "single_cause",
        }
        for index in range(total)
    ]


@pytest.mark.parametrize(
    ("total", "expected"),
    [(20, 5), (25, 5), (30, 6), (60, 12), (100, 20)],
)
def test_required_ambiguous_count_tracks_the_ratio(total, expected):
    assert required_ambiguous_cases(total) == expected


def test_required_ambiguous_count_never_drops_below_the_floor():
    for total in range(1, LARGE_SUITE):
        assert required_ambiguous_cases(total) >= MIN_AMBIGUITY_CASES


def test_minimum_ratio_is_twenty_percent():
    assert MIN_AMBIGUITY_RATIO == EXPECTED_MIN_RATIO


def test_larger_suite_with_only_five_ambiguous_cases_fails():
    """Regression: five ambiguous cases is 25% of 20 but only 8% of 60."""
    errors = check_composition(synthetic_suite(total=LARGE_SUITE, ambiguous=5))
    assert any("Insufficient ambiguous" in error for error in errors)


def test_error_message_states_the_ratio_requirement():
    errors = check_composition(synthetic_suite(total=LARGE_SUITE, ambiguous=5))
    message = next(error for error in errors if "Insufficient ambiguous" in error)
    assert f"{EXPECTED_MIN_RATIO:.0%}" in message
    assert str(LARGE_SUITE) in message


def test_larger_suite_meeting_the_ratio_passes():
    errors = check_composition(synthetic_suite(total=LARGE_SUITE, ambiguous=12))
    assert [error for error in errors if "Insufficient ambiguous" in error] == []


def test_committed_corpus_meets_the_ratio(corpus):
    ambiguous = sum(1 for case in corpus if case.get("scenario_type") in AMBIGUOUS_TYPES)
    assert ambiguous >= required_ambiguous_cases(len(corpus))
    assert [error for error in check_composition(corpus) if "Insufficient ambiguous" in error] == []


def test_ambiguous_cases_carry_an_ambiguity_note(corpus):
    for case in corpus:
        if case.get("scenario_type") in AMBIGUOUS_TYPES:
            ground_truth = case.get("ground_truth", {})
            assert ground_truth.get("ambiguity_note") or ground_truth.get(
                "insufficient_evidence_note"
            ), f"{case['case_id']}: ambiguous case missing an ambiguity note"


def test_insufficient_evidence_cases_carry_a_note(corpus):
    for case in corpus:
        if case.get("scenario_type") == "insufficient_evidence":
            assert case["ground_truth"].get("insufficient_evidence_note"), (
                f"{case['case_id']}: insufficient_evidence case missing a note"
            )
