"""Temporal cutoff integrity (audit §2).

The frozen-snapshot contract says an investigator may only see what was known
at ``incident_window.investigation_cutoff``. These tests pin that down:

* ``incident_window.end`` is not model-visible when it is after the cutoff;
* no agent-visible evidence, window or change may be dated after the cutoff;
* timestamps are compared as instants, never as strings;
* malformed or naive timestamps cannot bypass the invariant.
"""

from copy import deepcopy

import pytest

from nexus_benchmarks.agent_view import CONDITIONALLY_EXCLUDED_KEYS, build_agent_view
from nexus_benchmarks.cli import MIN_TOTAL_CASES
from nexus_benchmarks.temporal import (
    TimestampFormatError,
    check_case_temporal_integrity,
    parse_instant,
    try_parse_instant,
)


def test_every_fixture_has_a_window_end_after_its_cutoff(corpus):
    """The leak this module exists to close is present in every fixture."""
    count = 0
    for case in corpus:
        window = case["incident_window"]
        if parse_instant(window["end"]) > parse_instant(window["investigation_cutoff"]):
            count += 1
    assert count == len(corpus)
    assert len(corpus) >= MIN_TOTAL_CASES


def test_window_end_is_not_in_the_agent_view(corpus):
    for case in corpus:
        window = build_agent_view(case)["incident_window"]
        assert "end" not in window, f"{case['case_id']} leaked incident_window.end"


def test_window_end_is_kept_when_it_is_not_in_the_future(sample_case):
    """An already-finished window is ordinary context, not future knowledge."""
    sample_case["incident_window"]["end"] = sample_case["incident_window"]["start"]
    assert "end" in build_agent_view(sample_case)["incident_window"]


def test_window_end_is_dropped_when_the_cutoff_is_unparseable(sample_case):
    """Fail closed: 'cannot prove it is past' must not become 'assume it is past'."""
    sample_case["incident_window"]["investigation_cutoff"] = "whenever"
    assert "end" not in build_agent_view(sample_case)["incident_window"]


def test_cutoff_and_start_stay_visible(corpus):
    for case in corpus:
        window = build_agent_view(case)["incident_window"]
        assert set(window) == {"start", "investigation_cutoff"}


def test_end_is_explicitly_classified_as_conditionally_excluded():
    assert CONDITIONALLY_EXCLUDED_KEYS["incident_window"] == frozenset({"end"})


def test_corpus_has_no_temporal_violations(corpus):
    assert [error for case in corpus for error in check_case_temporal_integrity(case)] == []


def test_no_agent_visible_timestamp_exceeds_its_cutoff(corpus):
    """Acceptance condition: nothing in a projection is dated after the cutoff."""
    for case in corpus:
        cutoff = parse_instant(case["incident_window"]["investigation_cutoff"])
        view = build_agent_view(case)
        for evidence in view["evidence_catalog"]:
            for field in ("event_time", "collection_time", "time_window_end"):
                if field in evidence:
                    assert parse_instant(evidence[field]) <= cutoff, (case["case_id"], field)
        for change in view["changes"]:
            assert parse_instant(change["timestamp"]) <= cutoff, case["case_id"]
        assert parse_instant(view["incident_window"]["start"]) <= cutoff, case["case_id"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_time", "2024-01-15T10:20:00Z"),
        ("collection_time", "2024-01-15T10:20:00Z"),
        ("time_window_end", "2024-01-15T10:20:00Z"),
    ],
)
def test_future_evidence_is_rejected(sample_case, field, value):
    sample_case["evidence_catalog"][0][field] = value
    errors = check_case_temporal_integrity(sample_case)
    assert errors and "is after investigation_cutoff" in errors[0] and field in errors[0]


def test_future_change_is_rejected(sample_case):
    sample_case["changes"][0]["timestamp"] = "2024-01-15T10:30:00Z"
    errors = check_case_temporal_integrity(sample_case)
    assert errors and "changes[0]" in errors[0] and "timestamp" in errors[0]


def test_future_window_start_is_rejected(sample_case):
    sample_case["incident_window"]["start"] = "2024-01-15T10:20:00Z"
    errors = check_case_temporal_integrity(sample_case)
    assert errors and "incident_window.start" in errors[0]


def test_reversed_evidence_window_is_rejected(sample_case):
    sample_case["evidence_catalog"][0]["time_window_start"] = "2024-01-15T10:10:00Z"
    sample_case["evidence_catalog"][0]["time_window_end"] = "2024-01-15T10:05:00Z"
    errors = check_case_temporal_integrity(sample_case)
    assert any(
        "time_window_start" in error and "after time_window_end" in error for error in errors
    )


def test_reversed_incident_window_is_rejected(sample_case):
    sample_case["incident_window"]["start"] = "2024-01-15T10:10:00Z"
    sample_case["incident_window"]["end"] = "2024-01-15T10:05:00Z"
    errors = check_case_temporal_integrity(sample_case)
    assert any(
        "incident_window.start" in error and "after incident_window.end" in error
        for error in errors
    )


def test_evidence_exactly_at_the_cutoff_is_accepted(sample_case):
    cutoff = sample_case["incident_window"]["investigation_cutoff"]
    sample_case["evidence_catalog"][0]["event_time"] = cutoff
    sample_case["evidence_catalog"][0]["collection_time"] = cutoff
    assert check_case_temporal_integrity(sample_case) == []


