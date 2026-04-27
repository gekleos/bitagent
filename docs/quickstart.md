# Quickstart: 15 Minutes to Indexing

Follow this exact sequence to deploy BitAgent, seed the DHT network, and connect it to Sonarr. You will have a fully functional Torznab indexer running on `localhost` by the end of this guide.

## 1. Prerequisites

Ensure your host meets the baseline resource and network requirements before proceeding. BitAgent requires Postgres 14 or later; if you lack an external instance, the bundled database service in the example compose file is fully supported and requires zero configuration. Docker and Docker Compose must be installed and accessible to your user. Verify with `docker info` and `docker compose version` before continuing.

Allocate a minimum of **2 GB RAM** and **10 GB persistent disk** for the first month of operation. BitAgent caches magnet metadata, DHT node tables, and query logs during the warmup phase. Insufficient allocation will trigger OOM kills or disk write stalls.

Network egress must allow unrestricted **outbound TCP and UDP traffic**. The DHT protocol relies on UDP `4413` (default) and TCP `80/443` for tracker fallback. Inbound UDP must reach the BitAgent container; behind NAT, forward UDP `4413` to your container host. Closed UDP will prevent node discovery and cripple search response times.

## 2. Get the compose file

Retrieve the public-internet compose configuration from the repository. This file orchestrates four services: `bitagent` (Go indexer), `bitagent-ui` (FastAPI dashboard), `postgres:16-alpine`, and a `caddy:2-alpine` reverse proxy.

```bash
curl -O https://raw.githubusercontent.com/gekleos/bitagent/main/examples/compose.public.yml
```

Open the file and review the service definitions. The `bitagent` service runs the indexer and exposes Torznab on port `3333`. The `bitagent-ui` service exposes the dashboard on port `8080`. Caddy terminates TLS via Let's Encrypt automatic certificates and routes `bitagent.example.com` to the dashboard.

## 3. Generate auth + secrets

BitAgent requires two independent cryptographic keys: one for dashboard administration and one for *arr Torznab queries. Generate both with OpenSSL — execute twice to produce two distinct 64-character hex strings:

```bash
openssl rand -hex 32   # this is your DASHBOARD_API_KEY
openssl rand -hex 32   # this is your TORZNAB_API_KEY
```

Create a `.env` file in the same directory as your compose file:

```env
DASHBOARD_API_KEY=<paste_first_generated_key>
TORZNAB_API_KEY=<paste_second_generated_key>
BITAGENT_DOMAIN=bitagent.example.com
POSTGRES_DB=bitagent
POSTGRES_USER=bitagent
POSTGRES_PASSWORD=<a_separate_strong_password>
```

**Do not reuse keys between fields.** If the dashboard key leaks, the Torznab endpoint remains protected, and vice versa. Rotate immediately if you ever commit `.env` to version control.

## 4. First start

Deploy the stack in detached mode:

```bash
docker compose -f compose.public.yml up -d
```

Wait **3 minutes** before checking service status. The DHT bootstrap process needs time to locate initial peers and build the routing table. Querying before completion returns empty results.

After the 3-minute window, verify all services are healthy:

```bash
docker compose ps
```

You should see four services in `Up (healthy)` state. If any service shows `Restarting` or `unhealthy`, run `docker compose logs <service_name>`. Common issues: port conflicts on `8080`/`3333`, insufficient disk space, or firewall rules blocking UDP egress.

## 5. Open the dashboard

Navigate to `https://bitagent.example.com` in your browser (or `http://localhost:8080` if testing locally without TLS). On first load, the dashboard displays a one-time banner with the `DASHBOARD_API_KEY` for confirmation. Copy it to your password manager.

The top of the dashboard shows DHT peer count, indexer throughput, and cache hit ratio. Below, a live query feed and a Library tab populate as the classifier processes its first batch.

## 6. Sanity check

Validate the API endpoints before connecting Sonarr:

```bash

# Dashboard healthcheck

curl -s http://localhost:8080/healthz | jq .

# Authenticated API ping

curl -s "http://localhost:8080/api/me?apikey=$DASHBOARD_API_KEY" | jq .

# Torznab capabilities

curl -s "http://localhost:3333/torznab?t=caps&apikey=$TORZNAB_API_KEY" | head -20
```

Expected responses: `{"status":"ok",...}` for healthcheck; `{"id":"api-client",...}` for `/api/me`; valid Torznab `<caps>` XML for capabilities. Any 401 means a key mismatch — double-check `.env`.

## 7. Add to Sonarr

Open Sonarr → `Settings → Indexers → Add → Torznab → Custom`:

- **Name:** `BitAgent`
- **Enable:** ✓
- **URL:** `http://bitagent:3333/torznab`  *(use the compose service name; `localhost` won't resolve from inside Sonarr's container)*
- **API Key:** paste your `TORZNAB_API_KEY`
- **Categories:** select TV, Movies, or all per your library
- **Priority:** `25` (or whatever fits your stack — leave default if unsure)

Click **Test**. The button turns green with `Test was successful`. If you see `Connection failed`, verify the URL uses the compose service name and that BitAgent is actually reachable from Sonarr's network. Save the indexer.

## 8. Watch first grabs

Trigger a manual search in Sonarr (a single episode is enough) and watch the BitAgent dashboard's Library tab. Within **5–10 minutes** you should see indexed torrents appearing as Sonarr's first poll cycle completes.

The Library columns show seeder count, classifier confidence, and content type. Rows with the green status pill are confirmed grabs. Rows with a yellow pill are pending classification.

If nothing appears after 10 minutes, check:
- DHT peer count > 100 in the dashboard header
- Sonarr's indexer-test came back green
- No `BITAGENT_DHT_BIND_ADDR` conflict (check container logs)

## 9. What's next

BitAgent is now operational and feeding your *arr stack. Continue with:

- **Configuration reference**: `bitagent.dev/docs/configuration` — every env var, every default
- **Tuning guide**: `bitagent.dev/docs/performance-tuning` — Postgres, classifier, DHT
- **Troubleshooting**: `bitagent.dev/docs/troubleshooting` — port mapping, DHT starvation, logs
- **Customization**: `bitagent.dev/docs/customizing` — CEL rules, custom classifier extensions

For private-tracker-style setups (Prowlarr direct, api-key only, no SSO), see [docs/integrations/private-tracker-mode.md](integrations/private-tracker-mode.md).
