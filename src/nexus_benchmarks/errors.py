"""Exception types raised by the NEXUS benchmark tooling.

Messages live inside the exception classes (not at the ``raise`` sites) so that
error text is owned by the error type and stays testable.
"""

from pathlib import Path

import click


class NexusBenchmarkError(click.ClickException):
    """Base class for user-facing errors reported by the benchmark CLI."""


class BenchmarkAssetsNotFoundError(NexusBenchmarkError):
    """Raised when the benchmark schema/fixture directory cannot be located."""

    def __init__(self, searched: list[Path], env_var: str) -> None:
        listed = "\n".join(f"  - {candidate}" for candidate in searched)
        super().__init__(
            "Could not locate benchmark assets (schema/incident-case.schema.json).\n"
            f"Searched:\n{listed}\n"
            f"Set {env_var} to point at the benchmark directory explicitly."
        )


class SchemaLoadError(NexusBenchmarkError):
    """Raised when a JSON schema cannot be read, parsed, or meta-validated."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"Invalid schema {path}: {detail}")


class CaseLoadError(NexusBenchmarkError):
    """Raised when an incident case file cannot be read or parsed."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"Invalid JSON in {path}: {detail}")


class MalformedCaseError(NexusBenchmarkError):
    """Raised when a case has a shape the tooling cannot project or classify.

    Distinct from :class:`AgentViewError`: this is a structural defect (for
    example ``evidence_catalog: [null]``), not an answer-leakage defect.
    """

    def __init__(self, case_id: object, detail: str) -> None:
        super().__init__(f"Case {case_id}: {detail}")

    @classmethod
    def case_not_an_object(cls, value: object) -> "MalformedCaseError":
        """Build the error for a case file whose root is not a JSON object."""
        found = "null" if value is None else type(value).__name__
        return cls("<malformed case>", f"case must be a JSON object, got {found}")

    @classmethod
    def wrong_type(
        cls, case_id: object, subject: str, expected: str, value: object
    ) -> "MalformedCaseError":
        """Build the error for a field that has the wrong JSON type."""
        found = "null" if value is None else type(value).__name__
        return cls(case_id, f"{subject} must be {expected}, got {found}")


class TemporalIntegrityError(NexusBenchmarkError):
    """Projection refused because its investigation snapshot is not frozen."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(
            "Refusing to build an agent view: temporal integrity failed:\n"
            + "\n".join(f"  - {violation}" for violation in violations)
        )


class AgentViewError(NexusBenchmarkError):
    """Raised when a case cannot be projected onto the agent-visible view.

    The projection fails closed: any top-level key that has not been explicitly
    classified as agent-visible or evaluator-only is treated as a potential
    answer leak.
    """

    def __init__(self, case_id: str, unknown_keys: list[str]) -> None:
        super().__init__(
            f"Case {case_id}: refusing to build an agent view because it contains "
            f"unclassified top-level keys {sorted(unknown_keys)}. Every top-level key must "
            "be explicitly allowlisted as agent-visible or evaluator-only."
        )
