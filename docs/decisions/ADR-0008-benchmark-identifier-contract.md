# ADR-0008: Benchmark Identifier Contract — Stable Slugs, Not UUIDs

- Status: Accepted
- Date: 2026-10-10

## Context

`benchmarks/schema/incident-case.schema.json` declared `format: "uuid"` for
`service_id` and `environment_id`, while all 21 committed fixtures used
readable slugs such as `svc-001-payment` and `env-prod-us-east-1`. The
validator built `Draft202012Validator(incident_schema)` without a
`format_checker`, so `jsonschema` ignored every `format` keyword and the
contradiction was never detected.

Two defects had to be fixed together:

1. The declared contract and the data disagreed. A consumer that *does* enable
   format checking would reject every fixture.
2. No format was actually enforced, so a malformed `date-time` (for example
   `2024-01-27 10:00:00`) would have passed CI.

## Decision

**Identifiers in benchmark fixtures are stable, human-readable slugs with an
explicit regular expression, not UUIDs.**

| Field | Pattern | Example |
|-------|---------|---------|
| `service_id` | `^svc-[a-z0-9]+(?:-[a-z0-9]+)*$` | `svc-001-payment` |
| `environment_id` | `^env-[a-z0-9]+(?:-[a-z0-9]+)*$` | `env-prod-us-east-1` |

Both patterns live once, in `$defs`, and are referenced everywhere the
identifier appears (including `evaluation-result.schema.json`), so the two
schemas cannot drift apart.

**`date-time` and `uuid` formats are really validated.** The CLI constructs its
validators with `jsonschema.FormatChecker()`, and `rfc3339-validator` is a
declared runtime dependency because `jsonschema` silently skips `date-time`
without it. `run_id` in `evaluation-result.schema.json` remains a genuine UUID
and is now actually checked.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Convert all 21 fixtures to UUIDs | Loses legibility in every evidence summary, review comment and diff; ~1,000 identifier occurrences would have to be rewritten and cross-checked by hand |
| Keep `format: "uuid"` and drop format checking | Documents a contract the data violates; leaves `date-time` unchecked as well |
| Keep UUIDs and disable `format` entirely | Same as above, and throws away real validation of timestamps |

## Trade-offs and Consequences

**Pros:**

- Fixture files stay reviewable — `svc-014-recommendation` is meaningful in a
  diff, `3f2a…` is not.
- `date-time` values are now genuinely rejected when malformed (covered by
  negative tests in `tests/test_schema_validation.py`).
- One `$defs` entry means the identifier contract has a single definition.

**Cons:**

- Slug identifiers are not globally unique by construction; uniqueness is a
  repository convention enforced by review and by the cross-reference checks
  in the validator.
- Adding `rfc3339-validator` adds a runtime dependency that would be
  unnecessary if `date-time` were not used.

## Validation / Reversal Criteria

- **Validate:** `nexus-benchmark validate` passes with `FormatChecker` enabled;
  negative tests prove malformed timestamps and UUID-shaped service IDs fail.
- **Reverse if:** identifiers need to be minted by an external system that
  issues UUIDs — then migrate every fixture in one commit and update the
  `$defs` patterns and the negative tests together.
