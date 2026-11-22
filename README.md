# NEXUS — Foundation, Benchmark, and Phase 1A Demo

> **NEXUS turns software telemetry and engineering change history into a reproducible, evidence-backed investigation, then eventually helps engineers validate a proposed fix in an isolated environment.**

## Overview

NEXUS is an AI-native engineering investigation platform designed to correlate runtime telemetry, service dependencies, source-code changes, and deployment history to produce evidence-backed incident investigations.

**The implemented repository scope is Phase 0 plus the local Phase 1A deterministic demo.** Phase 0 provides the foundation, benchmark schemas, 22 incident fixtures, validation CLI, tests and CI. Phase 1A adds a separately locked, synthetic local demo for INC-001, INC-005 and INC-006; it is not telemetry ingestion or a production platform. Phase 1B and later work remain planned; no AI investigator, UI, database, durable telemetry store, or remediation system is implemented.

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
| Phase 1A local synthetic demo and non-durable OTLP proof sink | 🟡 IMPLEMENTED; Compose verification pending (see [Phase 1A app](apps/phase1a/README.md) and [status](docs/development/phase-1a-status.md)) |
| Operational telemetry ingestion pipeline | ❌ PLANNED (Phase 2+) |
| AI investigation agent | ❌ PLANNED (Phase 4+) |
| UI / Dashboard | ❌ PLANNED (Phase 3+) |
| Database integrations | ❌ PLANNED (Phase 2+) |
| Remediation sandbox | ❌ PLANNED (Phase 7+) |
| GitHub App integration | ❌ PLANNED (Phase 8+) |

For the commands that were actually executed and their results, see
[Phase 0 Status](docs/development/phase-0-status.md).

**Readiness:** Phase 0 remains the validated benchmark foundation. Phase 1A is a local deterministic demo, not the operational telemetry ingestion platform; Phase 1B and later phases remain planned. The historical [Phase 0 status report](docs/development/phase-0-status.md) remains unchanged. No diagnosis-accuracy result or production readiness is claimed. See the [Phase 1A status report](docs/development/phase-1a-status.md) for checks actually run and outstanding local Docker/Compose verification.

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

### Phase 1A Local Demo

The separate synthetic demo project and Compose topology are documented in [apps/phase1a](apps/phase1a/README.md). With Docker Compose installed, use:

```bash
scripts/phase1a.sh validate
scripts/phase1a.sh up
scripts/phase1a.sh run all --repeat 2
scripts/phase1a.sh logs
scripts/phase1a.sh down
```

This local demo covers only INC-001, INC-005 and INC-006 and exports ephemeral OTLP proof to local Collector stdout. It does not change the Phase 0 benchmark CLI contract. See [Phase 1A Status](docs/development/phase-1a-status.md) for the exact verification state.

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
- [Phase 1A Demo](apps/phase1a/README.md)
- [Phase 1A Status](docs/development/phase-1a-status.md)

## Non-Goals / Current Limitations

- `uv.lock` pins dependency versions and artifact hashes, not the OS image or
  Python patch release; this is not a byte-for-byte build or security guarantee
- The answer-text scan detects verbatim copies, not semantic/paraphrased leaks;
  two exact reviewed observation overlaps are documented in ADR-0014
- No operational or durable telemetry ingestion/storage; Phase 1A only has an
  ephemeral local Collector proof sink
- No AI model integration or agent framework; no benchmark diagnosis accuracy has
  been measured. Passing validation establishes fixture/schema hygiene only
- No UI or dashboard; Phase 1A's HTTP routes are synthetic demo service APIs only
- No database (PostgreSQL, Redis, ClickHouse, etc.)
- No message queue (Kafka, etc.)
- No embeddings, RAG, or knowledge graph
- No code patching, shell execution, or PR creation
- No Kubernetes, Terraform, or cloud deployment
- No claims about detection/root-cause accuracy without executed evaluation
- **Public product naming is unresolved** — "NEXUS" is a working codename with known market collision (incident.io's Nexus)

## License

MIT License — see [LICENSE](LICENSE).