def test_offsets_are_compared_as_instants(sample_case):
    """10:00:00Z and 11:00:00+01:00 are the same instant, not a string mismatch."""
    assert parse_instant("2024-01-15T10:00:00Z") == parse_instant("2024-01-15T11:00:00+01:00")
    assert parse_instant("2024-01-15T10:00:00Z") < parse_instant("2024-01-15T10:00:00-01:00")

    # 11:16+01:00 is 10:16Z — after the 10:15Z cutoff.
    sample_case["evidence_catalog"][0]["event_time"] = "2024-01-15T11:16:00+01:00"
    assert check_case_temporal_integrity(sample_case), (
        "a later instant written with a positive offset must still be rejected"
    )

    # 11:14+01:00 is 10:14Z — before the cutoff.
    sample_case["evidence_catalog"][0]["event_time"] = "2024-01-15T11:14:00+01:00"
    assert check_case_temporal_integrity(sample_case) == [], (
        "an earlier instant written with a positive offset must be accepted"
    )


def test_negative_offset_leak_is_caught(sample_case):
    """09:16-01:00 is 10:16Z: it sorts *before* the cutoff as a string but is later.

    A lexicographic comparison would let this future record through.
    """
    value = "2024-01-15T09:16:00-01:00"
    cutoff = sample_case["incident_window"]["investigation_cutoff"]
    assert value < cutoff, "string ordering says this is before the cutoff"
    assert parse_instant(value) > parse_instant(cutoff), "instant ordering says it is after"

    sample_case["evidence_catalog"][0]["event_time"] = value
    assert check_case_temporal_integrity(sample_case)


def test_positive_offset_record_is_not_false_flagged(sample_case):
    """11:14+01:00 is 10:14Z: it sorts *after* the cutoff as a string but is earlier."""
    value = "2024-01-15T11:14:00+01:00"
    cutoff = sample_case["incident_window"]["investigation_cutoff"]
    assert value > cutoff, "string ordering says this is after the cutoff"
    assert parse_instant(value) < parse_instant(cutoff), "instant ordering says it is before"

    sample_case["evidence_catalog"][0]["event_time"] = value
    assert check_case_temporal_integrity(sample_case) == []


@pytest.mark.parametrize(
    "value",
    [
        "2024-01-15T10:00:00Z",
        "2024-01-15t10:00:00z",
        "2024-01-15T10:00:00.500Z",
        "2024-01-15T10:00:00+05:30",
    ],
)
def test_accepted_rfc3339_forms(value):
    assert parse_instant(value).utcoffset() is not None


@pytest.mark.parametrize(
    "value",
    [
        "2024-01-15T10:00:00",  # naive: no offset
        "2024-01-15 10:00:00Z",  # space separator (RFC 3339 NOTE form, rejected here)
        "not-a-timestamp",
        "2024-13-45T99:00:00Z",
        "2024-01-15",  # date only
        "10:00:00Z",  # time only
        "",
        None,
        1705312800,  # epoch seconds
        ["2024-01-15T10:00:00Z"],
    ],
)
def test_rejected_timestamp_forms(value):
    with pytest.raises(TimestampFormatError):
        parse_instant(value)
    assert try_parse_instant(value) is None


def test_naive_timestamp_cannot_bypass_the_invariant(sample_case):
    """A naive cutoff is reported rather than silently assumed to be UTC."""
    sample_case["incident_window"]["investigation_cutoff"] = "2024-01-15T10:15:00"
    errors = check_case_temporal_integrity(sample_case)
    assert any("investigation_cutoff" in error and "RFC 3339" in error for error in errors)


@pytest.mark.parametrize("field", ["start", "end", "investigation_cutoff"])
def test_missing_window_field_is_reported(sample_case, field):
    broken = deepcopy(sample_case)
    del broken["incident_window"][field]
    errors = check_case_temporal_integrity(broken)
    assert any(f"incident_window.{field} is missing" in error for error in errors)


def test_all_current_fixture_timestamps_are_timezone_aware(corpus):
    for case in corpus:
        window = case["incident_window"]
        for field in ("start", "end", "investigation_cutoff"):
            assert try_parse_instant(window[field]) is not None, (case["case_id"], field)
        for evidence in case["evidence_catalog"]:
            for field in ("event_time", "collection_time", "time_window_start", "time_window_end"):
                if field in evidence:
                    assert try_parse_instant(evidence[field]) is not None, (case["case_id"], field)
        for change in case["changes"]:
            assert try_parse_instant(change["timestamp"]) is not None, case["case_id"]


# --- End-to-end enforcement through the installed CLI ---------------------


def test_installed_cli_rejects_a_future_dated_case(run_cli, corpus):
    """The invariant must hold in CI, not only when a helper is called directly."""
    case = deepcopy(corpus[0])
    case["case_id"] = "INC-900"
    case["evidence_catalog"][0]["event_time"] = "2030-01-01T00:00:00Z"
    result = run_cli({"INC-900-future-dated.json": case}, "--case", "INC-900")
    assert result.returncode != 0, result.stdout
    assert "is after investigation_cutoff" in result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_installed_cli_accepts_the_committed_corpus(run_cli, corpus):
    cases = {f"{case['case_id']}-{index}.json": case for index, case in enumerate(corpus)}
    result = run_cli(cases)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Temporal integrity checks: PASSED" in result.stdout


def test_installed_cli_rejects_a_naive_cutoff(run_cli, corpus):
    """A naive cutoff must fail the CLI, not be silently assumed UTC."""
    case = deepcopy(corpus[0])
    case["case_id"] = "INC-900"
    case["incident_window"]["investigation_cutoff"] = "2024-01-15T10:15:00"
    result = run_cli({"INC-900-naive.json": case}, "--case", "INC-900")
    assert result.returncode != 0, result.stdout
    assert "Traceback" not in result.stderr
