# Phase 1A Status — Local Deterministic Demo

**Status: PARTIAL — hosted exact-head validation is pending, and local WSL verification has not run.** This report does not declare Phase 1A complete or merge-ready. The topology remains four application services (`api-gateway`, `checkout-service`, `order-service`, `payment-service`), the separate `payco-mock`, and one local Collector. Only INC-001, INC-005, and INC-006 are implemented. Phase 1B remains planned.

## Scope and fixture constraints

- Root Phase 0 project and root `uv.lock` are unchanged. Demo dependencies remain isolated in `apps/phase1a/pyproject.toml` and `apps/phase1a/uv.lock`. ADR-0015 remains unchanged; ADR-0016 remains Proposed.
- Only the gateway publishes `127.0.0.1:8000`; backend and mock ports are private. App containers run non-root, read-only with `/tmp` tmpfs and `no-new-privileges`. Collector output is ephemeral debug/stdout; there is no persistent volume or remote exporter.
- INC-001 preserves the initial-symptom two-minute versus evidence five-minute discrepancy; the proposed metric uses five minutes only. The controlled Python `ValueError` is not represented as a Java `NullPointerException` or an invented source line. Change/commit references are synthetic, not provider lookups.
- INC-005 calls `payco-mock` directly from checkout; payment-service is not in this causal path. The 30,000 ms value is virtual against the 10,000 ms timeout, with no sleep. The 99.5% → 12% synthetic percentage and per-call timeout evidence remain distinct; no denominator or local change is invented.
- INC-006 retains the 10,000 → 100 requests/minute configuration change and the explicit 95×503 / 3×429 / 2×forwarded harness assumption. The model is not fixture-provided truth. The synthetic model and actual HTTP decisions now use separate instruments and provenance. 429 is not 5xx. Synthetic config time `2024-01-20T07:59:00Z` remains distinct from fixture commit evidence `2024-01-19T15:00:00Z`; fixture trace evidence is absent and app traces are supplemental.

## Remediation implementation and regression coverage

- INC-006 model counts use `nexus.demo.synthetic.gateway.modeled_request_decisions` (`{request}`, `synthetic_harness_assumption`); actual HTTP decisions use `nexus.gateway.http.rate_limit.decisions` (`{request}`, `observed_http_request`) only on gateway proxy traffic. The simulation response labels all modeled values and explicitly says it records no real requests.
- Status classification is explicit: `429` → `http_429`, 500–599 → `http_5xx`, otherwise → `forwarded`. In-memory metric-reader tests verify values, units, labels, scenario-only vs HTTP-only increments, and separation of the old mixed-counter failure mode.
- INC-005 virtual latency uses `nexus.demo.synthetic.logical_latency` (`ms`), emitted only for a PayCo mock 504; success-rate values remain in the `%` histogram. `nexus.payco.logical_timeouts` increments once per observed 504 and not for success. Tests cover a healthy call and repeated timed-out calls without wall-clock delay.
- Trigger/reset control calls now inspect all downstream responses. Rejected or unreachable services return HTTP 502 with completed/failed service names and partial status; response bodies, request data and tokens are not returned. Success response contracts are covered.
- Logs use `BatchLogRecordProcessor`; scenario-critical logs are explicitly force-flushed through `asyncio.to_thread` before response (2s bound, off the event loop). Shutdown force-flushes and closes all providers, reports failures rather than silently ignoring them, and is idempotent. An in-memory exporter regression test verifies explicit flush, structured attributes, service identity, and shutdown.
- Collector proof captures a UTC cutoff before smoke traffic, calls Compose logs with `--since` and timestamps, parses `service.name` only within signal resource blocks, and waits boundedly for an explicit service-by-signal matrix. Traces and metrics require all five services; logs require `api-gateway`, `checkout-service`, `payment-service`, and `payco-mock`. `order-service` emits no scenario business log by design. Tests reject stale-only output, absent log/service pairs, wrong-signal identities, and broad marker/name matches without resource associations.

## Image pin review

