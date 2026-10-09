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
| single_cause | 13 | INC-001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 018, 019, 020 |
| multi_factor | 1 | INC-021 |
| ambiguous | 4 | INC-013, 015, 017 |
| insufficient_evidence | 3 | INC-014, 016 |

**Total: 21 cases** (5 ambiguous/insufficient_evidence among first 20)

## Ground Truth / Agent-Visible Separation

**Critical for evaluation integrity:**

Each incident case contains two distinct sections:

1. **`evidence_catalog`** — Agent-visible evidence specifications. This is what the investigator (human or AI) can access at the `investigation_cutoff` time. Contains metrics, logs, traces, deployments, commits, configurations, etc.

2. **`ground_truth`** — Evaluator-only authoritative answer. Contains:
   - `root_cause_type`: The true root cause category
   - `primary_service_id`: The service where the root cause originates
   - `trigger_change_id`: The change that triggered the incident (if any)
   - `causal_chain`: The complete causal chain with evidence references
   - `ambiguity_note`: Explanation of why the case is ambiguous (if applicable)
   - `insufficient_evidence_note`: Explanation of what evidence is missing (if applicable)

**The evaluator must NEVER pass `ground_truth` to the agent.** The agent only receives `evidence_catalog` + `incident_window` + `affected_services` + `initial_symptoms`.

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
- Schema compliance for each case
- Unique case IDs
- Minimum case count (>= 20)
- Minimum ambiguous/insufficient_evidence count (>= 5 in first 20)
- Valid schema versions
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