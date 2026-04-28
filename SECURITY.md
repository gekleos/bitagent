# Security Policy

BitAgent is a self-hosted BitTorrent DHT crawler and Torznab provider. We treat security findings as first-class.

## Supported versions

| Version stream | Supported? |
| --- | --- |
| `main` (rolling) | yes |
| Latest tagged release | yes — patch releases as needed |
| Older tagged releases | best effort, no SLA |

Patches land on `main` first, then back-port to the latest tag.

## Reporting a vulnerability

**Do not file a public issue or discussion thread for a security finding.**

Use [GitHub Security Advisories](https://github.com/gekleos/bitagent/security/advisories/new) to open a private report. Include:

- Affected commit SHA or release tag
- Steps to reproduce (curl invocations, payloads, deployment shape)
- Impact assessment (auth bypass, RCE, data exfiltration, DoS, etc.)
- Optional: a suggested fix

We aim to acknowledge within **48 hours** and triage within **7 days**. A coordinated disclosure window of **90 days** is standard; extensions are negotiable for complex fixes or upstream coordination.

## Scope

**In scope (this repository — `gekleos/bitagent`):**

- The operator dashboard under `ui/` (FastAPI + Jinja2 + static assets), including its auth surface and TMDB integration
- The example deployments under `examples/` (`compose.public.yml`, `compose.authelia.yml`, `compose.tailnet.yml`, `prowlarr/`)
- The repair/sanitize tooling under `scripts/`
- The published Docker image `docker.io/gekleos/bitagent-ui` (and any future `gekleos/*` images we publish)
- Documented integration paths surfaced by the dashboard (Sonarr/Radarr evidence webhook, Torznab, GraphQL admin)

**Out of scope:**

- Issues in upstream `bitmagnet-io/bitmagnet` that we have not modified — please report those upstream.
- BitTorrent BEP protocol weaknesses — those are protocol-layer and belong with the BEP authors.
- Issues in third-party trackers, indexers, or `*arr` projects.
- Findings that require physical access, OS-level compromise, or already having admin credentials.

## Bug bounty

There is no monetary bounty. With the reporter's permission, valid findings are credited in the Hall of Fame below once a fix has shipped.

## Threat model

**Untrusted DHT input.** The DHT crawler ingests attacker-controlled input at high volume (torrent names, metainfo strings, peer announcements). All parsing paths must be defensive: no panics on malformed input, hard-cap input lengths, regex engines bounded by RE2 or equivalent, classifier rules sandboxed.

**Public-internet Torznab.** When `TORZNAB_API_KEY` is empty, the Torznab endpoint is open. Public-internet deployments must always set the key. The dashboard's `DASHBOARD_API_KEY` is a separate secret that gates the operator UI; never reuse it for the Torznab endpoint.

**GraphQL admin surface.** The GraphQL endpoint is privileged. It expects to live behind a trusted reverse proxy or tailnet; the public-release plan layers an API-key gate on the dashboard side. Direct exposure without the gate is unsupported.

**Postgres data layer.** A SQL-injection or unsafe migration would be high severity; only parameterised paths are accepted in the data layer. The classifier writes through the same parameterised gateway.

## Hall of fame

_(Empty — be the first.)_
