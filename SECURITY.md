# Security Policy

## Supported Versions

This project is in Phase 0 (pre-alpha). No security support is provided for any version. Security practices are documented for future phases.

## Reporting a Vulnerability

Use the repository's [GitHub Security Advisory workflow](https://github.com/gm-prog/NEXUS-/security/advisories/new)
for private vulnerability handling. **No verified public security email address
is configured**, so none is advertised here. Do not file public issues
containing vulnerability details.

**Reporting availability (checked 2026-10-10):** GitHub's
`GET /repos/gm-prog/NEXUS-/private-vulnerability-reporting` reports
`enabled: false`. Maintainers can draft advisories; the public researcher
reporting route is not enabled. Maintainers should enable private reporting or
publish a verified contact through a separately authorised settings decision.
No repository settings were changed in this correction.

## Threat Model & Permission Boundaries

See:
- [Threat Model](docs/security/threat-model.md)
- [Permission Model](docs/security/permission-model.md)

Key principles:

- All external data (logs, telemetry, code, runbooks, issues) is **untrusted**
- Model outputs are **not authorization** — enforcement happens at tool/policy boundary
- No production-mutating permissions in early phases
- Sandbox escape and network abuse are explicit threats for future remediation phase
- Benchmark answer/time leakage is a contamination risk; future evidence is rejected
- Fixture tool classification is metadata validation, **not runtime authorization**.
  Future executable tools must enforce capabilities and read-only credentials at
  their execution boundary (including restricting SQL, commands and tool arguments)

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
- A reviewed lockfile plus enforced locked/hashed installs is a
  **pre-Phase-1 prerequisite**, not a Phase 1 task that can be deferred until
  after implementation starts. Owner: NEXUS maintainers. Trigger: before any
  Phase 1 implementation begins. This correction does not adopt tooling or
  silently generate a lockfile. See [CONTRIBUTING.md](CONTRIBUTING.md#dependency-installation).
