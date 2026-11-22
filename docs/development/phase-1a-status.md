# Phase 1A Status — Local Deterministic Demo

**Status: PARTIAL — LOCAL VERIFICATION REQUIRED.** The isolated app, tests, Compose topology, Collector configuration, and documentation are implemented. Python tests and a manual five-process HTTP run passed in Arena. Docker and Docker Compose are absent in this sandbox, so the Compose topology, Collector startup/configuration, OTLP receipt, loopback port publication, and container cleanup were not run or verified here. Do not treat this as Phase 1A complete or merge-ready until the Compose/Collector checks below pass in CI and local WSL.

This is a factual implementation/verification report for the current revision. It intentionally does not contain a future commit SHA.

## Baseline and scope

- Repository: `gm-prog/NEXUS-`; default branch `master`.
- Fresh `git fetch origin master` observed live master unchanged at `8519af2d76ad3825011361310a4356c9d179141c` (the prompt's expected baseline). No open PRs were present at preflight.
- Arena's session branch is fixed as `arena/5b30c202-nexus`; it was fast-forwarded from `827b11739792698a2016b909080014d8420b3cff` to the verified master SHA before edits. No branch switch or newly named feature branch was used.
- The root Phase 0 project and `uv.lock` were not changed. App dependencies are isolated in `apps/phase1a/pyproject.toml` and `apps/phase1a/uv.lock`; resolution is bounded to artifacts uploaded before `2026-10-18T00:00:00Z`.
- Only INC-001, INC-005 and INC-006 are implemented. Benchmark fixtures, schemas, `TOOL_REGISTRY`, ADR-0001–ADR-0015, ADR-0004, and ADR-0006 are unchanged. ADR-0016 is a new **Proposed** architecture record.

## Implemented topology and scenario behavior

- Shared Python/FastAPI package launched as independent processes/containers for `api-gateway`, `checkout-service`, `order-service`, `payment-service`, and `payco-mock`; the mock is not an application service. Docker Compose publishes only gateway `127.0.0.1:8000`; backend and mock ports are private. All app endpoints have live/ready health routes and Compose health checks. The Collector image is explicitly version-pinned and configured for OTLP traces, metrics and logs with `debug` stdout exporter only.
- Gateway/checkout/payment paths use real HTTP requests and W3C `traceparent` propagation. JSON logs are correlated when a real exporter-enabled service process is running; bounded HTTP, payment, PayCo, rate-decision, and synthetic fixture measurements are defined. No request body, billing address, payment identifier, or secret is logged.
- INC-001: gateway → checkout → payment; controlled Python `ValueError` returns payment HTTP 500 when the scenario is triggered and billing address is absent. Metric sample is explicitly synthetic and uses the five-minute evidence window. The two-minute `initial_symptoms` wording discrepancy remains stated; no second measurement is invented. Deployment/commit evidence is a synthetic observation only.
- INC-005: checkout → payco-mock directly; payment-service is not called. Degraded mock returns a virtual 30,000 ms latency against the 10,000 ms timeout with no wall-clock sleep. The 99.5% → 12% success metric is synthetic; no unsupported denominator or local change record is added.
- INC-006: gateway config model changes from 10,000 to 100 requests/minute. A 100-unit sample represents 5,000 logical requests/minute at 50 requests/unit. The model's 95×503, 3×429 and 2 forwarded outcomes are labeled a deterministic implementation assumption, not fixture truth; 429 is separate from the 95% 5xx metric. Synthetic config time `2024-01-20T07:59:00Z` and fixture commit reference/time `stu901vwx234` / `2024-01-19T15:00:00Z` are separate observations. Generated traces are supplemental because the fixture has no trace evidence.

## Commands and observed results

| Check | Result | Evidence / limitation |
|---|---|---|
| Python / sandbox capability | PASS preflight | Python `3.11.2`; `uv` was initially not on PATH; Docker and Docker Compose commands returned `command not found`. No privileged install or remote Docker workaround attempted. |
| Root locked install | PASS on rerun | Installed pinned `uv==0.13.0` in a temporary tooling prefix outside the repo and ran `PATH=/tmp/nexus-uv-tooling/local/bin:$PATH ./scripts/locked_sync.sh`; no root lock changes. |
| Root Ruff formatting/lint | PASS | `./.venv/bin/ruff format --check .` and `./.venv/bin/ruff check .`. |
| Root test suite | PASS on rerun | `./.venv/bin/python -m pytest -v`: 383 passed. The initial attempt without `uv` on PATH had 377 passed and 6 setup errors in lock tests; after putting the pinned tooling binary on PATH, the full suite passed. |
| Phase 0 CLI/fixture validation | PASS | `.venv/bin/nexus-benchmark --help`, `list`, `validate`; all 22 cases valid, composition/policy/temporal/agent-view checks passed. |
| Root wheel smoke | PASS | `./scripts/wheel_smoke_test.sh`; locked root install, wheel/sdist build, all 22 packaged fixture bytes verified, installed CLI `help/list/validate` succeeded. |
| App lock and app tests | PASS | `uv lock --project apps/phase1a --check`, `uv sync --project apps/phase1a --locked --group dev`, `apps/phase1a/.venv/bin/python -m pytest apps/phase1a/tests -v`: 4 passed on Python 3.11.2. Python 3.12 was unavailable locally. |
| Independent-process HTTP scenario smoke | PASS (no Docker/Collector) | Started five independent Uvicorn service processes on loopback ports 8000 and 8101–8104, then ran `python scripts/phase1a_smoke.py --scenario all --repeat 2`: all three cases passed twice, including INC-005 direct-path and INC-006 status mix. All five processes were stopped; ports were confirmed closed. No OTLP endpoint was configured for this run. |
| YAML syntax parse | PASS, limited | PyYAML parsed Compose, Collector, and CI YAML. This is not equivalent to `docker compose config`. |
| Docker Compose config/startup and Collector validation | NOT RUN | Docker/Compose absent. |
| OTLP Collector receipt of traces, metrics and logs | NOT RUN | Requires Docker Compose; code/config alone is not telemetry receipt evidence. |
| Loopback publication/backend port audit in running Compose | NOT RUN | Statically configured only; verify with local Docker. |
| CI on exact PR head / required contexts | PASS on latest observed run; separate Collector receipt remains WSL follow-up | Run `45059712352` at head `f6234369b171be27d0f0d235e52b21b688b83d47`: Python 3.11 validation, Python 3.12 validation including Compose smoke, and wheel smoke all succeeded. The earlier runs found and fixed the image PATH issue and the missing OTLP log records; the latter now use a simple processor for immediate export. Compose smoke asserted actual Collector trace, metric, and log record output and all five service identities. Local Docker is unavailable, so independent WSL verification remains required. |

## Local WSL/OpenCode handoff (required before calling Phase 1A complete)

From a clean checkout of the PR head, first confirm status/branch/head and inspect the diff. With Python 3.11/3.12, `uv==0.13.0`, Docker Engine and Compose v2 installed, run:

```bash
./scripts/locked_sync.sh
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m pytest -v
.venv/bin/nexus-benchmark --help
.venv/bin/nexus-benchmark list
.venv/bin/nexus-benchmark validate
./scripts/wheel_smoke_test.sh
uv lock --project apps/phase1a --check
uv sync --project apps/phase1a --locked --group dev
apps/phase1a/.venv/bin/python -m pytest apps/phase1a/tests -v
scripts/phase1a.sh validate
scripts/phase1a.sh smoke
scripts/phase1a.sh logs
scripts/phase1a.sh down
```

Confirm the Compose smoke reports all five service identities and actual OTLP trace, metric, and log records from Collector stdout; check container health and that only the gateway publishes to loopback; confirm no containers, networks, or generated telemetry remain after `down`. Report any mismatch before merge. Phase 1B, storage selection, diagnosis scoring, production readiness and all other incident cases remain out of scope.
