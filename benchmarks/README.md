# NEXUS Benchmarks

This directory contains the benchmark suite for evaluating NEXUS incident investigation capabilities.

## Structure

```
benchmarks/
├── schema/
│   ├── incident-case.schema.json      # JSON Schema for incident scenarios
│   └── evaluation-result.schema.json  # JSON Schema for evaluation results
├── incidents/
│   ├── INC-001-null-pointer-payment.json
│   ├── INC-002-db-pool-exhaustion.json
│   ├── INC-003-slow-query-index-drop.json
│   ├── INC-004-redis-outage-cache-storm.json
│   ├── INC-005-downstream-timeout.json
│   ├── INC-006-http-5xx-config-typo.json
│   ├── INC-007-memory-leak-notification.json
│   ├── INC-008-cpu-saturation-recursion.json
│   ├── INC-009-queue-backlog-email.json
│   ├── INC-010-consumer-crash-kafka.json
│   ├── INC-011-faulty-deployment-ranking.json
│   ├── INC-012-config-drift-feature-flag.json
│   ├── INC-013-ambiguous-flag-dependency.json
│   ├── INC-014-insufficient-evidence-cdn.json
│   ├── INC-015-ambiguous-circular-dep.json
│   ├── INC-016-insufficient-evidence-broken-instrumentation.json
│   ├── INC-017-ambiguous-cache-stampede-vs-lock.json
│   ├── INC-018-schema-mismatch.json
│   ├── INC-019-db-lock-contention.json
│   ├── INC-020-fd-exhaustion.json
│   ├── INC-021-cascading-failure-auth.json
│   └── INC-022-ambiguous-flag-dependency-missing-comparison.json
└── expected-results/
    └── README.md
```

## Incident Categories Covered

| Category | Cases |
|----------|-------|
| unhandled_exception | INC-001 |
| connection_pool_exhaustion | INC-002 |
| slow_query | INC-003 |
| redis_outage | INC-004 |
| downstream_timeout | INC-005 |
| http_5xx_burst | INC-006, INC-016 |
| memory_leak | INC-007 |
| cpu_saturation | INC-008 |
| queue_backlog | INC-009 |
| consumer_crash | INC-010 |
| faulty_deployment | INC-011 |
| config_drift | INC-012 |
| feature_flag_regression | INC-022 |
| dependency_regression | INC-013, INC-014 |
| auth_failure | (covered in cascading) |
| schema_mismatch | INC-018 |
| cache_stampede | INC-017 |
| db_lock_contention | INC-019 |
| resource_exhaustion | INC-020 |
| cascading_failure | INC-015, INC-021 |

## Scenario Types

| Type | Count | Cases |
|------|-------|-------|
| single_cause | 16 | INC-001–013, 018, 019, 020 |
| multi_factor | 1 | INC-021 |
| ambiguous | 3 | INC-015, 017, 022 |
| insufficient_evidence | 2 | INC-014, 016 |

**Total: 22 cases** (5 of 22 = 22.7% ambiguous/insufficient_evidence)

The validator enforces **at least 20% of the whole suite**, not a fixed count:
`required_ambiguous_cases(total) = max(5, ceil(total * 0.20))`. Five ambiguous
cases is 25% of a 20-case suite but only 8% of a 60-case one.

## Ground Truth / Agent-Visible Separation

**Critical for evaluation integrity.** See
[ADR-0010](../docs/decisions/ADR-0010-agent-view-projection.md).

Each incident case contains both agent-visible evidence and the evaluator-only
answer key. The only supported boundary is the allowlisted projection in
`src/nexus_benchmarks/agent_view.py`.

**Agent-visible (allowlist):**

| Field | Notes |
|-------|-------|
| `schema_version`, `case_id` | Identity |
| `environment` | `name`, `region`, `cluster` |
| `incident_window` | `start`, `investigation_cutoff` only — `end` is always evaluator-only |
| `initial_symptoms` | |
| `affected_services` | `service_id`, `service_name` **only** — `impact` gives away the localisation answer |
| `evidence_catalog` | minus `synthetic_fixture_note`, which is fixture-authoring metadata |
| `changes` | Deployment/commit candidates, not the answer |

**Evaluator-only (never forwarded):** `title`, `category`, `scenario_type`,
`difficulty`, `description`, `ground_truth`, `expected_diagnosis`,
`misleading_or_confounding_signals`, `acceptable_alternatives`,
`required_checks`, `remediation_guidance`, `tags`.

The projection **fails closed**: an unclassified top-level key raises
`AgentViewError` instead of being forwarded. `incident_window.end`, service
`impact` and `synthetic_fixture_note` are explicitly classified nested exclusions.

### Frozen Snapshot Temporal Integrity

