# ADR-0009: Execution Classification for Benchmark Verification Steps

- Status: Accepted
- Date: 2026-10-10

## Context

`required_checks[]` describes the verification steps a thorough investigation
is expected to take. Several fixtures modelled **mutating** actions as ordinary
investigation steps:

- `toggle_feature_flag` — INC-013 `chk-003`, INC-015 `chk-002`
- `execute_db_command` (cancel a migration / kill a query) — INC-017 `chk-001`,
  INC-019 `chk-002`
- `cache_warmup` — INC-017 `chk-002`

Nothing in the data model distinguished these from `query_metrics`. If a later
tool registry maps `tool` names straight onto executable tools, the benchmark
data itself would encourage an autonomous agent to mutate production during
investigation, contradicting
[ADR-0004](ADR-0004-read-only-investigation.md) and the permission model's
`production.mutate` exclusion.

## Decision

Every `required_checks[]` entry is **required** to declare four fields:

| Field | Type | Meaning |
|-------|------|---------|
| `execution_class` | `read_only` \| `staging_experiment` \| `human_approval_required` | Safety classification |
| `target_environment` | `production` \| `staging` \| `sandbox` \| `not_applicable` | What the step acts on |
| `mutates_state` | boolean | Does performing it change system state? |
| `automated_execution_allowed` | boolean | May an autonomous agent run it un-gated? |

Invariants, enforced both by JSON Schema `allOf` constraints and by
`src/nexus_benchmarks/execution_policy.py`:

1. `automated_execution_allowed: true` **only** for non-mutating steps.
2. `read_only` → `mutates_state: false`, `automated_execution_allowed: true`.
3. `staging_experiment` → `mutates_state: true`, target is `staging`/`sandbox`,
   `automated_execution_allowed: false`.
4. `human_approval_required` → `mutates_state: true`,
   `automated_execution_allowed: false`.
5. A tool whose name implies mutation (`toggle_`, `execute_`, `kill_`,
   `cache_warmup`, …) may never be classified `read_only`.

The four previously-unclassified mutating steps were rewritten as *proposed
controlled experiments* (staging target, human authorization required) or, for
INC-019, as an explicitly gated remediation action. The fixture wording now
says so, so a reader cannot mistake them for read-only queries.

The tool-name → mutation registry lives in
`src/nexus_benchmarks/execution_policy.py`. It is deliberately **not**
duplicated into JSON Schema: one source of truth is easier to keep correct than
two that can drift.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Blocklist of known-mutating tool names only | Fails open: a new mutating tool name is treated as safe until someone notices |
| Remove the mutating steps from the fixtures | They are the honest way to disambiguate those scenarios; deleting them weakens the benchmark |
| Rename the tools to neutral names and carry the hazard in prose | Hides the hazard from the very registry that would execute it |
| Allow automated production mutation behind a "critical" flag | `critical` already means "important to the diagnosis", not "safe to run" |

## Trade-offs and Consequences

**Pros:**

- A future tool registry can refuse to execute any step whose
  `automated_execution_allowed` is `false` without guessing from the tool name.
- The benchmark encodes the investigation/remediation boundary from ADR-0004 in
  data, not just in prose.
- Classification violations fail CI, so new fixtures cannot regress.

**Cons:**

- Four boolean/enum fields per check make fixtures more verbose.
- The tool-name heuristic is a prefix/contains test; a mutating tool with an
  innocuous name would need to be added to the registry by hand.
- Scoring "investigation coverage" must now decide whether to require
  non-`read_only` steps to be *proposed* rather than *performed*.

## Validation / Reversal Criteria

- **Validate:** `nexus-benchmark validate` reports execution-policy violations;
  `tests/test_execution_policy.py` covers each invariant plus the
  unclassified/misclassified cases.
- **Reverse if:** a future phase defines a real capability/permission service —
  then `execution_class` should be derived from that service's capability
  metadata rather than duplicated per fixture.
