# ADR-0007: Product Naming & Positioning

- Status: Accepted
- Date: 2024-01-15

## Context

The internal codename "NEXUS" collides with existing products in the production intelligence / AI incident investigation space, notably **incident.io's "Nexus"** (announced 2023). This creates trademark and market confusion risk.

## Decision

**"NEXUS" remains a working codename. Final public branding is UNRESOLVED.**

### Current Positioning

- Internal codename: NEXUS
- Repository name: `nexus` (or `nexus-platform` if conflict)
- Package name: `nexus-benchmarks` (Phase 0 only)
- No public marketing, website, or trademark filing

### Required Before Public Launch

1. **Trademark search** — Comprehensive search for "NEXUS" in software/observability classes
2. **Differentiation articulation** — Clear, defensible positioning vs. incident.io Nexus and others
3. **Name selection** — Either:
   - Retain "NEXUS" with legal clearance + strong differentiation
   - Select new name with available trademark
4. **Brand assets** — Logo, tagline, messaging framework

### Differentiation Strategy (If Retaining Name)

NEXUS differentiates through:
- **Reproducible, frozen incident scenarios** — Not just live investigation
- **Evidence and counter-evidence linked to source records** — Not model assertions
- **Explicit handling of ambiguity and insufficient evidence** — Not forced answers
- **Investigation traces that can be audited and replayed** — Not black-box output
- **Controlled path from diagnosis to sandbox-tested pull request** — Not autonomous remediation

These are **engineering differentiators**, not marketing claims. They must be demonstrable in the product.

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Rename now (e.g., "AEGIS", "SENTINEL", "PRISM") | Premature; product not public; codename serves internal alignment |
| Ignore collision | Legal and market risk; irresponsible for a product intended for public use |

## Trade-offs and Consequences

**Pros:**
- Honest about uncertainty
- Avoids wasted rebranding effort if name changes
- Focuses team on engineering differentiation, not marketing
- Legal can run proper search when ready

**Cons:**
- Internal references use a name that may change
- External contributors may assume final name
- Repository/package name may need migration

## Validation / Reversal Criteria

- **Validate:** Before any public release (GitHub public, website, conference talk), trademark search completed and name decision documented in updated ADR
- **Reverse if:** Trademark search reveals blocking conflict → rename with new ADR