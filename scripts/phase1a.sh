#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f apps/phase1a/compose.yaml --project-directory apps/phase1a)

usage() {
    cat <<'EOF'
Usage: scripts/phase1a.sh COMMAND [ARG]
  validate              Validate the Compose file
  up                    Build and start the complete local topology, wait for health
  status                Show service health/status
  run INC-001|INC-005|INC-006|all [--repeat N]
  reset                 Clear demo fault state
  logs                  Follow OpenTelemetry Collector stdout proof
  smoke                 Run all scenarios twice and assert Collector signals
  down                  Stop and remove the stack
EOF
}

command="${1:-help}"
case "$command" in
    validate)
        docker compose -f apps/phase1a/compose.yaml --project-directory apps/phase1a config --quiet
        ;;
    up)
        "${COMPOSE[@]}" up --build --detach --wait --wait-timeout 180
        ;;
    status)
        "${COMPOSE[@]}" ps --all
        ;;
    run)
        shift
        scenario="${1:-all}"
        if (($# > 0)); then
            shift
        fi
        python3 scripts/phase1a_smoke.py --scenario "$scenario" "$@"
        ;;
    reset)
        python3 - <<'PY'
import json
import urllib.request
request = urllib.request.Request(
    "http://127.0.0.1:8000/__demo__/reset",
    data=b"{}",
    headers={"content-type": "application/json", "authorization": "Bearer local-demo-only"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=3) as response:
    print(json.dumps(json.load(response), sort_keys=True))
PY
        ;;
    logs)
        "${COMPOSE[@]}" logs --follow --no-color otel-collector
        ;;
    smoke)
        if ! output=$("${COMPOSE[@]}" up --build --detach --wait --wait-timeout 180 2>&1); then
            printf '%s\n' "$output" >&2
            summary=$(printf '%s\n' "$output" | tail -n 8 | tr '\n' ';')
            printf '::error title=Phase 1A Compose startup failed::%s\n' "$summary" >&2
            "${COMPOSE[@]}" ps --all >&2 || true
            "${COMPOSE[@]}" logs --no-color >&2 || true
            exit 1
        fi
        printf '%s\n' "$output"
        if ! python3 scripts/phase1a_smoke.py --scenario all --repeat 2 --verify-telemetry; then
            printf '::error title=Phase 1A smoke failed::Check the smoke failure annotation and following Compose logs.\n' >&2
            "${COMPOSE[@]}" ps --all >&2 || true
            "${COMPOSE[@]}" logs --no-color >&2 || true
            exit 1
        fi
        ;;
    down)
        "${COMPOSE[@]}" down --remove-orphans --volumes
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
