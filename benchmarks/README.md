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
│   └── INC-021-cascading-failure-auth.json
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
| feature_flag_regression | INC-013 |
| dependency_regression | INC-014, INC-019 |
| auth_failure | (covered in cascading) |
| schema_mismatch | INC-018 |
| cache_stampede | INC-017 |
| db_lock_contention | INC-019 |
| resource_exhaustion | INC-020 |
| cascading_failure | INC-015, INC-021 |

## Scenario Types

| Type | Count | Cases |
|------|-------|-------|
| single_cause | 15 | INC-001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 018, 019, 020 |
| multi_factor | 1 | INC-021 |
| ambiguous | 3 | INC-013, 015, 017 |
| insufficient_evidence | 2 | INC-014, 016 |

**Total: 21 cases** (5 of 21 = 23.8% ambiguous/insufficient_evidence)

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
| `incident_window` | `start`, `end`, `investigation_cutoff` |
| `initial_symptoms` | |
| `affected_services` | `service_id`, `service_name` **only** — `impact` gives away the localisation answer |
| `evidence_catalog` | minus `synthetic_fixture_note`, which is fixture-authoring metadata |
| `changes` | Deployment/commit candidates, not the answer |

**Evaluator-only (never forwarded):** `title`, `category`, `scenario_type`,
`difficulty`, `description`, `ground_truth`, `expected_diagnosis`,
`misleading_or_confounding_signals`, `acceptable_alternatives`,
`required_checks`, `remediation_guidance`, `tags`.

The projection **fails closed**: an unclassified top-level key raises
`AgentViewError` instead of being forwarded.

## Verification Step Safety

See [ADR-0009](../docs/decisions/ADR-0009-verification-step-execution-classes.md).
Every `required_checks[]` entry must declare `execution_class`,
`target_environment`, `mutates_state` and `automated_execution_allowed`.

| `execution_class` | `mutates_state` | `automated_execution_allowed` | `target_environment` |
|-------------------|-----------------|-------------------------------|----------------------|
| `read_only` | `false` | `true` | any |
| `staging_experiment` | `true` | `false` | `staging` / `sandbox` |
| `human_approval_required` | `true` | `false` | any |

Mutating steps exist in INC-013, INC-015, INC-017 and INC-019. They are
rewritten as *proposed controlled experiments* (staging) or *gated remediation
actions* (human approval) and may never be executed automatically against
production.

## Identifier Contract

See [ADR-0008](../docs/decisions/ADR-0008-benchmark-identifier-contract.md).

- `service_id` — `^svc-[a-z0-9]+(?:-[a-z0-9]+)*$` (e.g. `svc-001-payment`)
- `environment_id` — `^env-[a-z0-9]+(?:-[a-z0-9]+)*$` (e.g. `env-prod-us-east-1`)
- All timestamps are RFC 3339 UTC and are **really validated** — the CLI
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
- Agent-view separation from ground truth for every case
- Filename matches case_id

## Adding New Cases

1. Copy an existing case as template
2. Assign next sequential `INC-XXX` ID
3. Fill all required fields per schema
4. Ensure `scenario_type` is accurate
5. Run `nexus-benchmark validate` — must pass
6. Run `pytest` — all tests must pass

## Modifying Existing Cases

**Never silently change scenario meaning.** If a case's ground truth, evidence, or expected diagnosis changes:

1. Document the change in an ADR
2. Update any affected evaluation baselines
3. Ensure `nexus-benchmark validate` still passes

## Synthetic Fixture Notes

Each evidence item includes a `synthetic_fixture_note` field describing what fixture data Phase 1/2 will need to generate. These are not real telemetry — they are specifications for future data generation.