# NEXUS Schema Strategy

> **Status:** Documented for Phase 0. Decisions recorded in ADRs.

---

## Why JSON Schema for Phase 0 Benchmarks

### Requirements

1. **Language-neutral** — Benchmark fixtures must be readable/writable by any future implementation (Python, TypeScript, Go, Rust) without code generation.
2. **Human-editable** — Engineers author scenario fixtures directly in JSON. Schema provides IDE validation and documentation.
3. **Machine-validatable** — CI and CLI must validate structure, required fields, and cross-file invariants without an LLM.
4. **Versioned** — Schema evolution must be explicit and validated.
5. **No runtime dependencies** — Validation runs in CI without network or model access.

### Decision

**JSON Schema (Draft 2020-12)** is the source of truth for benchmark fixture shapes.

- `benchmarks/schema/incident-case.schema.json` — Incident scenario specification
- `benchmarks/schema/evaluation-result.schema.json` — Evaluation run result contract

Both schemas:
- Declare `$schema: "https://json-schema.org/draft/2020-12/schema#"`
- Use `additionalProperties: false` where appropriate to catch typos
- Define `schema_version` field for forward compatibility
- Are committed to the repository and validated in CI

---

## What Is NOT Decided Yet

### Application API Schemas

When a real API is introduced (Phase 3+), we must decide:

| Question | Options | Decision Criteria |
|----------|---------|-------------------|
| **Source of truth** | OpenAPI 3.1, Pydantic models, TypeScript interfaces, JSON Schema | Single source; generated clients; validation in gateway |
| **Code generation** | `openapi-python-client`, `typescript-fetch`, `oapi-codegen` | Language coverage, maintenance burden |
| **Compatibility policy** | Strict backward compatibility, versioned endpoints, consumer-driven contracts | Breaking change frequency, consumer coordination |
| **Schema registry** | None (git), Buf, Apicurio, Confluent | Scale, team workflow, tooling |

**ADR required** before duplicating domain definitions across languages.

---

## Schema Versioning Principles

### Explicit Version Field

Every schema-conformant document includes:

```json
{
  "schema_version": "1.0.0",
  ...
}
```

Format: `MAJOR.MINOR.PATCH` (SemVer-like but for schemas).

### Compatibility Rules

| Version Change | When | Migration |
|----------------|------|-----------|
| **PATCH** | Bug fixes in validation (stricter `pattern`, added `enum` value) | None — existing valid docs remain valid |
| **MINOR** | New optional fields, new enum values, relaxed constraints | None — existing valid docs remain valid |
| **MAJOR** | Removed/renamed required fields, changed types, stricter `additionalProperties` | Migration script + ADR; old schema retained for transition |

### Validation in CI

- `nexus-benchmark validate` checks:
  - Each fixture validates against its declared `schema_version`
  - All fixtures use the same `schema_version` (or documented exceptions)
  - Schema files themselves validate against meta-schema
- CI fails on any validation error

### Deliberate Migrations

- No silent changes to existing fixture meaning
- Schema version bump + migration script + ADR for any breaking change
- Old schema retained in `benchmarks/schema/v{N}/` for reference

---

## Benchmark Schema Separation

Two distinct schemas enforce the **ground truth / agent-visible separation**:

### `incident-case.schema.json` (Scenario Specification)

Contains **both**:
- `evidence_catalog` — Agent-visible evidence specifications (what the investigator can access)
- `ground_truth` — Evaluator-only authoritative answer (root cause, ambiguity designation, etc.)

**Validation rule:** The CLI validates structure only. It does NOT enforce separation — that is a semantic rule for evaluator implementation.

### `evaluation-result.schema.json` (Run Result)

Represents a completed evaluation run. Contains:
- Scores for each measure
- Evidence references used by the agent
- Invalid/missing evidence references
- Latency, cost, tool counts
- Evaluator version

No ground truth — only the run's measurements.

---

## Future Evolution Path

| Phase | Schema Need | Likely Approach |
|-------|-------------|-----------------|
| 1 | Demo app telemetry schemas | JSON Schema (OTel semantic conventions) |
| 2 | Application state API | OpenAPI 3.1 + code generation |
| 3 | Investigation API | OpenAPI 3.1 + code generation |
| 4 | Agent tool interfaces | JSON Schema (tool input/output) |
| 7 | Remediation sandbox API | OpenAPI 3.1 + code generation |

**Principle:** Start with JSON Schema for data fixtures. Move to OpenAPI when HTTP APIs exist. Avoid maintaining parallel definitions for the same domain.