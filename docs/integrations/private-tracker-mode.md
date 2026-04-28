# Private Tracker Mode

## What "private tracker mode" means here

In the *arr ecosystem, the term "private tracker" does not refer to community structure or ratio enforcement; it simply denotes an indexer that requires authentication to access. BitAgent adopts this terminology to clarify its operational profile. When you enable API key gating via the `TORZNAB_API_KEY` (enforced by the BitAgent server's Torznab handler) and `DASHBOARD_API_KEY` (enforced by the BitAgent dashboard), BitAgent functions identically to any other private indexer from Prowlarr's perspective: it blocks unauthenticated requests, validates passkeys, and routes traffic only for authorized clients.

Structurally, however, BitAgent is a self-hosted, public-DHT metadata indexer. You are not joining a community; you *are* the tracker. Your "passkey" is the API key, and your only "members" are your own *arr stack. This mode borrows the authentication and routing conventions of traditional private trackers while remaining fundamentally a local search engine.

## Setup

Generate cryptographically secure, distinct keys for each service boundary:

```bash
openssl rand -hex 32 > .env-TORZNAB_API_KEY
openssl rand -hex 32 > .env-DASHBOARD_API_KEY
```

Export both values into your BitAgent environment. `TORZNAB_API_KEY` protects the Torznab XML endpoint for inbound indexer queries. `DASHBOARD_API_KEY` secures the web UI and administrative REST API. They must remain separate to maintain least-privilege boundaries.

Validate each gate independently before proceeding:

```bash

# Torznab endpoint verification

curl -H "Authorization: Bearer $(cat .env-TORZNAB_API_KEY)" \
  https://bitagent.example.com/torznab?t=caps

# Dashboard verification

curl "https://bitagent.example.com:8080/api/me?apikey=$(cat .env-DASHBOARD_API_KEY)"
```

Both should return `200 OK` with valid responses.

In Prowlarr, navigate to `Settings → Indexers → Add New Indexer`, select `Custom (Torznab)`, and populate the fields exactly as you would for any private-tracker endpoint:

- **URL:** `https://bitagent.example.com/torznab`
- **API Key:** the `TORZNAB_API_KEY` you generated
- **Enable Private:** checked (forces Prowlarr to skip public fallbacks)
- **Priority:** `10` or `1` depending on your search strategy
- **Search/Download Limits:** match your DHT throughput

Once saved, Prowlarr will automatically append the `apikey` query parameter to all downstream requests. When the bundled definition ships upstream (`Prowlarr/Indexers!XXXX`), this collapses to a one-click import.

## Why this matters

Exposing BitAgent to the public internet without authentication would hand your entire indexed state and query metadata to unknown actors. Private mode keeps search patterns, library synchronization state, and DHT harvest entirely internal to your *arr stack.

By enforcing API gating, you gain full compatibility with Prowlarr's private-indexer conventions: automatic rate-limiting, configurable retry budgets, and search-priority queuing all function as designed. The key is rotation-friendly; you can issue a Sonarr-style key rotation via `POST /api/settings/regenerate-api-key` without restarting the service or breaking active indexer health checks.

## Comparison to traditional private trackers

Traditional private trackers operate as invitation-only communities governed by ratio enforcement, upload curators, internal forums, and peer-review systems. BitAgent borrows only the authentication-gating pattern from that model. There is no member directory, no ratio tracking, and no community moderation. You are not seeding to a centralized swarm; you are harvesting a public DHT network.

Curation is handled automatically by your CEL classifier rather than uploader reputation. While traditional trackers rely on social capital and manual approval, BitAgent relies on local configuration and deterministic indexing rules.

## Operator checklist

- Generate `TORZNAB_API_KEY` and `DASHBOARD_API_KEY` using separate `openssl rand` commands.
- Inject both keys into your BitAgent container environments before first startup.
- Restrict network egress on BitAgent if you wish to limit public DHT participation.
- Place Caddy or Traefik in front to terminate TLS and handle upstream routing.
- Store both API values in your password manager; never commit them to version control.
- Set Prowlarr/Sonarr/Radarr indexer priority and search limits to match your bandwidth.
- Verify operation by querying `?t=search&q=test` and confirming a `200` with valid Torznab XML.
- Establish a 90-day key rotation cadence using the `/api/settings/regenerate-api-key` endpoint.
- Monitor `/api/audit` logs for any unauthorized configuration changes or key rotations.
- If exposing to the public internet, explicitly set `TRUST_NPM_HEADERS=false` after `DASHBOARD_API_KEY` is applied.
