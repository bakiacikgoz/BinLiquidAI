# Security Policy

## Reporting a Vulnerability

Do not open a public issue containing vulnerability details. Use GitHub Private
Vulnerability Reporting or a private Security Advisory when that feature is enabled.
Include the affected commit and component, realistic impact, reproduction steps,
redacted logs, and a suggested mitigation when known.

If private reporting is temporarily unavailable, a public issue may request a private
contact channel, but it must contain no vulnerability detail.

## Scope

Reports may cover authentication, identity and RBAC; policy or approval bypass; audit,
replay or evidence integrity; signing and key verification; provider governance and
redaction; tool-execution and computer-use boundaries; terminal, filesystem, browser
and network controls; and secret leakage through logs, support bundles, evidence or
provider envelopes.

## Security Model

ImperaOS uses fail-closed policy evaluation, an explicit approval lifecycle, signed
evidence, privacy-safe defaults, and qualification before support claims. Deployment
guidance is in [SECURITY_BASELINE.md](SECURITY_BASELINE.md). See also the
[security review packet](docs/AGENT_CONTROL_PLANE_SECURITY_REVIEW_PACKET.md) and
[product boundary](docs/AGENT_CONTROL_PLANE_PRODUCT_BOUNDARY.md).

## Supported Code

Security maintenance covers current `main` and the latest explicitly maintained
release line. Indefinite backports are not promised.

## Disclosure Process

Maintainers validate and assess reports, prepare and test a patch, and coordinate
disclosure when appropriate. The project offers no guaranteed response SLA or bug
bounty.

## Safe Research Expectations

Do not perform unauthorized third-party testing, social engineering, denial of
service, destructive testing, or testing that risks other people's data or systems.
