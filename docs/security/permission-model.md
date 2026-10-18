# NEXUS Permission Model

> **Status:** Capability design for future phases. Not implemented in Phase 0. This document specifies intended boundaries; it does not grant or enforce runtime capabilities.

---

## Capability Categories

### Read-Oriented Capabilities (Phases 1–4)

| Capability | Description | Planned phase | Boundary |
|---|---|---|---|
| `telemetry.read` | Query logs, metrics, and traces | 1 | Read-only |
| `repository.read` | Read source code, commits, diffs, and PRs | 2 | Read-only |
| `deployment.read` | Read deployment history, config snapshots, and artifact metadata | 2 | Read-only |
| `incident.read` | Read incident records, hypotheses, evidence, and diagnoses | 2 | Read-only |
| `runbook.read` | Read runbooks, procedures, and historical resolutions | 3 | Read-only |

Phases 1–4 are read-only for the investigator. These capability names describe a future design, not available Phase 0 runtime tools.

### Sandbox-Local Remediation (Phase 7)

| Capability | Description | Planned phase | Required boundary |
|---|---|---|---|
| `workspace.modify` | Apply a patch to a checkout inside an isolated sandbox workspace | 7 | Workspace only; no remote Git write |
| `execution.test` | Run tests, linters, and type checkers | 7 | Sandboxed; bounded resources; no production network |
| `security.scan` | Run SAST, SCA, and secret scans | 7 | Sandboxed artifacts; does not mutate target systems |

These capabilities do not start before the isolated sandbox, policy enforcement, logging, and human-review gates have been implemented and reviewed.

### Remote Git-Provider Operations (Phase 8)

| Capability | Description | Planned phase | Required boundary |
|---|---|---|---|
| `branch.create` | Create a remote feature branch | 8 | Explicitly allowed unprotected feature branches only |
| `commit.push` | Push commits to an allowed remote feature branch | 8 | No tags, protected-branch writes, force-pushes, or bypass |
| `pull_request.create` | Open a PR against the designated base branch | 8 | Explicit human approval; normal provider protections apply |

**Capability naming:** the old generic `repository.write` identifier is withdrawn from the proposed capability model because it obscures whether a write is sandbox-local or remote. Use `workspace.modify` for sandbox-local edits and `commit.push` for remote feature-branch pushes. Do not silently alias the withdrawn name. The agent never receives protected-branch mutation or merge authority.

### High-Risk Capabilities — Never Granted

| Capability | Description | Exclusion |
|---|---|---|
| `production.execute` | Execute commands in production | Never |
| `production.mutate` | Modify production config, data, or infrastructure | Never |
| `unrestricted_shell` | Arbitrary shell command execution | Never |
| Protected-branch write / agent-controlled merge | Modify a protected target or merge a PR | Never; not an agent capability |

---

## Authorization Principles

### 1. Model Output Is Not Authorization

Text retrieved from a repository, log, ticket, or runbook is **untrusted data**. A model output or proposed tool call is not authorization.

Before a future tool call executes, a runtime policy boundary must validate its schema, identity, phase-appropriate capability, target/environment, and human-approval requirements, and record the decision and outcome in an audit trail. No such runtime enforcement exists in Phase 0.

### 2. Capability-Based, Not Role-Based

A future run's capability set must reflect its authorized phase, incident policy, target environment, and required human approval. No capability is inferred from text or model output.

### 3. Explicit Human Approval Gates

- `workspace.modify`: review/approval of the proposed remediation before application in the sandbox.
- `execution.test` and `security.scan`: allowed only after sandbox policy permits the run; outputs are artifacts, not proof of safety.
- `branch.create`, `commit.push`, and `pull_request.create`: explicit human approval at the Phase 8 provider boundary.
- PR merge: **human-controlled only**. There is no agent merge capability.

A successful sandbox test does not grant remote write permission automatically.

### 4. Audit Trail for Every Privileged Action

| Action | Required audit fields |
|---|---|
| Tool call | `run_id`, tool, parameters, result hash, duration, allow/deny decision |
| Capability grant | `run_id`, capability, grantor, reason, expiry |
| Human approval | proposal ID, approver, decision, comments, timestamp |
| Sandbox execution | attempt ID, command, exit code, artifacts, network attempts |
| Remote provider operation | repository, branch/ref, operation, actor, approval reference, provider result, timestamp |

### 5. Least Privilege by Default

- **Phases 1–4:** read-only investigation capabilities only.
- **Phase 5:** repository intelligence, commit analysis, runbook matching, and memory remain read-oriented. No write/test/sandbox/remote Git capabilities are granted.
- **Phase 7:** `workspace.modify`, `execution.test`, and `security.scan` are sandbox-local only, after isolation and policy gates exist.
- **Phase 8:** remote `branch.create`, `commit.push`, and `pull_request.create` only through scoped provider credentials and explicit human approval.
- **All phases:** protected-branch writes, agent-controlled merges, `production.execute`, `production.mutate`, and `unrestricted_shell` remain excluded.

No capability is granted by default; all require explicit policy.

---

## Capability Matrix by Phase

| Capability | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 |
|---|---|---|---|---|---|---|---|---|
| `telemetry.read` | Read | Read | Read | Read | Read | Read | Read | Read |
| `repository.read` | — | Read | Read | Read | Read | Read | Read | Read |
| `deployment.read` | — | Read | Read | Read | Read | Read | Read | Read |
| `incident.read` | — | Read | Read | Read | Read | Read | Read | Read |
| `runbook.read` | — | — | Read | Read | Read | Read | Read | Read |
| `workspace.modify` | — | — | — | — | — | — | Sandbox | Sandbox |
| `execution.test` | — | — | — | — | — | — | Sandbox | Sandbox |
| `security.scan` | — | — | — | — | — | — | Sandbox | Sandbox |
| `branch.create` | — | — | — | — | — | — | — | Human-gated, feature branch only |
| `commit.push` | — | — | — | — | — | — | — | Human-gated, feature-branch push only |
| `pull_request.create` | — | — | — | — | — | — | — | Human-gated |
| Protected-branch write / agent merge | Never | Never | Never | Never | Never | Never | Never | Never |

“Read” and “Sandbox” describe the future target design; they are not evidence of implemented capabilities. Phase 6 remains read-oriented until an explicitly approved later phase changes that boundary.

---

## Future: Token Management (Phase 8+)

- Git provider app with the minimum repository-scoped permissions needed for feature branches and PR creation.
- Short-lived tokens per authorized operation/run (OIDC/JIT where supported).
- Token rotation and revocation.
- Audit trail for all credential use.
- No provider credential is available inside the Phase 7 remediation sandbox.

---

## Phase 0: No Implementation

No authentication, authorization, or capability-enforcement code exists in Phase 0. This document describes a future design target, not functioning runtime controls.
