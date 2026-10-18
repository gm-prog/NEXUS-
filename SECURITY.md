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

- `uv.lock` commits the complete runtime/dev/build closure with exact versions
  and SHA-256 artifact hashes. Library metadata retains minimum bounds; the
  repository's supported development/CI path is the strict locked setup.
- CI uses `uv` 0.13.0, a full-SHA setup action and embedded release checksums.
  Checkout and Python setup actions also use verified immutable full SHAs.
- `scripts/locked_sync.sh` checks manifest consistency and stages locked wheels
  before building this project **without isolation**. Build-system constraints
  must be mirrored in the dev extra, closing uv's build-only drift blind spot.
- Wheel smoke exports locked, hashed runtime requirements, requires matching
  hashes and binary wheels, then installs the local wheel `--no-deps --no-index`.
  No independent pip dependency resolution or unbounded tool upgrade bypasses
  the lock in CI/build/install validation.
- `rfc3339-validator` remains a declared runtime dependency because `jsonschema`
  only enforces `format: date-time` with its `FormatChecker` backend installed.
- No arbitrary code execution from benchmark fixtures: SQL and remediation
  descriptions are data, not executed operations or runtime authorization.
- Locked versions are not proof of vulnerability absence. OS images, Python
  patch releases and arbitrary downstream library-consumer installs are not
  pinned by this lock. Review updates with the commands in
  [CONTRIBUTING.md](CONTRIBUTING.md#deliberate-lock-updates).
