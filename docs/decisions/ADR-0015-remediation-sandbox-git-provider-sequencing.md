# ADR-0015: Remediation Sandbox vs Git-Provider Sequencing

- Status: Proposed
- Date: 2026-10-19

- Scope guard: **This draft records combination C1 only** (sandbox begins in Phase 7; remote provider branch/push/PR operations begin in Phase 8). Do not reuse this clause-level treatment unchanged if another combination is selected.
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

1. **C2 — sandbox Phase 5; remote PR Phase 7.** This preserves ADR-0004 as written and requires no ADR-0015, but expands Phase 5 beyond the roadmap's read-oriented scope and brings provider operations forward.
2. **C3 — sandbox Phase 7; remote PR Phase 7.** If selected, regenerate ADR-0015 to clarify ADR-0004's “Phase 5+” versus “Phase 7+” sandbox wording only; preserve workflow step 5's Phase 7 remote-PR timing. Do not use this draft's Phase 8 supersession of step 5.
3. **C4 — sandbox Phase 5; remote PR Phase 8.** If selected, regenerate ADR-0015 to supersede workflow step 5's remote-PR timing to Phase 8 **and explicitly resolve** the conflict between ADR-0004's Phase 5+ sandbox clause and “Isolated Remediation (Phase 7+)” heading. The decision must choose either (a) interpret that heading as the start of the complete workflow, while the sandbox environment begins in Phase 5, or (b) formally supersede the heading's phase label. Option (a) preserves more text but is the more strained reading; option (b) is clearer but changes the heading's intended timing.
4. **Keep remote PR creation in Phase 7.** This retains ADR-0004 workflow step 5 as written but requires provider credentials and audit/failure controls before Phase 8; it should be chosen only with explicit safeguards and an updated phase plan.

If C3 or C4 is selected, replace/regenerate this ADR's scope before acceptance so it precisely matches that combination. If C2 is selected, do not accept ADR-0015; preserve ADR-0004 unchanged.
## Trade-offs and Consequences

- Remote Git integration arrives later; Phase 7 can be tested without a live provider or token.
- Phase 7 still requires real sandbox isolation and tests; a review package is not proof of patch safety.
- Phase 8 must provide scoped credentials, auditing, and failure handling before remote writes.
- A maintainer must explicitly accept or reject this proposal before implementation. This ADR documents a proposed decision, not an enforced runtime policy.

## Validation / Reversal Criteria

Before implementation, reviewers must confirm that the roadmap and permission-model phase boundaries agree and that Phase 7 acceptance tests run without live provider credentials.

Revisit this decision if credential lifecycle, provider audit logging, and failure isolation are formally moved into Phase 7 with equivalent safeguards, or implementation evidence shows that provider-neutral Phase 7 acceptance cannot meet product needs. Any reversal must be recorded through a new or superseding ADR; do not silently edit ADR-0004.
