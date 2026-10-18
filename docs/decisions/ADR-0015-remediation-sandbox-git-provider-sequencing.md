# ADR-0015: Remediation Sandbox vs Git-Provider Sequencing

- Status: Proposed
- Date: 2026-10-19

## Context

Accepted [ADR-0004](ADR-0004-read-only-investigation.md) contains both the statement “Phase 5+: Remediation runs in isolated sandbox with human approval gate” and the section heading “Isolated Remediation (Phase 7+).” Its workflow step 5 says that, on approval, a PR is created through the Git provider API with a scoped token. The roadmap places sandboxed remediation in Phase 7 and credential management, provider integration, and privileged-action audit hardening in Phase 8.

Taken literally, these statements blur three boundaries: read-oriented repository intelligence in Phase 5; sandbox-local patch/test/scan work; and remote provider writes. Remote PR creation before Phase 8's credential, audit, and failure controls are specified would make those boundaries hard to implement consistently.

## Decision

**Proposed decision:** interpret the sandbox-start intent as Phase 7, aligning the general “Phase 5+” statement with the more specific “Phase 7+” remediation section and the roadmap.

- Phases 0–4 remain strictly read-only investigation.
- Phase 5 remains read-oriented repository intelligence, commit analysis, and memory; it does not receive sandbox mutation/test or remote Git capabilities.
- Phase 7 builds the isolated, non-production sandbox and produces patch, test/scan, log, and evidence artifacts in a human-review package. Acceptance tests use a local/fake provider interface; no live provider credentials or remote branch/PR operation is required in Phase 7.
- Phase 8 owns remote feature-branch creation, pushing commits to explicitly allowed unprotected feature branches, and opening remote PRs through scoped, short-lived credentials with audited operations and explicit human approval.
- The agent never receives protected-branch-write, force-push, bypass, or merge authority. Humans merge PRs through the provider's normal protections and status checks.

## Relationship to ADR-0004

If accepted, this ADR **clarifies the phase timing** of ADR-0004's “Phase 5+” versus “Phase 7+” sandbox language and **supersedes only the timing** in the “On approval: PR created via Git provider API (scoped token)” workflow step: remote provider branch/push/PR operations move to Phase 8.

ADR-0004's body is not modified by this proposal. Its read-only investigation boundary, human-approval requirement, isolated sandbox, no-production-credentials rule, restricted network/resource limits, audit requirements, and prohibition on `production.execute`/`production.mutate` remain preserved. This proposal creates no merge capability and weakens no safety constraint.

## Alternatives Considered

1. **Keep remote PR creation in Phase 7.** This retains ADR-0004 step 5 as written but requires provider credentials and audit/failure controls before Phase 8.
2. **Start sandbox mutation in Phase 5.** This reads “Phase 5+” literally but expands Phase 5 beyond the roadmap's read-oriented intelligence scope and conflicts with the more specific “Phase 7+” heading.
3. **Defer the clarification.** This avoids a new ADR but leaves implementers with conflicting phase boundaries.

## Trade-offs and Consequences

- Remote Git integration arrives later; Phase 7 can be tested without a live provider or token.
- Phase 7 still requires real sandbox isolation and tests; a review package is not proof of patch safety.
- Phase 8 must provide scoped credentials, auditing, and failure handling before remote writes.
- A maintainer must explicitly accept or reject this proposal before implementation. This ADR documents a proposed decision, not an enforced runtime policy.

## Validation / Reversal Criteria

Before implementation, reviewers must confirm that the roadmap and permission-model phase boundaries agree and that Phase 7 acceptance tests run without live provider credentials.

Revisit this decision if credential lifecycle, provider audit logging, and failure isolation are formally moved into Phase 7 with equivalent safeguards, or implementation evidence shows that provider-neutral Phase 7 acceptance cannot meet product needs. Any reversal must be recorded through a new or superseding ADR; do not silently edit ADR-0004.
