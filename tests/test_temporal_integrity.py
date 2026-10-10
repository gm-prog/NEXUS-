"""Temporal-cutoff regressions at helper, projection and installed-CLI boundaries."""

from copy import deepcopy
from datetime import timedelta

import pytest

from nexus_benchmarks.agent_view import (
    AGENT_VISIBLE_NESTED_KEYS,
    EVALUATOR_ONLY_NESTED_KEYS,
    build_agent_view,
)
from nexus_benchmarks.errors import TemporalIntegrityError
from nexus_benchmarks.temporal import (
    CUTOFF_TIMESTAMP_PATHS,
    EVALUATOR_TIMESTAMP_PATHS,
    TimestampFormatError,
    check_case_temporal_integrity,
    parse_instant,
)

# These cases isolate each typed, projected timestamp (including both optional
# window endpoints). sample_case is INC-001 with a 10:15Z cutoff.
FUTURE_FIELDS = [
    ("incident_window", None, "start"),
    ("evidence_catalog", 0, "event_time"),
    ("evidence_catalog", 0, "collection_time"),
    ("evidence_catalog", 0, "time_window_start"),
    ("evidence_catalog", 0, "time_window_end"),
    ("changes", 0, "timestamp"),
]
BAD_TIMESTAMPS = [
    "2024-01-15T10:00:00",  # naive: no offset
    "2024-01-15 10:00:00Z",  # space separator: outside the strict schema contract
    "not-a-timestamp",
    "2024-13-45T99:00:00Z",
    "2024-01-15T10:00:00+00:99",  # datetime alone silently normalises this offset
    "2024-01-15T10:00:00+24:00",
    "2024-01-15T10:00:00Z\n",  # full matching must reject trailing data
    "0001-01-01T00:00:00+01:00",  # UTC underflow: controlled error, not OverflowError
    "9999-12-31T23:00:00-02:00",  # UTC overflow
    "2024-01-15",
    "10:00:00Z",
    "",
    None,
    1705312800,
    ["2024-01-15T10:00:00Z"],
]


def _record(case, group, index):
    return case[group] if index is None else case[group][index]


def _date_time_paths(spec, prefix=""):
    paths = {prefix} if spec.get("format") == "date-time" else set()
    for key, child in spec.get("properties", {}).items():
        paths.update(_date_time_paths(child, prefix + "." + key if prefix else key))
    if "items" in spec:
        paths.update(_date_time_paths(spec["items"], prefix + "[]"))
    return paths


def test_every_schema_timestamp_has_a_temporal_disposition(incident_schema):
    """New typed time-bearing fields cannot silently bypass the policy."""
    assert _date_time_paths(incident_schema) == CUTOFF_TIMESTAMP_PATHS | EVALUATOR_TIMESTAMP_PATHS
    assert not CUTOFF_TIMESTAMP_PATHS & EVALUATOR_TIMESTAMP_PATHS
    for path in CUTOFF_TIMESTAMP_PATHS:
        group, field = path.replace("[]", "").split(".")
        assert field in AGENT_VISIBLE_NESTED_KEYS[group]


def test_window_end_is_explicitly_evaluator_only():
    assert EVALUATOR_ONLY_NESTED_KEYS["incident_window"] == frozenset({"end"})
    assert "end" not in AGENT_VISIBLE_NESTED_KEYS["incident_window"]


@pytest.mark.parametrize("end", ["2024-01-15T10:10:00Z", "2024-01-15T10:45:00Z"])
def test_window_end_never_appears_even_before_the_cutoff(sample_case, end):
    sample_case["incident_window"]["end"] = end
    assert "end" not in build_agent_view(sample_case)["incident_window"]


def test_every_current_projection_excludes_window_end(corpus):
    for case in corpus:
        assert set(build_agent_view(case)["incident_window"]) == {"start", "investigation_cutoff"}


def test_corpus_has_no_temporal_violations(corpus):
    assert [error for case in corpus for error in check_case_temporal_integrity(case)] == []


