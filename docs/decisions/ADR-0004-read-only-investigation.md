# ADR-0004: Read-Only Investigation & Isolated Remediation

- Status: Accepted
- Date: 2024-01-15

## Context

AI agents with production write access are a safety risk. NEXUS must enforce a clear boundary: investigation is read-only; remediation is isolated and human-gated.

## Decision

**Phases 0–4: Strictly read-only investigation. No production mutations.**

**Phase 5+:** Remediation runs in isolated sandbox with human approval gate.

### Read-Only Investigation (Phases 0–4)

- Tools expose only read operations: `query_logs`, `query_metrics`, `get_trace`, `get_deployment`, `get_commit`, `search_runbooks`, `get_historical_incidents`
- No `create`, `update`, `delete`, `execute` operations
- Agent capability set enforced at tool registry level
- CI validates no write tools registered in read-only phases

### Isolated Remediation (Phase 7+)

- **Sandbox:** Ephemeral environment (container/VM) with:
  - No network egress (or allowlist only)
  - No production credentials
  - Read-only filesystem except workspace
  - Resource limits (CPU, memory, time, disk)
- **Workflow:**
  1. Agent generates patch in sandbox workspace
  2. Sandbox runs: tests, lint, type-check, security scans (SAST, SCA, secrets)
  3. Artifacts stored (logs, coverage, SBOM, scan results)
  4. Human reviews artifacts → approves/rejects
  5. On approval: PR created via Git provider API (scoped token)
- **No `production.execute` or `production.mutate` capabilities ever.**

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Agent with production write (with guardrails) | Guardrails fail; model output is not authorization |
| Human-in-the-loop for every tool call | Too slow; defeats automation value |
| Remediation in staging environment | Staging ≠ production; drift causes false confidence |

## Trade-offs and Consequences

**Pros:**
- Clear safety boundary: investigation ≠ remediation
- Human accountability for production changes
- Sandbox enables aggressive testing (chaos, load) without risk
- Audit trail: diagnosis → proposal → sandbox results → approval → PR

**Cons:**
- Longer time-to-fix (human gate)
- Sandbox infrastructure investment
- May not catch production-specific issues (data volume, real traffic)

## Validation / Reversal Criteria

- **Validate:** Phase 7 sandbox catches >90% of introduced regressions in benchmark remediation tasks; zero production incidents from NEXUS-generated PRs in first 6 months
- **Reverse if:** Sandbox cannot reproduce production behavior for critical paths (e.g., database lock contention at scale) — then design production canary with automatic rollback instead