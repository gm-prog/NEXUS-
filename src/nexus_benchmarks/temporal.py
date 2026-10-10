"""Temporal integrity of the agent-visible part of a benchmark case.

The frozen-snapshot contract (``docs/architecture/evidence-model.md``,
``docs/development/testing-strategy.md``) says an investigator may only see
what was known at ``incident_window.investigation_cutoff``.

A case file nevertheless records the *whole* incident, including
``incident_window.end`` — the time the incident was resolved or observation
ended — which in every current fixture is **after** the cutoff. Forwarding it
hands the investigator the future: the length and eventual resolution of an
incident that is still open at the moment of investigation.

Two consequences, both implemented here:

1. ``incident_window.end`` is evaluator-side metadata whenever it is later than
   the cutoff. :func:`nexus_benchmarks.agent_view.build_agent_view` drops it in
   that case (see ``CONDITIONALLY_EXCLUDED_KEYS``).
2. No agent-visible record may be dated after the cutoff. That is enforced as a
   corpus invariant by :func:`check_temporal_integrity`, not left to fixture
   authors.

Timestamps are parsed as timezone-aware RFC 3339 instants and compared as
instants. They are never compared lexicographically, and a naive timestamp
(no offset) is rejected rather than assumed to be UTC.

This module is deliberately tolerant of malformed *structures*: a structurally
invalid case produces a controlled error string, never an exception, so the
validator can report every problem in a fixture in one pass. Malformed
*timestamp strings* are reported by the schema layer (``format: date-time``)
and skipped here, so the same defect is not reported twice.
"""

import re
from datetime import UTC, datetime

from nexus_benchmarks.errors import MalformedCaseError

#: Strict RFC 3339 date-time: a ``T`` separator and a numeric offset or ``Z``
#: are both mandatory. A naive timestamp is rejected rather than silently
#: assumed to be UTC, and the space separator permitted only by the RFC's
#: NOTE (§5.6, "by mutual agreement") is rejected too.
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)


class TimestampFormatError(ValueError):
    """Raised when a timestamp is not a timezone-aware RFC 3339 instant.

    The message is assembled by :meth:`for_value` so that the raise sites stay
    short (Ruff ``TRY003``) and the wording lives with the error type.
    """

    @classmethod
    def for_value(cls, value: object, reason: str) -> "TimestampFormatError":
        return cls(f"{value!r} is not a usable instant: {reason}")


