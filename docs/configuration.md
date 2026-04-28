# Configuration

BitAgent is configured entirely through environment variables — no config file is required for any deployment shape. The runtime resolves env vars at startup, applies defaults, and keeps everything in a single resolved-config tree that you can introspect with `bitagent config show`.

This page is the authoritative list. If a variable is not on this page, it does not exist.

For first-time setup see [Quickstart](quickstart.md). For production layouts see [Deployment](deployment.md). For the security implications of each auth knob see [operations/security.md](operations/security.md).

## Required

The single hard requirement is the database password. The container will exit on startup if it is empty.

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_PASSWORD` | *(required)* | Postgres credential. Pick something long and random — this is the only thing standing between an attacker on the host and your indexed corpus. |

## Networking

Two ports and a Postgres connection. Defaults work for the bundled `examples/docker-compose.public.yml` stack; override only if you have a port conflict or external Postgres.

| Variable | Default | Purpose |
|---|---|---|
| `BITAGENT_HTTP_PORT` | `3333` | HTTP API port. Hosts `/graphql`, `/torznab/api`, `/metrics`, `/import`, `/evidence/arr/*`. |
| `BITAGENT_PEER_PORT` | `3334` | BitTorrent peer protocol port. Outbound-dominant; opening it inbound increases throughput but is not required. |
| `POSTGRES_HOST` | `postgres` | Hostname or IP. Defaults to the compose service name in the bundled stack. |
| `POSTGRES_PORT` | `5432` | Postgres port. |
| `POSTGRES_NAME` | `bitmagnet` | Database name. The legacy schema name is preserved for compatibility with deployments that pre-date the rebrand; do not rename without a planned migration. |
| `POSTGRES_USER` | `bitmagnet` | Postgres user. Same compat reasoning as `POSTGRES_NAME`. |

## Authentication

BitAgent's HTTP server has no opinions about auth — it trusts whoever connects. Two env vars gate the two surfaces that face external clients.

| Variable | Default | Purpose |
|---|---|---|
| `TORZNAB_API_KEY` | *(none)* | When set, every `/torznab/api` request must include `apikey=<value>`. Empty leaves `/torznab` open — fine on a tailnet or behind a reverse proxy with its own auth, **not fine on the open internet.** Constant-time compare. |
| `EVIDENCE_WEBHOOK_SECRET` | *(none)* | Shared secret for the `*arr` webhook ingester. Mirror this value as the `X-Evidence-Token` Custom Header on every Sonarr/Radarr/Lidarr/Readarr Connect → Webhook configuration. Operator-internal stack only. |

## Classifier

The classifier runs locally with no external dependencies. TMDB enrichment is optional and improves movie/TV title resolution.

| Variable | Default | Purpose |
|---|---|---|
| `TMDB_API_KEY` | *(none)* | Free TMDB v3 API key. Enriches movie + TV records with title, release year, and episode metadata. Empty disables the TMDB stage; the rest of the classifier still works. Get a key at <https://www.themoviedb.org/settings/api>. |

## Crawler

A single multiplicative knob covers DHT worker concurrency. Higher values mean more peers, more memory, more CPU.

| Variable | Default | Purpose |
|---|---|---|
| `DHT_SCALING_FACTOR` | `1` | Multiplier applied to internal DHT worker counts. `1` is safe on a 4 GB host. `4`–`10` is appropriate on a beefier box; anything higher should be informed by `bitagent_dht_*` Prometheus signal. |
| `BITMAGNET_DHT_CRAWLER_SCALING_FACTOR` | inherits | The internal config path that `DHT_SCALING_FACTOR` resolves into. The bundled compose file maps the shorter name to this one — you do not normally need to set it directly. |

## Logging

| Variable | Default | Purpose |
|---|---|---|
| `LOG_LEVEL` | `info` | One of `debug`, `info`, `warn`, `error`. `info` is fine for steady-state; `debug` is loud and only useful while reproducing a specific issue. |

## CSAM defense

A pre-fetch double-hashed blocklist filters infohashes before BitAgent ever does a BEP-9 metadata fetch — closing the swarm-touching exposure window for the one category of content where post-fetch classification is too late. Defaults are safe: enabled with no feeds is a NoOp until you opt in to a feed you trust. Full architecture is in [concepts/csam-defense.md](concepts/csam-defense.md).

| Variable | Default | Purpose |
|---|---|---|
| `CSAM_BLOCKLIST_ENABLED` | `true` | Master toggle. Leaving it on with no feeds set has zero runtime cost. |
| `CSAM_BLOCKLIST_FEED_URLS` | *(none)* | Comma-separated list of community blocklist feed URLs. Each feed is fetched, parsed (one double-hash per line), and merged into a bloom filter. Empty = NoOp. |
| `CSAM_BLOCKLIST_EXPORT_ENABLED` | `true` | When the post-fetch classifier flags a CSAM-banned title, append the double-hashed infohash to a local JSONL log. On by default; the file never leaves the host unless `EXPORT_UPSTREAM_URL` is also set. |
| `CSAM_BLOCKLIST_EXPORT_UPSTREAM_URL` | *(none)* | Optional outbound endpoint for community contribution. POSTs each new double-hash observation. Off by default — opt in only if you have an endpoint you trust. |

## Content filter

Drops torrents whose title is non-English / non-Latin-script / has blocked extensions / matches NSFW keywords. **Two-stage opt-in** so you can quantify the impact before turning it on.

| Variable | Default | Purpose |
|---|---|---|
| `CONTENT_FILTER_ENABLED` | `false` | Stage 1: shadow mode. Filter rules run, counterfactual metrics are emitted, but no torrent is actually dropped. |
| `CONTENT_FILTER_ENFORCE` | `false` | Stage 2: enforcement. Drops actually take effect. Requires `CONTENT_FILTER_ENABLED=true`. |

The recommended workflow is to set `ENABLED=true` for at least a week, watch `bitagent_contentfilter_*` metrics, then flip `ENFORCE=true` once the drop pattern looks reasonable.

## Retention

Periodic deletion of torrents that haven't been seen in DHT announcements for a long time. Same two-stage opt-in pattern as the content filter.

| Variable | Default | Purpose |
|---|---|---|
| `RETENTION_ENABLED` | `false` | Stage 1: dry run. The `would_purge` counter increments for each torrent that *would* be deleted. Nothing actually deletes. |
| `RETENTION_ENABLE_PURGE` | `false` | Stage 2: real delete. Requires `RETENTION_ENABLED=true`. |

The default predicate is conservative: no canonical label, no evidence record, age > 60 days, `updated_at` older than 180 days, and every torrent source reports `seeders=0`. Validate the dry-run trend before flipping `ENABLE_PURGE`.

## Evidence-source ingestors (advanced)

These variables configure pollers for downstream `*arr` apps and qBittorrent. They are present in the advanced `deploy/docker-compose.yml`, **not** in `examples/docker-compose.public.yml`. Empty values disable the corresponding source without error — the worker logs `no X instances configured` and idles.

| Variable | Default | Purpose |
|---|---|---|
| `BITAGENT_IMAGE_TAG` | `latest` | Container image tag. |
| `SONARR_URL` / `SONARR_API_KEY` | *(none)* | Sonarr base URL + API key. |
| `RADARR_URL` / `RADARR_API_KEY` | *(none)* | Radarr base URL + API key. |
| `READARR_URL` / `READARR_API_KEY` | *(none)* | Readarr base URL + API key. |
| `LIDARR_URL` / `LIDARR_API_KEY` | *(none)* | Lidarr base URL + API key. |
| `QB_INSTANCE_URL` | *(none)* | qBittorrent WebUI URL. |
| `QB_INSTANCE_USERNAME` | *(none)* | qBittorrent WebUI username. |
| `QB_INSTANCE_PASSWORD` | *(none)* | qBittorrent WebUI password. |

## VPN integration (advanced)

The advanced stack runs BitAgent behind Gluetun for VPN-egressed DHT traffic. Same scope note as evidence-source ingestors — these are not present in the public quickstart compose. See `deploy/README.md` for full provider notes.

| Variable | Default | Purpose |
|---|---|---|
| `VPN_SERVICE_PROVIDER` | *(required for Gluetun)* | e.g. `mullvad`, `nordvpn`, `protonvpn`, `airvpn`. |
| `VPN_TYPE` | `wireguard` | `wireguard` or `openvpn`. |
| `WIREGUARD_PRIVATE_KEY` | *(required for wg)* | Gluetun WireGuard private key. |
| `WIREGUARD_ADDRESSES` | *(required for wg)* | Gluetun WireGuard address (comma-separated). |
| `VPN_SERVER_COUNTRIES` | `United States` | Egress country selection. |

## Live config inspection

Run `bitagent config show` against your running container to dump every config path, type, current value, default, and the source resolver that produced it (env var, default, file, etc.). This is the canonical way to verify a configuration override took effect:

```bash
docker exec bitagent bitagent config show
```

Output is a wide table; pipe to `less -S` if your terminal is narrow. The `From` column tells you exactly where a value came from — invaluable when an override is silently being shadowed by a higher-precedence source.

See [reference/cli.md](reference/cli.md) for the full CLI surface.

## See also

- [Quickstart](quickstart.md)
- [Deployment](deployment.md)
- [reference/cli.md](reference/cli.md)
- [reference/metrics.md](reference/metrics.md)
- [concepts/csam-defense.md](concepts/csam-defense.md)
- [operations/security.md](operations/security.md)