def test_every_current_projection_is_frozen_at_its_cutoff(corpus):
    """Independent assertions on every exposed typed timestamp, not just the helper."""
    for case in corpus:
        view = build_agent_view(case)
        cutoff = parse_instant(view["incident_window"]["investigation_cutoff"])
        assert parse_instant(view["incident_window"]["start"]) <= cutoff
        assert "end" not in view["incident_window"]
        for evidence in view["evidence_catalog"]:
            for field in ("event_time", "collection_time", "time_window_start", "time_window_end"):
                if field in evidence:
                    assert parse_instant(evidence[field]) <= cutoff, (case["case_id"], field)
        for change in view["changes"]:
            assert parse_instant(change["timestamp"]) <= cutoff, case["case_id"]


@pytest.mark.parametrize(("group", "index", "field"), FUTURE_FIELDS)
def test_future_timestamp_is_rejected_by_policy_and_projection(sample_case, group, index, field):
    _record(sample_case, group, index)[field] = "2024-01-15T10:20:00Z"
    errors = check_case_temporal_integrity(sample_case)
    assert any(field in error and "is after investigation_cutoff" in error for error in errors)
    with pytest.raises(TemporalIntegrityError, match=field):
        build_agent_view(sample_case)


@pytest.mark.parametrize(("group", "index", "field"), FUTURE_FIELDS)
def test_installed_cli_rejects_each_future_timestamp(run_cli, sample_case, group, index, field):
    sample_case["case_id"] = "INC-900"
    _record(sample_case, group, index)[field] = "2024-01-15T10:20:00Z"
    result = run_cli({"INC-900-future.json": sample_case}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert field in output and "is after investigation_cutoff" in output
    assert "Traceback" not in output


@pytest.mark.parametrize(("group", "index", "field"), FUTURE_FIELDS)
def test_malformed_and_naive_times_cannot_bypass_direct_projection(
    sample_case, group, index, field
):
    for timestamp in BAD_TIMESTAMPS:
        broken = deepcopy(sample_case)
        _record(broken, group, index)[field] = timestamp
        errors = check_case_temporal_integrity(broken)
        assert any(field in error and "RFC 3339" in error for error in errors)
        with pytest.raises(TemporalIntegrityError, match=field):
            build_agent_view(broken)


@pytest.mark.parametrize("field", ["event_time", "collection_time", "time_window_end"])
@pytest.mark.parametrize("timestamp", ["not-a-time", "2024-01-15T10:00:00"])
def test_installed_cli_rejects_malformed_evidence(run_cli, sample_case, field, timestamp):
    sample_case["case_id"] = "INC-900"
    sample_case["evidence_catalog"][0][field] = timestamp
    result = run_cli({"INC-900-malformed.json": sample_case}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert field in output and "date-time" in output
    assert "dependent checks NOT RUN" in output
    assert "Traceback" not in output


@pytest.mark.parametrize("field", ["start", "end", "investigation_cutoff"])
def test_missing_window_field_is_reported(sample_case, field):
    del sample_case["incident_window"][field]
    assert any(
        f"incident_window.{field} is missing" in e
        for e in check_case_temporal_integrity(sample_case)
    )
    with pytest.raises(TemporalIntegrityError, match=field):
        build_agent_view(sample_case)


@pytest.mark.parametrize("group", ["incident_window", "evidence_catalog"])
def test_reversed_windows_are_rejected(sample_case, group):
    record = sample_case[group] if group == "incident_window" else sample_case[group][0]
    start, end = (
        ("start", "end") if group == "incident_window" else ("time_window_start", "time_window_end")
    )
    record[start] = "2024-01-15T10:10:00Z"
    record[end] = "2024-01-15T10:05:00Z"
    assert any("reversed window" in error for error in check_case_temporal_integrity(sample_case))
    with pytest.raises(TemporalIntegrityError, match="reversed window"):
        build_agent_view(sample_case)


@pytest.mark.parametrize("field", ["time_window_start", "time_window_end"])
def test_partial_window_is_not_silently_accepted(sample_case, incident_validator, field):
    del sample_case["evidence_catalog"][0][field]
    assert list(incident_validator.iter_errors(sample_case)), "schema must require paired endpoints"
    assert any("supplied together" in error for error in check_case_temporal_integrity(sample_case))


def test_evidence_exactly_at_cutoff_is_accepted(sample_case):
    cutoff = sample_case["incident_window"]["investigation_cutoff"]
    for field in ("event_time", "collection_time", "time_window_end"):
        sample_case["evidence_catalog"][0][field] = cutoff
    assert check_case_temporal_integrity(sample_case) == []
    build_agent_view(sample_case)


@pytest.mark.parametrize(
    ("timestamp", "future"),
    [
        ("2024-01-15T11:16:00+01:00", True),
        ("2024-01-15T09:16:00-01:00", True),
        ("2024-01-15T11:14:00+01:00", False),
        ("2024-01-15T15:45:00+05:30", False),  # equal to 10:15Z cutoff
    ],
)
def test_offsets_are_compared_as_instants(sample_case, timestamp, future):
    sample_case["evidence_catalog"][0]["event_time"] = timestamp
    assert bool(check_case_temporal_integrity(sample_case)) is future


def test_equivalent_instants_with_different_offsets():
    assert parse_instant("2024-01-15T10:00:00Z") == parse_instant("2024-01-15T11:00:00+01:00")
    assert parse_instant("2024-01-15T10:00:00Z") == parse_instant("2024-01-15T15:30:00+05:30")


def test_string_order_is_not_chronological_order():
    cutoff = "2024-01-15T10:15:00Z"
    earlier = "2024-01-15T11:14:00+01:00"
    later = "2024-01-15T09:16:00-01:00"
    assert earlier > cutoff and parse_instant(earlier) < parse_instant(cutoff)
    assert later < cutoff and parse_instant(later) > parse_instant(cutoff)


def test_sub_microsecond_future_is_not_truncated(sample_case):
    sample_case["evidence_catalog"][0]["event_time"] = "2024-01-15T10:15:00.0000001Z"
    assert check_case_temporal_integrity(sample_case)
    assert parse_instant("2024-01-15T10:15:00.0000001Z") > parse_instant("2024-01-15T10:15:00Z")


@pytest.mark.parametrize(
    "timestamp",
    [
        "2024-01-15T10:00:00Z",
        "2024-01-15t10:00:00z",
        "2024-01-15T10:00:00.500Z",
        "2024-01-15T15:30:00+05:30",
    ],
)
def test_accepted_rfc3339_forms(timestamp):
    assert parse_instant(timestamp).utcoffset() == timedelta(0)


@pytest.mark.parametrize("timestamp", BAD_TIMESTAMPS)
def test_rejected_rfc3339_forms(timestamp):
    with pytest.raises(TimestampFormatError):
        parse_instant(timestamp)


def test_installed_cli_accepts_the_current_corpus(run_cli, corpus):
    cases = {f"{case['case_id']}-snapshot.json": case for case in corpus}
    result = run_cli(cases)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Temporal integrity checks: PASSED" in result.stdout


@pytest.mark.parametrize("value", ["2030-01-01T00:00:00Z", "2024-01-15T10:20:00"])
def test_opaque_config_cannot_hide_a_future_or_naive_time(sample_case, value):
    sample_case["changes"][0]["details"] = {"observed_at": value}
    with pytest.raises(TemporalIntegrityError, match="observed_at"):
        build_agent_view(sample_case)


def test_installed_cli_rejects_future_configuration_time(run_cli, sample_case):
    sample_case["case_id"] = "INC-900"
    sample_case["changes"][0]["details"] = {"observed_at": "2030-01-01T00:00:00Z"}
    result = run_cli({"INC-900-future-config.json": sample_case}, "--case", "INC-900")
    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "observed_at" in output and "is after investigation_cutoff" in output
    assert "Traceback" not in output


def test_opaque_config_past_time_is_accepted(sample_case):
    sample_case["changes"][0]["details"] = {"observed_at": "2024-01-15T15:30:00+05:30"}
    assert (
        build_agent_view(sample_case)["changes"][0]["details"]
        == sample_case["changes"][0]["details"]
    )
