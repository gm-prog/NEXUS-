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

- Dependencies pinned in `pyproject.toml` / lockfile
- CI installs from trusted indexes only
- No arbitrary code execution from benchmark fixtures (they are data, not code)