def parse_instant(value: object) -> datetime:
    """Parse ``value`` into a timezone-aware ``datetime`` normalised to UTC.

    Raises:
        TimestampFormatError: if ``value`` is not a string, does not match the
            RFC 3339 shape, or carries no timezone offset.
    """
    if not isinstance(value, str):
        raise TimestampFormatError.for_value(value, "not an RFC 3339 string")
    if not RFC3339_PATTERN.match(value):
        raise TimestampFormatError.for_value(value, "does not match RFC 3339")
    try:
        parsed = datetime.fromisoformat(_normalise(value))
    except ValueError as error:
        raise TimestampFormatError.for_value(value, f"not a valid date-time: {error}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TimestampFormatError.for_value(value, "no timezone offset")
    return parsed.astimezone(UTC)


def _normalise(value: str) -> str:
    """Upper-case the ``t`` separator and ``z`` zone for ``fromisoformat``.

    RFC 3339 permits lower case; ``datetime.fromisoformat`` does not. The regex
    has already fixed the shape, so only these two positions need adjusting.
    """
    normalised = value[:10] + "T" + value[11:]
    if normalised.endswith("z"):
        normalised = normalised[:-1] + "Z"
    return normalised


def try_parse_instant(value: object) -> datetime | None:
    """``parse_instant`` that returns ``None`` instead of raising."""
    try:
        return parse_instant(value)
    except TimestampFormatError:
        return None


def check_temporal_integrity(cases: list[object]) -> list[str]:
    """Return temporal-cutoff violations for every case in ``cases``."""
    errors: list[str] = []
    for case in cases:
        errors.extend(check_case_temporal_integrity(case))
    return errors


def check_case_temporal_integrity(case: object) -> list[str]:
    """Return temporal-cutoff violations for a single case."""
    if not isinstance(case, dict):
        return [MalformedCaseError.case_not_an_object(case).message]

    case_id = str(case.get("case_id", "<unknown case>"))
    window = case.get("incident_window")
    if not isinstance(window, dict):
        return [
            MalformedCaseError.wrong_type(case_id, "incident_window", "an object", window).message
        ]

    errors: list[str] = []
    errors.extend(_check_window(case_id, window))

    cutoff = try_parse_instant(window.get("investigation_cutoff"))
    if cutoff is None:
        # Without a usable cutoff no other temporal rule can be evaluated.
        return errors
    if "start" in window:
        start = try_parse_instant(window["start"])
        if start is not None and start > cutoff:
            errors.append(_after(case_id, "incident_window.start", window["start"], cutoff))
    if "start" in window and "end" in window:
        start = try_parse_instant(window["start"])
        end = try_parse_instant(window["end"])
        if start is not None and end is not None and start > end:
            errors.append(
                f"{case_id}: incident_window.start {window['start']} is after "
                f"incident_window.end {window['end']}"
            )

    errors.extend(_check_evidence(case, case_id, cutoff))
    errors.extend(_check_changes(case, case_id, cutoff))
    return errors


def _check_window(case_id: str, window: dict) -> list[str]:
    errors = []
    for field in ("start", "end", "investigation_cutoff"):
        if field not in window:
            errors.append(f"{case_id}: incident_window.{field} is missing")
        elif try_parse_instant(window[field]) is None:
            errors.append(
                f"{case_id}: incident_window.{field} {window[field]!r} is not a "
                "timezone-aware RFC 3339 timestamp"
            )
    return errors


def _check_evidence(case: dict, case_id: str, cutoff: datetime) -> list[str]:
    catalog = case.get("evidence_catalog", [])
    if not isinstance(catalog, list):
        return [
            MalformedCaseError.wrong_type(case_id, "evidence_catalog", "an array", catalog).message
        ]

    errors: list[str] = []
    for index, item in enumerate(catalog):
        if not isinstance(item, dict):
            errors.append(
                MalformedCaseError.wrong_type(
                    case_id, f"evidence_catalog[{index}]", "an object", item
                ).message
            )
            continue
        subject = f"evidence_catalog[{index}] ({item.get('evidence_id', '?')})"
        for field in ("event_time", "collection_time", "time_window_end"):
            errors.extend(_at_or_before(case_id, subject, item, field, cutoff))
        errors.extend(_ordered_window(case_id, subject, item))
    return errors


def _check_changes(case: dict, case_id: str, cutoff: datetime) -> list[str]:
    changes = case.get("changes", [])
    if not isinstance(changes, list):
        return [MalformedCaseError.wrong_type(case_id, "changes", "an array", changes).message]

    errors: list[str] = []
    for index, change in enumerate(changes):
        if not isinstance(change, dict):
            errors.append(
                MalformedCaseError.wrong_type(
                    case_id, f"changes[{index}]", "an object", change
                ).message
            )
            continue
        subject = f"changes[{index}] ({change.get('change_id', '?')})"
        errors.extend(_at_or_before(case_id, subject, change, "timestamp", cutoff))
    return errors


def _at_or_before(
    case_id: str, subject: str, record: dict, field: str, cutoff: datetime
) -> list[str]:
    if field not in record:
        return []
    instant = try_parse_instant(record[field])
    if instant is None or instant <= cutoff:
        return []
    return [_after(case_id, f"{subject} {field}", record[field], cutoff)]


def _ordered_window(case_id: str, subject: str, record: dict) -> list[str]:
    if "time_window_start" not in record or "time_window_end" not in record:
        return []
    window_start = try_parse_instant(record["time_window_start"])
    window_end = try_parse_instant(record["time_window_end"])
    if window_start is None or window_end is None or window_start <= window_end:
        return []
    return [
        f"{case_id}: {subject} time_window_start {record['time_window_start']} is after "
        f"time_window_end {record['time_window_end']}"
    ]


def _after(case_id: str, subject: str, value: object, cutoff: datetime) -> str:
    return (
        f"{case_id}: {subject} {value} is after investigation_cutoff "
        f"{cutoff.isoformat()} — the investigator could not have known it"
    )
