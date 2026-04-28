# Security model and hardening

BitAgent's HTTP server has no opinion about authentication. It trusts whoever connects. Every security control in this document is either an env var that BitAgent does honour, or a network/proxy layer that you put in front of it.

This page is the operator's reference for how to deploy BitAgent without making yourself the next obvious target.

## Threat model

**In scope.** A self-hoster's deployment exposed via a single host with port `3333` reachable. The operator's IP visible on the public BitTorrent DHT. An open `/torznab/api` endpoint. Misconfigured Postgres password. Loss/leak of `TORZNAB_API_KEY` or `EVIDENCE_WEBHOOK_SECRET`.

**Out of scope.** Zero-day vulnerabilities in Postgres or the Go runtime. Supply-chain compromise of a base image. Kernel-level exploits or container escape. Compromise of upstream `*arr` services (BitAgent trusts whatever data they send).

The single load-bearing assumption is that the host running BitAgent is trusted. There is no internal mTLS between BitAgent and Postgres in the bundled stack.

## Network attack surface

The default `examples/docker-compose.public.yml` exposes port `3333` directly. All of these paths answer on it:

| Path | Auth (default) | Sensitive? |
|---|---|---|
| `/graphql` | none | Yes — full mutation surface |
| `/torznab/api` | none — gates on `TORZNAB_API_KEY` if set | Yes if `*arr` uses it |
| `/metrics` | none | Information disclosure (DB sizes, infohash counts) |
| `/import` | none | Yes — accepts NDJSON bulk-import |
| `/evidence/arr/<instance>` | gates on `X-Evidence-Token` matching `EVIDENCE_WEBHOOK_SECRET` | Yes |

**Do not expose port `3333` directly to the internet.** Always front it with a reverse proxy that adds auth.

## Authentication tiers

Three deployment shapes, in increasing order of exposure tolerance.

### Tier 1 — open (default)

Use only on a tailnet, ZeroTier, LAN, or container-network-only deployment. BitAgent accepts all requests. Network isolation is the entire control.

### Tier 2 — API key

- `TORZNAB_API_KEY` — gates `/torznab/api` (constant-time compare; timing-safe). Required when the `*arr` clients are on a different host or network than BitAgent.
- `EVIDENCE_WEBHOOK_SECRET` — gates `/evidence/arr/*` (compared against the `X-Evidence-Token` header on each webhook).

Generate keys with at least 256 bits of entropy:

