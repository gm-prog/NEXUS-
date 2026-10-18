# NEXUS — Phase 0: Foundation and Benchmark

> **NEXUS turns software telemetry and engineering change history into a reproducible, evidence-backed investigation, then eventually helps engineers validate a proposed fix in an isolated environment.**

## Overview

NEXUS is an AI-native engineering investigation platform designed to correlate runtime telemetry, service dependencies, source-code changes, and deployment history to produce evidence-backed incident investigations.

**This repository contains Phase 0 only:** the greenfield foundation, architecture documentation, benchmark schemas, 20+ incident scenario fixtures, a deterministic validation CLI, automated tests, and CI. No telemetry ingestion, AI agents, UI, databases, or remediation systems are implemented.

## Problem & Intended Workflow

Engineers investigating a failing service need to answer:

- What is failing, and when did it begin?
- Which service or dependency is affected?
- What changed shortly before the failure?
- Which traces, logs, metrics, commits, deployments, and prior incidents are relevant?
- What evidence supports each proposed explanation?
- What evidence contradicts it, and what remains unknown?
- What would verify or disprove the current hypothesis?
- Can a proposed remediation be tested safely before a human reviews it?

NEXUS does not claim to be an all-knowing autonomous SRE. The design favors explicit evidence, deterministic checks, calibrated uncertainty, human oversight, and reproducible evaluation.

## Core Design Principles

| Principle | Engineering Consequence |
|-----------|------------------------|
| Evidence before AI | Deterministic retrieval and correlation run before any model reasoning |
| Deterministic systems do deterministic work | Queries, correlations, and anomaly detection use pure functions |
| AI for interpretation, not replacement | Models propose hypotheses; tools verify them |
| Conclusions reference evidence records | Every claim links to a retrievable source |
| Supporting and contradicting evidence are first-class | Both are stored and surfaced equally |
| Distinguish symptom, factor, trigger, root cause | Structured causal chain, not flat labels |
| Express uncertainty; abstain when insufficient | `unknown` is a valid, scored conclusion |
| Every agent/tool action auditable | Full investigation trace for replay |
| Read-only investigation precedes write-capable workflow | No production mutations in early phases |
| Remediation runs outside production | Sandbox execution with human approval gate |
| Modular monolith until scale justifies separation | Single deployable unit, clear internal boundaries |
| Add infrastructure only when requirement supports it | No Kafka, K8s, vector DB without measured need |
| Evaluate against stable benchmark before claiming improvement | Frozen scenarios, regression detection |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            NEXUS SYSTEM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────────────┐    │
│  │ Applications │    │  Git Provider    │    │  CI/CD Systems         │    │
│  │ (OpenTelemetry)│   │  (commits, PRs)  │    │  (deployments, builds) │    │
│  └──────┬───────┘    └────────┬─────────┘    └───────────┬────────────┘    │
│         │                     │                        │                   │
│         └─────────────────────┼────────────────────────┘                   │
│                               ▼                                            │
│                    ┌────────────────────────┐                              │
│                    │  Collection & Ingestion │  (PLANNED)                  │
│                    │  Validation, Normalize,  │                              │
│                    │  Enrich, Timestamp      │                              │
│                    └───────────┬─────────────┘                              │
│                                │                                           │
│                                ▼                                           │
│         ┌──────────────────────┼──────────────────────┐                   │
│         ▼                      ▼                      ▼                   │
│  ┌───────────────┐    ┌───────────────┐    ┌─────────────────┐           │
│  │ Telemetry     │    │ Application   │    │ Deterministic   │           │
│  │ Storage       │    │ State         │    │ Evidence Intel  │           │
│  │ (logs,metrics,│    │ (projects,    │    │ (correlation,   │           │
│  │  traces)      │    │  services,    │    │  deployment     │           │
│  │  (PLANNED)    │    │  incidents,   │    │  lookup, baselines)        │
│  └───────┬───────┘    │  hypotheses)  │    │  (PLANNED)      │           │
│          │            │  (PLANNED)    │    └────────┬────────┘           │
│          │            └───────┬───────┘             │                    │
│          │                    │                     │                    │
│          └────────────────────┼─────────────────────┘                    │
│                               ▼                                          │
│                    ┌────────────────────────┐                            │
│                    │  Incident Investigation │  (PLANNED)                │
│                    │  Evidence bundle,      │                            │
│                    │  Hypotheses, Tools,    │                            │
│                    │  Verification, Diagnosis│                           │
│                    └───────────┬────────────┘                            │
│                                │                                         │
│                                ▼                                         │
│                    ┌────────────────────────┐                            │
│                    │  Evaluation            │  (PLANNED)                │
│                    │  Frozen scenarios,     │                            │
│                    │  Repeatable runs,      │                            │
│                    │  Regression compare    │                            │
│                    └───────────┬────────────┘                            │
│                                │                                         │
│                                ▼                                         │
│                    ┌────────────────────────┐                            │
│                    │  Remediation (Future)  │  (PLANNED)                │
│                    │  Isolated workspace,   │                            │
│                    │  Tests/scans, Artifacts│                            │
│                    │  Human approval → PR   │                            │
│                    └────────────────────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

> **Legend:** All components marked **(PLANNED)** are not implemented in Phase 0.

## Implementation Status