- Python is pinned to `python:3.12.15-slim-bookworm`. CPython’s official `v3.12.15` tag was dated 2026-09-30. The official Docker Library `python` metadata at commit [`2fde087`](https://github.com/docker-library/official-images/commit/2fde087b614c3bfc43eb55eb41133371fcb6260d) records `3.12.15-slim-bookworm` and lists multiple architectures. Compared with the previous 3.12.12 base, upstream CPython changes include security fixes such as CVE-2026-2297, CVE-2026-3644, CVE-2026-4224 and CVE-2026-12003 (see [the official tag comparison](https://github.com/python/cpython/compare/v3.12.12...v3.12.15)). The exact patch tag is retained rather than floating `3.12`/`latest`.
- Collector is pinned to `otel/opentelemetry-collector-contrib:0.162.0`, an official release published 2026-09-29 ([core release notes](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.162.0), [contrib release notes](https://github.com/open-telemetry/opentelemetry-collector-contrib/releases/tag/v0.162.0)). An attempted newer `0.163.0` exact pin was rejected by Docker Hub as `not found` in remediation CI run 45062447730, so it is not retained. Reviewed `0.162.0` breaking changes concern unrelated processor/scraper/helper components; enabled OTLP receiver, batch processor, debug exporter and health-check extension configuration is unchanged. The isolated OTLP SDK/exporter packages remain pinned at 1.38.0; no dependency lock changes were needed. Compose pulled and started `0.162.0` in runs 45062565084 and 45062860923, with traces/metrics received, but neither run completed the log receipt smoke; full exact-head runtime smoke remains pending.
- Exact version tags are used, not floating tags. Registry manifest digests were not independently available through the allowed GitHub metadata access, and no image scanner or Docker daemon is available in Arena. GitHub repository advisory endpoints returned 404; this is **not** a claim that either image has no CVEs. The required real image pull/build/start and Compose smoke are delegated to the new hosted Compose CI run; its result is recorded below after completion.

## Validation evidence and provenance

These categories prove different things: unit/contract tests prove local code behavior, not real multi-container behavior; hosted Compose CI proves runtime behavior on its runner, not on Samrat’s machine; only the OpenCode WSL run establishes behavior in the user’s local Docker environment.

| Check | Result | Evidence / limit |
|---|---|---|
| Root lock and dependency sync | PASS | `uv lock --check`; `./scripts/locked_sync.sh` with pinned `uv==0.13.0`. Root `uv.lock` unchanged. |
| Root formatting and lint | PASS | `.venv/bin/ruff format --check .`; `.venv/bin/ruff check .`. |
| Root tests | PASS | `.venv/bin/python -m pytest -v`: 390 passed, including Collector transcript/parser regressions. |
| Phase 0 fixture validation | PASS | `.venv/bin/nexus-benchmark validate`: all 22 cases valid; composition, execution-policy, temporal-integrity and agent-view checks passed. |
| Root wheel smoke | PASS | `./scripts/wheel_smoke_test.sh`: packaged all 22 fixture bytes and installed CLI help/list/validate succeeded outside the checkout. |
| Isolated app lock/sync/tests | PASS | `uv lock --project apps/phase1a --check`; `uv sync --project apps/phase1a --locked --group dev`; app tests: 8 passed on Python 3.11.2. |
| Five-process HTTP smoke without Docker/OTLP | PASS, limited | Ran all three scenarios twice through five independent local service processes; all assertions passed and all service ports were closed after termination. This does not establish Compose or Collector receipt. |
| Docker/Compose in Arena | NOT RUN — unavailable | `docker` is not installed (`command not found`); `docker version`, `docker compose version`, `scripts/phase1a.sh validate`, and Arena-local `scripts/phase1a.sh smoke` cannot be run here. |
| WSL/Docker on Samrat’s machine | PENDING / NOT RUN | Must be performed by OpenCode in a clean worktree at the exact PR SHA; see handoff below. |

### CI run-to-commit record

Run IDs and full tested SHAs were checked directly against GitHub Actions metadata. Runs before remediation are baselines, not proof that remediation changes passed.

- **Pre-remediation:** [run 45059712352](https://github.com/gm-prog/NEXUS-/actions/runs/45059712352), tested only `f6234369b171be27d0f0d235e52b21b688b83d47`, conclusion **success** (Python 3.11, Python 3.12 including Compose smoke, and wheel smoke).
- **Exact starting-head baseline:** [run 45059855211](https://github.com/gm-prog/NEXUS-/actions/runs/45059855211), tested `6b4fe6ca9350ec7b683c3b033eb8688fe0c6e84d`, conclusion **success** (Python 3.11, Python 3.12 including Compose smoke, and wheel smoke). This was the remediation starting point, not a remediation run.
- **First remediation attempt:** [run 45062447730](https://github.com/gm-prog/NEXUS-/actions/runs/45062447730), tested only `28e2c3acb5b66fdcddde2b84ea14cc732e7c8193`, conclusion **failure**. Python 3.11 validation and wheel smoke passed; Python 3.12 tests/app validation passed, but Compose startup failed because Docker Hub returned `not found` for the newly selected `0.163.0` image. The Python 3.12 cleanup step ran successfully. The base was changed to exact tag `0.162.0`; that tag's runtime pull/build/smoke is still unverified.
- **Second remediation attempt:** [run 45062565084](https://github.com/gm-prog/NEXUS-/actions/runs/45062565084), tested only `de3f4856e802003aca236d1964429ed60d4c57be`, conclusion **failure**. Python 3.11 validation and wheel smoke passed; Python 3.12 tests/app checks and Compose validation passed, and the Compose smoke reached the current-run Collector receipt poll. Traces/metrics were associated, but all expected log-resource pairs were missing; the required cleanup step passed. This rules out the earlier `.163.0` pull failure but does not verify the telemetry smoke. The BatchLogRecordProcessor schedule/export bounds are now explicit and timeout diagnostics include parsed signal/resource counts.
- **Third remediation attempt:** [run 45062860923](https://github.com/gm-prog/NEXUS-/actions/runs/45062860923), tested only `c924bf3ae6ecfa0be1a509c2d205a04d94bdf005`, conclusion **failure**. Python 3.11 validation and wheel smoke passed; Python 3.12 tests/app checks and Compose validation passed, and cleanup passed. The Compose smoke still received no Collector log resource blocks (`logs=0`) while all five trace and metric resources were present. The latest change explicitly force-flushes the critical demo log events off the event loop before their HTTP response; an exact-head runtime rerun is pending.
- **Explicit-flush attempt:** [run 45063295769](https://github.com/gm-prog/NEXUS-/actions/runs/45063295769), tested only `85c4996dfefc25683de7ce7257a0da1a7aaf2ab9`, conclusion **failure**. Wheel smoke and Python 3.11 validation passed; Python 3.12 tests, app checks, and Compose validation passed; Compose telemetry smoke failed after 25s with traces=20, metrics=130, logs=0; cleanup passed. Critical business/control logs now call the SDK force-flush off the async event loop before responding, but this did not resolve the Compose symptom. The exporter wiring or runtime behavior still needs investigation; do not describe the log-export blocker as fixed.
- **Next exact-head run after further diagnosis:** PENDING. Record the full SHA, Actions run ID/link, conclusion, and individual job/step results only after the run finishes. Do not infer the tested SHA from PR head or commit message.

## OpenCode WSL verification handoff

**Run only after Arena pushes the remediation and records the new full PR head SHA in this file.** Use a clean worktree so local edits are preserved. Substitute the exact recorded SHA below; do not checkout a stale branch snapshot.

```bash
# From the existing repository, preserve local edits and create a separate worktree.
git status --short --branch
git fetch origin
git worktree add --detach ../NEXUS-phase1a-verify <EXACT_REMEDIATION_SHA>
cd ../NEXUS-phase1a-verify
git status --short --branch
git rev-parse HEAD
# Confirm HEAD equals the exact SHA recorded above and the worktree is clean.

docker version
docker compose version
scripts/phase1a.sh down
scripts/phase1a.sh validate
scripts/phase1a.sh smoke

docker compose -f apps/phase1a/compose.yaml --project-directory apps/phase1a ps --all
docker compose -f apps/phase1a/compose.yaml --project-directory apps/phase1a config --format json
# Inspect published ports: only api-gateway should publish 127.0.0.1:8000.
docker compose -f apps/phase1a/compose.yaml --project-directory apps/phase1a logs --no-color --timestamps otel-collector
scripts/phase1a.sh down
docker compose -f apps/phase1a/compose.yaml --project-directory apps/phase1a ps --all
```

Confirm all services became healthy; all scenario passes (three scenarios twice) succeeded; current-run trace/metric/log evidence matches the documented signal/service matrix; only gateway has the loopback host binding; and no project containers/network or generated telemetry remain after scoped `down`. Do not run global Docker prune or delete unrelated resources. Capture command output, report mismatches without local edits, and leave this status PENDING until the result is supplied.

## Remaining gates

Exact-head hosted CI, including the Compose build/start/health and telemetry smoke against the two reviewed image pins, must finish successfully. Independent review and local WSL/Docker verification remain pending. No declaration of Phase 1A completion or merge recommendation is made here. Phase 1B and all later services/scenarios remain out of scope.
