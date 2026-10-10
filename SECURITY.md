# Security Policy

## Supported Versions

This project is in Phase 0 (pre-alpha). No security support is provided for any version. Security practices are documented for future phases.

## Reporting a Vulnerability

If you discover a security issue in this codebase (e.g., in the validation CLI, schema processing, or test infrastructure), please report it by opening a GitHub Security Advisory or emailing security@nexus.local.

Do not file public issues for security vulnerabilities.

## Threat Model & Permission Boundaries

See:
- [Threat Model](docs/security/threat-model.md)
- [Permission Model](docs/security/permission-model.md)

Key principles:

- All external data (logs, telemetry, code, runbooks, issues) is **untrusted**
- Model outputs are **not authorization** — enforcement happens at tool/policy boundary
- No production-mutating permissions in early phases
- Sandbox escape and network abuse are explicit threats for future remediation phase
- Benchmark answer leakage is a contamination risk

## Secrets Handling

- No real credentials, API keys, or tokens in this repository
- `.env` files are gitignored
- `.env.example` contains only placeholder values
- Future phases will use proper secret management (not implemented)

## Supply Chain

- **No lockfile is committed.** `pyproject.toml` declares *minimum* version
  bounds only (for example `jsonschema>=4.23.0`), so two installs a week apart
  can resolve different versions. This is a known gap, not a pinned supply
  chain.
- `rfc3339-validator` is a declared runtime dependency because `jsonschema`
  only enforces `format: date-time` when a `FormatChecker` backend is present.
- CI installs from PyPI with `pip` and does not use hash checking.
- No arbitrary code execution from benchmark fixtures (they are data, not code).
- Tracked follow-up: adopt a lockfile (uv or pip-compile) and install with
  `--require-hashes` or `uv sync --locked` before Phase 1. See
  [CONTRIBUTING.md](CONTRIBUTING.md).