```bash
openssl rand -hex 32
```text
Both keys are read at process startup. Rotation requires a process restart; see [Key rotation](#key-rotation) below.

### Tier 3 — reverse-proxy auth

For public-internet exposure. Use Caddy, Traefik, NPM, Authelia, or Cloudflare Access in front. The proxy does the auth, BitAgent trusts whatever traffic the proxy forwards.

Defense-in-depth: keep `TORZNAB_API_KEY` and `EVIDENCE_WEBHOOK_SECRET` set even when the proxy is doing the heavy lifting. A misconfigured proxy that silently lets traffic through still hits a 401 from BitAgent if the keys aren't there.

## DHT and IP exposure

BitAgent participates in the public BitTorrent DHT. There is no setting that disables this; it is what BitAgent fundamentally *does*. Consequence:

- Your IP is published to the global DHT routing table.
- During BEP-9 metainfo fetch, your IP appears in swarm peer lists.
- Peer-tracking services (e.g. "I know what you download") observe and record this.

BitAgent does *not* download torrent payloads — only metadata. The exposure window is bounded to the metadata phase. Still, for any deployment where IP exposure is a concern, the standard mitigation is:

- Run BitAgent behind a VPN tunnel (Gluetun is what the advanced stack uses).
- Use a VPN provider that supports port forwarding so DHT inbound traffic gets symmetric reach.

CSAM — the one category where post-fetch detection is too late — has its own pre-fetch double-hash defense. See [concepts/csam-defense.md](../concepts/csam-defense.md).

## CSAM defense

Briefly: a pre-fetch double-hashed bloom filter rejects known-CSAM infohashes *before* BitAgent ever opens a TCP connection to a peer. Defaults are safe (enabled, no feeds = NoOp). Layered architecture in [concepts/csam-defense.md](../concepts/csam-defense.md).

The post-classify regex (`keywords.banned`) provides a second layer for any infohash that slips past the pre-fetch filter. The self-export pipeline contributes back to community feeds, so each operator's observations harden the pre-fetch defense for the next operator.

## Database hardening

`POSTGRES_PASSWORD` is the only thing standing between an attacker on the host and your indexed corpus.

- Generate it with `openssl rand -hex 32`. Avoid passwords with shell-special characters.
- Never commit `.env` files to git. Add them to `.gitignore` from day one.
- Rotate immediately on any suspected leak.
- The default Postgres user is `bitmagnet` with full database privileges on the `bitmagnet` database. Bind to localhost or the docker compose internal network — do not expose `5432` externally.

For the bundled compose stack, Postgres is on the internal docker network only and is not reachable from the host's external interfaces.

## Reverse-proxy recipe

Caddy template for a public deployment with mixed auth:

```caddyfile
bitagent.example.com {
  # /torznab/api: gated on TORZNAB_API_KEY only — *arr clients hit it
  reverse_proxy /torznab/* bitagent:3333

  # /evidence/arr/*: gated on EVIDENCE_WEBHOOK_SECRET only
  reverse_proxy /evidence/* bitagent:3333

  # Everything else: forward_auth or basic_auth
  @internal {
    not path /torznab/* /evidence/*
  }
  basic_auth @internal {
    admin <bcrypt_hash>
  }
  reverse_proxy @internal bitagent:3333
}
```text
Generate the bcrypt hash with `caddy hash-password`. Use a 12+ character random password.

## Webhook auth (`X-Evidence-Token`)

Every `*arr` Connect → Webhook entry needs the `X-Evidence-Token` Custom Header set to the same value as `EVIDENCE_WEBHOOK_SECRET`. The webhook URL pattern is:

```text
http://<bitagent-host>:3333/evidence/arr/<instance-label>
```text
`<instance-label>` is operator-chosen — it ends up in the `label_evidence.source_instance` column for traceability (e.g. `sonarr-main`, `sonarr-anime`, `radarr-4k`).

Mismatched or missing token → request rejected, no row written, increments `bitagent_evidence_events_rejected_total`.

## Key rotation

### `TORZNAB_API_KEY`

1. Generate the new key: `openssl rand -hex 32`.
2. Update `TORZNAB_API_KEY` in the BitAgent env (`.env` file or secrets store), restart the BitAgent container.
3. Update each `*arr` indexer's API Key field to the new value.
4. Test each indexer connection.
5. The old key is now dead — no need to retire it explicitly.

### `EVIDENCE_WEBHOOK_SECRET`

Mirroring matters here — webhook signal is dropped during the gap.

1. Generate the new value.
2. Update each `*arr` Connect → Webhook entry's `X-Evidence-Token` to the new value first.
3. Update `EVIDENCE_WEBHOOK_SECRET` in BitAgent's env and restart.
4. The webhook ingestor will reject any in-flight `*arr` retries that still carry the old token — `*arr` will retry with the new token, and the data eventually lands.

For zero gap, deploy a forward-compatible BitAgent build that accepts both old and new tokens for the rotation window — not currently shipped; ask in Discussions if you need it.

## Logging and audit

`LOG_LEVEL=info` is the production default and captures auth failures, webhook rejection, and CSAM-defense activity. `LOG_LEVEL=debug` captures every Torznab query — useful for incident response, very loud.

All logs go to stdout. No telemetry, no upstream phone-home — except `CSAM_BLOCKLIST_EXPORT_UPSTREAM_URL` if you opt in.

## Container hardening

The bundled Dockerfile already does most of what you'd want:

- Runs as a non-root user. Do not override `USER` in your compose.
- The image is small (Alpine base, multi-stage build).
- No build tooling in the runtime layer.

If you want to harden further:

- `read_only: true` in compose. BitAgent doesn't need a writable rootfs at runtime.
- `cap_drop: [ALL]`. The only capability that might be needed is `CAP_NET_BIND_SERVICE`, and only if you've set `BITAGENT_PEER_PORT` below `1024`. Keep it ≥ `1024` and you can drop everything.
- `tmpfs` on `/tmp` if you need any writes at all.
- Mount Postgres data on a dedicated volume; never bind-mount the database directory from the host filesystem (file-permission drift).

## Vulnerability reporting

Report security issues via the repo's [SECURITY.md](https://github.com/gekleos/bitagent/blob/main/SECURITY.md) — don't open a public issue for unpatched vulnerabilities. The maintainer triages on a best-effort basis; there is no formal SLA or bounty.

## See also

- [Configuration](../configuration.md)
- [Deployment](../deployment.md)
- [Concepts: CSAM defense](../concepts/csam-defense.md)
- [Integrations: Private tracker mode](../integrations/private-tracker-mode.md)
