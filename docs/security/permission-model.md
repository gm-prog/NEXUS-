# NEXUS Permission Model

> **Status:** Capability design for future phases. Not implemented in Phase 0.

---

## Capability Categories

### Read-Oriented (Phases 1–4)

| Capability | Description | Phase | Risk |
|------------|-------------|-------|------|
| `telemetry.read` | Query logs, metrics, traces from telemetry storage | 1 | Low — read-only, no PII by default |
| `repository.read` | Read source code, commits, diffs, PRs from Git provider | 2 | Medium — source code access |
| `deployment.read` | Read deployment history, config snapshots, artifact metadata | 2 | Low |
| `incident.read` | Read incident records, hypotheses, evidence, diagnoses | 2 | Medium — incident history |
| `runbook.read` | Read runbooks, procedures, historical resolutions | 3 | Low |

### Potential Write/Test (Phases 5–7+)

| Capability | Description | Phase | Risk |
|------------|-------------|-------|------|
| `branch.create` | Create new branch in repository | 5 | Medium — repo write |
| `repository.write` | Push commits, create tags | 5 | High — modifies history |
| `code.modify` | Apply patches to source files in sandbox | 5 | High — code mutation |
| `execution.test` | Run tests, linters, type checkers in sandbox | 5 | Medium — compute, no network |
| `security.scan` | Run SAST, SCA, secret scans in sandbox | 5 | Low — read-only scans |
| `pull_request.create` | Open PR with changes | 7 | High — triggers CI/CD, human review |

### High Risk — Excluded from Early Implementation

| Capability | Description | Exclusion Reason |
|------------|-------------|------------------|
| `production.execute` | Execute commands in production environment | Never — violates read-only investigation principle |
| `production.mutate` | Modify production state (config, data, infra) | Never — violates safety boundary |
| `unrestricted_shell` | Arbitrary shell command execution | Never — RCE vector |

---

## Authorization Principles

### 1. Model Output Is Not Authorization

Text retrieved from a repository, log, ticket, or runbook is **untrusted data**. A model's output (including tool calls) is **not authorization**.

**Enforcement:** Every tool call is validated at a policy boundary:
- Tool schema validates parameters
- Permission service checks caller's capabilities
- Audit log records: caller, tool, parameters, result, decision

### 2. Capability-Based, Not Role-Based

Permissions are fine-grained capabilities, not coarse roles. An agent run receives a capability set based on:
- Phase (read-only vs. write-capable)
- Incident severity (SEV1 may allow broader read)
- Tenant policy (future multi-tenancy)
- Human approval (for write capabilities)

### 3. Explicit Human Approval Gates

Write capabilities require explicit human confirmation:
- `code.modify` → Human reviews diff before sandbox execution
- `pull_request.create` → Human approves PR creation after sandbox success
- `repository.write` → Never directly; only via approved PR merge

### 4. Audit Trail for Every Privileged Action

| Action | Audit Fields |
|--------|--------------|
| Tool call | `run_id`, `tool`, `parameters`, `result_hash`, `duration_ms`, `allowed` |
| Capability grant | `run_id`, `capability`, `granted_by`, `reason`, `expires_at` |
| Human approval | `proposal_id`, `approver`, `decision`, `comments`, `timestamp` |
| Sandbox execution | `attempt_id`, `command`, `exit_code`, `artifacts`, `network_attempts` |

### 5. Least Privilege by Default

- Phase 1–4 agents: `{telemetry.read, repository.read, deployment.read, incident.read, runbook.read}`
- Phase 5+ agents: Add `{branch.create, code.modify, execution.test, security.scan}` **only in sandbox**
- Phase 7+ agents: Add `{pull_request.create}` **only after human approval**

No capability is granted by default; all are explicit.

---

## Capability Matrix by Phase

| Capability | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 7 |
|------------|---------|---------|---------|---------|---------|---------|
| `telemetry.read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `repository.read` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `deployment.read` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `incident.read` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `runbook.read` | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| `branch.create` | ❌ | ❌ | ❌ | ❌ | ✅ (sandbox) | ✅ |
| `repository.write` | ❌ | ❌ | ❌ | ❌ | ✅ (sandbox) | ✅ |
| `code.modify` | ❌ | ❌ | ❌ | ❌ | ✅ (sandbox) | ✅ |
| `execution.test` | ❌ | ❌ | ❌ | ❌ | ✅ (sandbox) | ✅ |
| `security.scan` | ❌ | ❌ | ❌ | ❌ | ✅ (sandbox) | ✅ |
| `pull_request.create` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (human gate) |

---

## Future: Token Management (Phase 8+)

- Git provider app with scoped permissions (contents:read, pull_requests:write, etc.)
- Short-lived tokens per agent run (OIDC/JIT)
- Token rotation and revocation
- Audit log of all token usage

---

## Phase 0: No Implementation

No authentication, authorization, or capability enforcement code exists in Phase 0. This document defines the **design target** for later phases.