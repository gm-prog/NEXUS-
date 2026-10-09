# ADR-0002: Benchmark Format: JSON Schema

- Status: Accepted
- Date: 2024-01-15

## Context

Phase 0 requires a machine-readable, language-neutral format for incident scenario fixtures and evaluation results. Requirements:
- Human-editable (engineers author scenarios)
- IDE support (validation, autocomplete)
- CI-validatable without network/LLM
- Versioned with explicit migration path
- No code generation required for consumers

## Decision

**Use JSON Schema (Draft 2020-12) as the source of truth for benchmark fixtures.**

Files:
- `benchmarks/schema/incident-case.schema.json` — Scenario specification
- `benchmarks/schema/evaluation-result.schema.json` — Evaluation run result

Both schemas:
- Declare `$schema: "https://json-schema.org/draft/2020-12/schema#"`
- Use `additionalProperties: false` to catch typos
- Include `schema_version` field in each document
- Are committed and validated in CI via `nexus-benchmark validate`

## Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Pydantic models + JSON | Python-only; requires code generation for other languages |
| TypeScript interfaces + JSON | TypeScript-only; no standard validation CLI |
| Protocol Buffers | Not human-editable; requires code generation |
| YAML with JSON Schema | YAML adds complexity (anchors, types); JSON is sufficient |
| Custom validator code | Duplicates schema logic; harder to maintain |

## Trade-offs and Consequences

**Pros:**
- Universal: any language with JSON Schema validator can consume
- Mature ecosystem: `jsonschema` (Python), `ajv` (JS), `gojsonschema` (Go), etc.
- IDE support: VS Code, IntelliJ, Vim/Neovim with LSP
- Explicit versioning via `schema_version` field
- CI validation is a single command

**Cons:**
- JSON verbose for large fixtures (mitigated: scenarios are moderate size)
- No comments in JSON (mitigated: schema includes `description` fields)
- JSON Schema learning curve (mitigated: team familiarity, good docs)

## Validation / Reversal Criteria

- **Validate:** All 20+ fixtures validate; CLI catches malformed/duplicate/invalid cases; CI passes
- **Reverse if:** Application API (Phase 3+) requires OpenAPI as source of truth; then benchmark schemas may align or migrate (see ADR-0006)