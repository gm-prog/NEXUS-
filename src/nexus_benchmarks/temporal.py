"""Fail-closed temporal validation for frozen investigation snapshots.

The typed timestamps the investigator can see must be valid timezone-aware
RFC 3339 instants at or before ``incident_window.investigation_cutoff``.
Future evidence is rejected, not silently filtered: ``evidence_catalog`` and
``changes`` describe inputs available to the investigator, not future records.

``incident_window.end`` is evaluator-only metadata and never projected, even
when it happens to be before the cutoff. It is still checked for a valid format
and a coherent incident window. All existing fixture timestamps are preserved.

Malformed timestamps are errors here as well as in JSON Schema. Direct callers
of the projection must not be able to bypass the cutoff by omitting the CLI's
schema-validation step. Instants are normalised to UTC and compared with exact
fractional-second precision (``datetime`` alone silently truncates after six
fractional digits).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from rfc3339_validator import validate_rfc3339

from nexus_benchmarks.errors import MalformedCaseError

# Full-match, ASCII-only, mandatory offset. RFC 3339 permits lowercase t/z;
# normalise those before passing the value to the RFC 3339 backend.
_RFC3339_SHAPE = re.compile(
    r"(?P<whole>[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(?P<fraction>\.[0-9]+)?(?P<zone>[Zz]|[+-][0-9]{2}:[0-9]{2})"
)

# A schema/projection drift test enumerates all declared date-time fields and
# requires an explicit disposition. Opaque prose/config values still need
# author review; adding a new typed timestamp requires extending this contract.
CUTOFF_TIMESTAMP_PATHS = frozenset({
    "incident_window.start",
    "incident_window.investigation_cutoff",
    "evidence_catalog[].event_time",
    "evidence_catalog[].collection_time",
    "evidence_catalog[].time_window_start",
    "evidence_catalog[].time_window_end",
    "changes[].timestamp",
})
EVALUATOR_TIMESTAMP_PATHS = frozenset({"incident_window.end"})


class TimestampFormatError(ValueError):
    """A timestamp cannot be interpreted as an RFC 3339 instant."""

    @classmethod
    def for_value(cls, value: object, reason: str) -> "TimestampFormatError":
        return cls(f"{value!r} is not a usable timezone-aware RFC 3339 instant: {reason}")


@dataclass(frozen=True, order=True)
class Instant:
    """UTC whole second plus an exact fraction, ordered chronologically."""

    whole_second: datetime
    fraction: Decimal

    def isoformat(self) -> str:
        """Canonical UTC representation, preserving sub-microsecond precision."""
        whole = self.whole_second.isoformat(timespec="seconds")
        fraction = format(self.fraction, "f")[1:].rstrip("0") if self.fraction else ""
        return whole[:-6] + fraction + "+00:00"

    def utcoffset(self) -> timedelta | None:
        """The normalised instant is timezone-aware UTC, never a naive time."""
        return self.whole_second.utcoffset()


def parse_instant(value: object) -> Instant:
    """Parse a timezone-aware RFC 3339 timestamp into an exact UTC instant.

    The same RFC 3339 backend used by jsonschema verifies calendar dates,
    clock components and numeric offsets. Full matching also rejects trailing
    data. Leap seconds are unsupported by that backend and fail closed.
    Unrepresentable UTC dates (offsets crossing datetime's year limits) yield
    a controlled format error, not an OverflowError.
    """
    if not isinstance(value, str):
        raise TimestampFormatError.for_value(value, "expected a string")
    parts = _RFC3339_SHAPE.fullmatch(value)
    if parts is None or not validate_rfc3339(value.upper()):
        raise TimestampFormatError.for_value(value, "invalid date, clock, offset or syntax")
    try:
        whole = datetime.fromisoformat(parts["whole"].upper() + parts["zone"].upper())
        whole = whole.astimezone(UTC)
    except (ValueError, OverflowError) as error:
        raise TimestampFormatError.for_value(value, "UTC instant is out of range") from error
    return Instant(whole, Decimal("0" + (parts["fraction"] or ".0")))


def check_temporal_integrity(cases: list[object]) -> list[str]:
    """Report all temporal violations, including malformed structures."""
    return [error for case in cases for error in check_case_temporal_integrity(case)]


def check_case_temporal_integrity(case: object) -> list[str]:
    """Report a case's cutoff violations without assuming schema-valid input."""
    if not isinstance(case, dict):
        return [MalformedCaseError.case_not_an_object(case).message]
    case_id = str(case.get("case_id", "<unknown case>"))
    window = case.get("incident_window")
    if not isinstance(window, dict):
        return [
            MalformedCaseError.wrong_type(case_id, "incident_window", "an object", window).message
        ]

    errors: list[str] = []
    times = {
        field: _read_time(window, field, f"{case_id}: incident_window.{field}", errors)
        for field in ("start", "end", "investigation_cutoff")
    }
    cutoff = times["investigation_cutoff"]
    _check_order(times["start"], times["end"], f"{case_id}: incident_window.start > end", errors)
    _check_cutoff(times["start"], cutoff, f"{case_id}: incident_window.start", errors)

    _check_records(case, "evidence_catalog", case_id, cutoff, errors)
    _check_records(case, "changes", case_id, cutoff, errors)
    return errors


def _check_records(
    case: dict, key: str, case_id: str, cutoff: Instant | None, errors: list[str]
) -> None:
    records = case.get(key)
    if not isinstance(records, list):
        errors.append(MalformedCaseError.wrong_type(case_id, key, "an array", records).message)
        return
    for index, record in enumerate(records):
        where = f"{case_id}: {key}[{index}]"
        if not isinstance(record, dict):
            errors.append(
                MalformedCaseError.wrong_type(case_id, where, "an object", record).message
            )
            continue
        if key == "evidence_catalog":
            _check_evidence_times(record, where, cutoff, errors)
        else:
            instant = _read_time(record, "timestamp", f"{where}.timestamp", errors)
            _check_cutoff(instant, cutoff, f"{where}.timestamp", errors)


def _check_evidence_times(
    record: dict, where: str, cutoff: Instant | None, errors: list[str]
) -> None:
    times = {}
    for field in ("event_time", "collection_time", "time_window_start", "time_window_end"):
        if field.startswith("time_window_") and field not in record:
            continue
        times[field] = _read_time(record, field, f"{where}.{field}", errors)
        _check_cutoff(times[field], cutoff, f"{where}.{field}", errors)

    # Aggregate/trace windows may be absent, but a supplied interval must have
    # both endpoints. Schema dependentRequired asserts the same shape rule.
    if ("time_window_start" in record) != ("time_window_end" in record):
        errors.append(f"{where}: time_window_start and time_window_end must be supplied together")
    _check_order(
        times.get("time_window_start"),
        times.get("time_window_end"),
        f"{where}: time_window_start > time_window_end",
        errors,
    )


def check_visible_time_literals(view: dict) -> list[str]:
    """Check standalone timestamp-like values in otherwise opaque projected data.

    Configuration details may contain a timestamp without a schema ``format``
    annotation. An ISO-shaped standalone value must not be a future/naive-time
    backdoor. Embedded dates inside prose or URLs still require author review;
    this does not pretend to interpret natural-language temporal claims.
    """
    errors: list[str] = []
    window = view.get("incident_window", {})
    if not isinstance(window, dict) or "investigation_cutoff" not in window:
        return errors  # the typed temporal validator diagnoses this first
    cutoff = parse_instant(window["investigation_cutoff"])
    _check_literals(view, str(view.get("case_id", "<unknown case>")), cutoff, errors)
    return errors


def _check_literals(value: object, path: str, cutoff: Instant, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _check_literals(item, f"{path}.{key}", cutoff, errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_literals(item, f"{path}[{index}]", cutoff, errors)
    elif isinstance(value, str) and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ][0-9:.+Zz-]+", value
    ):
        try:
            instant = parse_instant(value)
        except TimestampFormatError as error:
            errors.append(f"{path}: {error}")
        else:
            _check_cutoff(instant, cutoff, path, errors)


def _read_time(record: dict, field: str, path: str, errors: list[str]) -> Instant | None:
    if field not in record:
        errors.append(f"{path} is missing")
        return None
    try:
        return parse_instant(record[field])
    except TimestampFormatError as error:
        errors.append(f"{path}: {error}")
        return None


def _check_cutoff(
    instant: Instant | None, cutoff: Instant | None, path: str, errors: list[str]
) -> None:
    if instant is not None and cutoff is not None and instant > cutoff:
        errors.append(
            f"{path} {instant.isoformat()} is after investigation_cutoff {cutoff.isoformat()}"
        )


def _check_order(start: Instant | None, end: Instant | None, path: str, errors: list[str]) -> None:
    if start is not None and end is not None and start > end:
        errors.append(f"{path}: reversed window ({start.isoformat()} > {end.isoformat()})")
