# Deployment Guide

End-to-end deployment of the BitAgent stack: the Go DHT crawler, the FastAPI dashboard, Postgres for the metadata index, and a reverse proxy for TLS / auth.

## Architecture

```text
                  ┌──────────────────────┐
                  │       DHT swarm      │
                  │       (BEP-5 UDP)    │
                  └─────────────┬────────┘
                                │ UDP/4413
                                ▼
                  ┌──────────────────────┐    GraphQL + Torznab
                  │   bitagent (Go)      │◄──────────────────────┐
                  │  - DHT crawler       │                       │
                  │  - classifier        │   ┌───────────────────┴───────────┐
                  │  - Torznab adapter   │   │   Sonarr / Radarr / Lidarr    │
                  │  - GraphQL + metrics │   │  Readarr / Prowlarr           │
                  └────┬─────────────────┘   └───────────┬───────────────────┘
                       │ TCP/3333                        │ webhook POST
                       ▼                                 ▼
                  ┌──────────────┐              ┌────────────────────┐
                  │  Postgres 16 │              │   bitagent-ui      │
                  │  (metadata)  │              │  - dashboard       │
                  └──────────────┘              │  - /api/evidence   │
                                                │  - SQLite sidecar  │
                                                └────┬───────────────┘
                                                     │ TCP/8080 (or APP_PORT)
                                                     ▼
                                                operator browser
                                                (via Caddy / NPM / Authelia)
```

## Prerequisites

- **Docker** 24+ and **Docker Compose** v2.
- **2 GiB RAM** headroom for Postgres + the crawler at steady state. 4 GiB if you want headroom for the LLM-rerank classifier path.
- **UDP/4413 inbound** reachable from the public internet — closed ports cap DHT yield at ~20% of full rate.
- **Postgres 16+** (the bundled compose service is fine; bring your own only if you have an existing cluster).
- **A domain** if you're going public — the `compose.public.yml` flow assumes you have DNS pointed at the Docker host and Caddy handles automatic TLS.

## Reference compose layouts

Three canonical shapes. Pick the one that matches your network topology.

### `compose.tailnet.yml` — private network or LAN-only

No TLS, `REQUIRE_AUTH=false`. Safe **only** when the dashboard is unreachable from the public internet.

```yaml
services:
  bitagent:
    image: ghcr.io/bitagent-dev/bitagent:latest    # pin a SHA in production
    container_name: bitagent
    ports:
      - "3333:3333/tcp"
      - "4413:4413/udp"
    environment:
      DATABASE_URL: postgresql://bitagent:bitagent@postgres:5432/bitagent
      BITAGENT_DHT_BIND_ADDR: ":4413"
      BITAGENT_LOG_LEVEL: info
      TORZNAB_API_KEY: ""    # empty = open Torznab; fine on tailnet
    volumes:
      - bitagent_core_data:/data
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  bitagent-ui:
    image: ghcr.io/bitagent-dev/bitagent-ui:latest    # pin a SHA in production
    container_name: bitagent-ui
    ports:
      - "8080:8080"
    environment:
      BITAGENT_GRAPHQL_URL: http://bitagent:3333/graphql
      BITAGENT_METRICS_URL: http://bitagent:3333/metrics
      REQUIRE_AUTH: "false"
      TMDB_API_KEY: ""    # set if you want poster art
      LOG_LEVEL: info
    volumes:
      - bitagent_ui_data:/data
    depends_on:
      - bitagent
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: bitagent-postgres
    environment:
      POSTGRES_USER: bitagent
      POSTGRES_PASSWORD: bitagent
      POSTGRES_DB: bitagent
    volumes:
      - bitagent_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bitagent -d bitagent"]
      interval: 10s
      timeout: 5s
      retries: 6
    restart: unless-stopped

volumes:
  bitagent_core_data:
  bitagent_postgres_data:
  bitagent_ui_data:
```

### `compose.public.yml` — public internet, Caddy auto-TLS, API-key auth

`REQUIRE_AUTH=true`, both dashboard and Torznab keys set, dashboard reachable at a real domain. Caddy terminates TLS via Let's Encrypt.

```yaml
services:
  bitagent:
    image: ghcr.io/bitagent-dev/bitagent:latest
    container_name: bitagent
    ports:
      - "4413:4413/udp"
      # 3333 is internal only — Caddy proxies it
    environment:
      DATABASE_URL: postgresql://bitagent:${POSTGRES_PASSWORD}@postgres:5432/bitagent
      TORZNAB_API_KEY: ${TORZNAB_API_KEY}
      BITAGENT_LOG_LEVEL: info
    volumes:
      - bitagent_core_data:/data
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  bitagent-ui:
    image: ghcr.io/bitagent-dev/bitagent-ui:latest
    container_name: bitagent-ui
    environment:
      BITAGENT_GRAPHQL_URL: http://bitagent:3333/graphql
      BITAGENT_METRICS_URL: http://bitagent:3333/metrics
      REQUIRE_AUTH: "true"
      DASHBOARD_API_KEY: ${DASHBOARD_API_KEY}
      TORZNAB_API_KEY: ${TORZNAB_API_KEY}
      TMDB_API_KEY: ${TMDB_API_KEY}
      LOG_LEVEL: info
    volumes:
      - bitagent_ui_data:/data
    depends_on:
      - bitagent
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: bitagent-postgres
    environment:
      POSTGRES_USER: bitagent
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: bitagent
    volumes:
      - bitagent_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bitagent -d bitagent"]
      interval: 10s
      timeout: 5s
      retries: 6
    restart: unless-stopped

  caddy:
    image: caddy:2-alpine
    container_name: bitagent-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    restart: unless-stopped

volumes:
  bitagent_core_data:
  bitagent_postgres_data:
  bitagent_ui_data:
  caddy_data:
  caddy_config:
```