| Component | Status |
|-----------|--------|
| Architecture documentation | ✅ IMPLEMENTED |
| Benchmark schemas (JSON Schema) | ✅ IMPLEMENTED |
| 22 incident scenario fixtures | ✅ IMPLEMENTED |
| Validation CLI (`nexus-benchmark`) | ✅ IMPLEMENTED (installed console script) |
| Agent-view / ground-truth separation | ✅ IMPLEMENTED (allowlisted projection + temporal cutoff, tested) |
| Verification-step execution policy | ✅ IMPLEMENTED (`read_only` / `staging_experiment` / `human_approval_required`, registered-tool allowlist) |
| Automated tests (pytest) | ✅ VERIFIED (383 local tests; dated local/hosted evidence in status report) |
| Linting/formatting (Ruff) | ✅ IMPLEMENTED |
| CI (GitHub Actions) | ✅ IMPLEMENTED (triggers on `master`) |
| Dependency lockfile | ✅ COMMITTED (`uv.lock`; strict runtime/dev/build installs and hash-checked wheel smoke) |
| Telemetry ingestion pipeline | ❌ PLANNED (Phase 1+) |
| AI investigation agent | ❌ PLANNED (Phase 4+) |
| UI / Dashboard | ❌ PLANNED (Phase 3+) |
| Database integrations | ❌ PLANNED (Phase 2+) |
| Remediation sandbox | ❌ PLANNED (Phase 7+) |
| GitHub App integration | ❌ PLANNED (Phase 8+) |

For the commands that were actually executed and their results, see
[Phase 0 Status](docs/development/phase-0-status.md).

**Readiness:** Phase 0 is the only implemented phase, and its correction is not
permission to start Phase 1. The [status report](docs/development/phase-0-status.md)
distinguishes PR #1's pre-merge exact-head sign-off (PR #1 is merged as of
2026-10-18) from the post-merge push run at the merge commit, and records the
reviewed INC-016/INC-019, leakage and lock corrections. No diagnosis-accuracy
result is claimed. Phase 1 requires a separate instruction and has not started.

## Quick Start

### Prerequisites

- Python 3.11+
- `uv` **0.13.0** on PATH, installed outside the project `.venv`
- Bash (Windows: WSL2)

### Installation

```bash
# Clone and enter repository
git clone https://github.com/gm-prog/NEXUS-.git
cd NEXUS-

# Enforce uv.lock, stage the locked build backend, then install editable
# without build isolation. See CONTRIBUTING.md for pinned uv setup.
./scripts/locked_sync.sh
source .venv/bin/activate
```

### Validate Benchmarks

```bash
# List all incident cases
nexus-benchmark list

# Validate all cases
nexus-benchmark validate

# Validate a specific case
nexus-benchmark validate --case INC-001
```

`validate` checks schema compliance (with `date-time`/`uuid` format checking
enabled), cross-file composition, the ambiguity-coverage ratio, the execution
metadata policy of every verification step, the temporal cutoff of every typed
investigation timestamp, and a tested allowlist excluding evaluator-only fields
(including `incident_window.end`). Future/malformed evidence is rejected, not
filtered. Schema-invalid cases have dependent checks explicitly marked NOT RUN.
This is fixture validation, not runtime authorization or AI diagnosis evaluation.

### Run Tests & Checks

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nexus_benchmarks

# Lint and format check
ruff check .
ruff format --check .

# Build a wheel, install it in a clean environment and run the CLI from a
# directory outside the checkout
./scripts/wheel_smoke_test.sh
```

### Command Contract

`nexus-benchmark` is installed as a real console script
(`nexus_benchmarks.cli:main`). The benchmark schemas and fixtures ship inside
the wheel, so all three commands work from any directory:

```bash
nexus-benchmark --help
nexus-benchmark list
nexus-benchmark validate
```

## Documentation

- [Architecture Overview](docs/architecture/system-architecture.md)
- [Design Principles](docs/architecture/principles.md)
- [Domain Model](docs/architecture/domain-model.md)
- [Evidence Model](docs/architecture/evidence-model.md)
- [Incident Lifecycle](docs/architecture/incident-lifecycle.md)
- [Data Flow](docs/architecture/data-flow.md)
- [Schema Strategy](docs/architecture/schema-strategy.md)
- [Threat Model](docs/security/threat-model.md)
- [Permission Model](docs/security/permission-model.md)
- [ADRs](docs/decisions/)
- [Roadmap](docs/development/roadmap.md)
- [Testing Strategy](docs/development/testing-strategy.md)
- [Benchmark Details](benchmarks/README.md)
- [Phase 0 Status](docs/development/phase-0-status.md)

## Non-Goals / Current Limitations

- `uv.lock` pins dependency versions and artifact hashes, not the OS image or
  Python patch release; this is not a byte-for-byte build or security guarantee
- The answer-text scan detects verbatim copies, not semantic/paraphrased leaks;
  two exact reviewed observation overlaps are documented in ADR-0014
- No telemetry collection, processing, or storage
- No AI model integration or agent framework; no benchmark diagnosis accuracy has
  been measured. Passing validation establishes fixture/schema hygiene only
- No UI, dashboard, or API server
- No database (PostgreSQL, Redis, ClickHouse, etc.)
- No message queue (Kafka, etc.)
- No embeddings, RAG, or knowledge graph
- No code patching, shell execution, or PR creation
- No Kubernetes, Terraform, or cloud deployment
- No claims about detection/root-cause accuracy without executed evaluation
- **Public product naming is unresolved** — "NEXUS" is a working codename with known market collision (incident.io's Nexus)

## License

MIT License — see [LICENSE](LICENSE).