The cutoff is `incident_window.investigation_cutoff`, not `end`.
`temporal.py` parses timezone-aware RFC 3339 instants, normalises offsets to
UTC and compares exact fractional seconds, never timestamp strings.
`start`, evidence `event_time`/`collection_time` and optional window endpoints,
and every change `timestamp` must be at/before the cutoff. Optional evidence
windows require both endpoints in order. Future/malformed records are rejected,
not silently filtered. The CLI and direct `build_agent_view()` calls both
validate this contract. JSON Schema-invalid shapes never reach dependent
policy checks; the CLI prints NOT RUN diagnostics and exits nonzero.

Standalone timestamp-like configuration literals are also checked.
Opaque prose/configuration values still require author review; the validator
does not interpret arbitrary natural-language temporal or causal claims.

### What INC-013 and INC-022 Score

The question is the **cause of the observed incident**, not whether newly
deployed code has an independent latent defect. INC-013 retains both flag-on
and flag-off traces that fail at the same degraded dependency, so it is now
`single_cause` / `dependency_failure`. Its hypothetical code-bug alternative
was removed; the optional staging comparison tests resilience, not the already
supported diagnosis. All original evidence and timestamps are unchanged; the
legacy filename is retained for stable links.

Reclassification left four uncertainty cases, below the unchanged absolute
floor of five. INC-022 supplies a genuinely ambiguous contrasting snapshot:
regional degradation, only partial root spans, and no flag-off holdout. Both
local response handling and dependency failure explain the observed errors
without decisive failure-location data. No future experiment result is assumed.
See [ADR-0013](../docs/decisions/ADR-0013-observed-incident-target.md).

Other material corpus-review findings (not silently rewritten) are tracked in
[Phase 0 Status](../docs/development/phase-0-status.md): INC-016's arithmetic and
INC-019's unspecified blocking lock mode. Schema/CLI success is not proof of
benchmark realism or diagnosis accuracy.

## Verification Step Safety

See [ADR-0009](../docs/decisions/ADR-0009-verification-step-execution-classes.md).
Every `required_checks[]` entry must declare `execution_class`,
`target_environment`, `mutates_state` and `automated_execution_allowed`.

| `execution_class` | `mutates_state` | `automated_execution_allowed` | `target_environment` |
|-------------------|-----------------|-------------------------------|----------------------|
| `read_only` | `false` | `true` | any |
| `staging_experiment` | `true` | `false` | `staging` / `sandbox` |
| `human_approval_required` | `true` | `false` | any |

Tool names must be in the positive `TOOL_REGISTRY`: 18 read-only observation
names and 3 mutating names. Unknown names fail closed in **every** execution
class until explicitly reviewed/registered. Name patterns are defence in depth,
not the classification boundary. A registered mutating tool cannot be declared
`read_only`, and no state-changing operation may be autonomous anywhere.

Six mutating steps exist across INC-013, INC-015, INC-017, INC-019 and INC-022.
They are proposals for staging experiments or human-gated remediation, not
instructions to execute. The INC-013 proposal is non-critical to its diagnosis.
**This is fixture metadata validation, not runtime authorization.** Future
executable tools must enforce capability permissions and argument restrictions
at their execution boundary; none are implemented in Phase 0.

## Identifier Contract

See [ADR-0008](../docs/decisions/ADR-0008-benchmark-identifier-contract.md).

- `service_id` — `^svc-[a-z0-9]+(?:-[a-z0-9]+)*$` (e.g. `svc-001-payment`)
- `environment_id` — `^env-[a-z0-9]+(?:-[a-z0-9]+)*$` (e.g. `env-prod-us-east-1`)
- All timestamps are timezone-aware RFC 3339, UTC or numeric offset, and are **really validated** — the CLI
  enables `jsonschema.FormatChecker` and depends on `rfc3339-validator`.

## Validation

Run the benchmark validator:

```bash
# Validate all cases
nexus-benchmark validate

# Validate a specific case
nexus-benchmark validate --case INC-001

# List all cases
nexus-benchmark list
```

The validator checks:
- Schema compliance for each case, with format checking enabled
- Unique case IDs
- Minimum case count (>= 20)
- Minimum ambiguous/insufficient_evidence count (>= max(5, ceil(20% of suite)))
- Valid schema versions
- Execution policy for every verification step
- Typed temporal cutoff integrity for every case
- Agent-view separation from evaluator-only fields for every case
- Filename matches case_id is additionally pinned by pytest (not inferred from schema validity)

## Adding New Cases

1. Copy an existing case as template
2. Assign next sequential `INC-XXX` ID
3. Fill all required fields per schema
4. Ensure `scenario_type` is accurate
5. Register every verification tool and classify its side effects
6. Keep every projected typed timestamp at/before the cutoff and review prose
7. Run `nexus-benchmark validate` — must pass
8. Run `pytest` — all tests must pass

## Modifying Existing Cases

**Never silently change scenario meaning.** If a case's ground truth, evidence, or expected diagnosis changes:

1. Document the change in an ADR
2. Update any affected evaluation baselines
3. Ensure `nexus-benchmark validate` still passes

## Synthetic Fixture Notes

Each evidence item includes a `synthetic_fixture_note` field describing what fixture data Phase 1/2 will need to generate. These are not real telemetry — they are specifications for future data generation.