Minimal `Caddyfile` next to it:

```caddy
bitagent.example.com {
    reverse_proxy bitagent-ui:8080
}
```

`.env` (next to compose, in `.gitignore`):

```text
DASHBOARD_API_KEY=<openssl rand -hex 32>
TORZNAB_API_KEY=<openssl rand -hex 32, DIFFERENT KEY>
POSTGRES_PASSWORD=<openssl rand -hex 16>
TMDB_API_KEY=<your TMDB v3 key, optional>
```

### `compose.authelia.yml` — public internet, SSO via Authelia

Same as `compose.public.yml` but Authelia (or oauth2-proxy / Cloudflare Access) handles the front-door auth, and the dashboard trusts the `X-Forwarded-User` header instead of validating an API key for browser sessions.

Diff against `compose.public.yml`:

```yaml
  bitagent-ui:
    environment:
      REQUIRE_AUTH: "true"
      DASHBOARD_API_KEY: ${DASHBOARD_API_KEY}    # still needed for /api/* scripted access
      TORZNAB_API_KEY: ${TORZNAB_API_KEY}
      TRUST_FORWARDED_USER: "true"               # ← new
      TMDB_API_KEY: ${TMDB_API_KEY}
```

The Caddyfile becomes:

```caddy
bitagent.example.com {
    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.example.com/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
    reverse_proxy bitagent-ui:8080
}
```

Authelia must inject `Remote-User` (or rename via Caddy's `header_up X-Forwarded-User {http.reverse_proxy.header.Remote-User}`).

## Generating keys

Two distinct keys, **never reuse one for the other**:

```bash
# Dashboard browser/scripted auth
openssl rand -hex 32   # → DASHBOARD_API_KEY

# Torznab API for *arr
openssl rand -hex 32   # → TORZNAB_API_KEY (must differ from above)
```

Rotate by:

1. Generate new key.
2. Update `.env`.
3. `docker compose up -d` (the changed env triggers a recreate).
4. Update `*arr` Torznab indexer config (or scripted callers) with the new key.

## First-run checklist

```bash
docker compose up -d
docker compose logs -f bitagent     # watch for "DHT bootstrap complete"
```

Within ~3 minutes the bitagent core should log DHT bootstrap. Then:

1. Open `https://bitagent.example.com` (or `http://localhost:8080` for tailnet).
2. Authenticate (API key, Authelia, or open access depending on layout).
3. **Wants tab** — add a few targets so the classifier has bias from day one (see [Wants Guide](wants.md)).
4. **Sonarr → Settings → Indexers → Add → Torznab Custom** — URL `https://bitagent.example.com/torznab` (or `http://bitagent:3333/torznab` if same Docker network), API Key = `TORZNAB_API_KEY`. Repeat for Radarr / Lidarr / Readarr.
5. **Sonarr/Radarr → Settings → Connect → Add → Webhook** — URL `https://bitagent.example.com/api/evidence`, POST, triggers On Grab + On Import. Repeat for each `*arr`. See [Evidence Pipeline](evidence.md).
6. Wait ~30 minutes for the classifier to admit the first wave.

## Persistence and backups

Three named volumes own all persistent state:

| Volume | Holds | Lose it = |
| --- | --- | --- |
| `bitagent_core_data` | DHT routing-table snapshot | Slower bootstrap; full DHT rediscovery in ~5 min |
| `bitagent_postgres_data` | Indexed metadata (millions of torrent rows) | Full re-crawl, days of yield |
| `bitagent_ui_data` | Wants, evidence log, settings overrides, audit log, poster cache | Operator profile + classifier feedback |

Back up `bitagent_postgres_data` and `bitagent_ui_data`. The core's data volume is recoverable from the public DHT.

`pg_dump` is fine for Postgres; for SQLite use `sqlite3 .backup` or just snapshot the volume — the dashboard pauses writes briefly during shutdown.

## Updating

CI publishes a new image on every commit to `main`, tagged with the short SHA and `:main`. Pin the SHA, not `:main`:

```yaml
image: ghcr.io/bitagent-dev/bitagent-ui:b06dd447
```

To upgrade:

1. Bump the SHA in compose.
2. `docker compose up -d` — only affected services recreate.
3. Volumes survive the recreate; the dashboard re-reads the same `bitagent-ui.db`.

If the new version requires an env var or compose change, the release notes will say so. Don't blind-bump across major versions.

## Common pitfalls

- **Closed UDP/4413** — the single biggest cause of poor crawl yield.
- **Reusing one key for both endpoints** — different threat models, different rotation cadences. Don't.
- **Public internet with `REQUIRE_AUTH=false`** — your dashboard becomes a free Torznab provider for anyone who finds it, plus an open settings-mutation surface. Don't.
- **`TMDB_API_KEY` unset** — Library posters silently fall back to text. Not a bug, but ugly. Free tier is fine.
- **Auto-update points to `:main` or `:latest`** — the docker daemon will sometimes serve stale digests. Pin the SHA.
- **Stack mounting `/data` on bind-mounts owned by root** — the dashboard's container user is `appuser` (uid 10001). Use a named volume, or `chown -R 10001 /your/host/path` first.
