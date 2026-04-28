# Upgrade

BitAgent follows semver:

- **PATCH** (`1.0.0 → 1.0.1`) — bug fixes. Safe to upgrade in place.
- **MINOR** (`1.0.x → 1.1.0`) — new features, additive schema changes. Take a backup first.
- **MAJOR** (`1.x → 2.0.0`) — breaking changes. Take a backup, read the changelog, plan the window.

Migrations are forward-only and run automatically on worker startup via goose. There is no manual migration step.

## Read the changelog first

Before any upgrade, skim:

- [project/changelog.md](../project/changelog.md) — release notes per tag.
- The `HISTORY.md` file at the repo root — the longer-form decision log.

Look for breaking changes, deprecation notices, and any "operator action required" callouts.

## Public quickstart upgrade (build-from-source)

If you deployed from `examples/docker-compose.public.yml` and built the image locally:

```bash
cd /path/to/bitagent
git pull
docker compose -f examples/docker-compose.public.yml \
  --env-file examples/.env.public \
  up -d --build
```

Wait ~3 minutes for the full restart and DHT re-bootstrap. The Postgres data volume persists — you do not lose the indexed corpus.

## Image-tagged upgrade (advanced)

For deployments using `ghcr.io/gekleos/bitagent:<tag>` (the advanced host / Portainer pattern):

1. Bump `BITAGENT_IMAGE_TAG` in your secrets store (secrets manager, Vault, or environment).
2. Trigger a Portainer redeploy — the standard pattern is git-backed stack with 5m auto-update + GitLab webhook on any push to `deploy/`.
3. Verify the container actually recreated:
   ```bash
   docker inspect bitagent --format '{{ .State.StartedAt }}'
   ```
   `StartedAt` must be newer than the merge commit time. If it's older, the redeploy was a no-op (image digest unchanged) — force a redeploy with `pullImage: true` in Portainer's stack config.

## Pre-upgrade backup (MINOR / MAJOR)

```bash
docker exec bitagent-postgres pg_dump -U bitmagnet bitmagnet \
  | gzip > "bitagent-pre-upgrade-$(date +%F).sql.gz"
```

Keep this on a separate host or volume. If the upgrade goes wrong, this is your fallback.

For PATCH upgrades, skip the backup if you have a recent (≤ 24h) nightly dump.

## Post-upgrade verification

Run these checks in order:

```bash
# 1. All services healthy
docker compose ps

# 2. Health endpoint
curl -sf http://localhost:3333/healthz
# expect: HTTP 200

# 3. Torznab caps endpoint
curl -s "http://localhost:3333/torznab/api?t=caps&apikey=$TORZNAB_API_KEY" | head -3
# expect: <?xml version="1.0" ...?> ...

# 4. DHT peer count after 5 min
curl -s http://localhost:3333/metrics \
  | grep '^bitagent_dht_client_request_concurrency'
# expect: nonzero values; sum should be > 100

# 5. First search (from a real *arr or via curl)
curl -s "http://localhost:3333/torznab/api?t=tvsearch&q=ubuntu&apikey=$TORZNAB_API_KEY" | head -10
# expect: valid RSS XML with <item> entries (or 0-item RSS, but valid)
```

If any of these fail, jump to [Common pitfalls](#common-upgrade-pitfalls) below.

## Rolling back

### Image-based

Bump `BITAGENT_IMAGE_TAG` to the previous tag, redeploy.

### Source-built

```bash
cd /path/to/bitagent
git checkout <previous-tag>
docker compose -f examples/docker-compose.public.yml \
  --env-file examples/.env.public \
  up -d --build
```

### Database rollback

Migrations are additive in normal cases — you don't usually need a DB rollback. If you do:

```bash
# Restore from the pre-upgrade dump (preferred — clean state)
gunzip -c bitagent-pre-upgrade-<date>.sql.gz \
  | docker exec -i bitagent-postgres psql -U bitmagnet bitmagnet

# OR roll back specific migrations via goose (advanced)
docker exec bitagent goose -dir /app/migrations \
  postgres "host=postgres user=bitmagnet password=$POSTGRES_PASSWORD dbname=bitmagnet sslmode=disable" \
  down-to <previous_version>
```

The dump-restore path is safer than goose-down — `down` migrations may not be tested for every release.

## Common upgrade pitfalls

### Stale image cache

Webhook fires HTTP 204 but `docker pull :latest` returns "access forbidden" — the registry login expired. Symptom: container restarts but version unchanged.

```bash
docker login ghcr.io/gekleos -u gekleos
# then redeploy
```

### Schema drift after a partial migration

Extremely rare. If migrations failed mid-way and the worker is now wedged:

1. Restore from the pre-upgrade dump.
2. Restart the upgrade with `LOG_LEVEL=debug`.
3. Capture the failing migration log and open a GitHub issue.

### DHT peer count stays low after upgrade

UDP egress was working before, isn't now. Most likely cause: a firewall rule changed, or the VPN reconnected to a different exit IP.

```bash
# Quick UDP egress check from inside the container
docker exec bitagent sh -c 'cat /proc/net/udp | head -5'
# (entries with rem_address ≠ 00000000:0000 are healthy outbound)
```

If you're behind a VPN, verify the inbound port-forward at your provider matches `BITAGENT_PEER_PORT`.

### Healthz returns 500

Postgres is unreachable from the BitAgent container. Common causes: Postgres restarted last and BitAgent's connection pool is wedged; the password env var changed; the network alias dropped. `docker compose restart bitagent` usually unwedges it.

## Major version upgrades (vN.0.0)

For a major version bump:

1. Read the changelog **carefully**. Note every "BREAKING:" line.
2. Run the upgrade in a staging environment first if you can.
3. Take a fresh backup right before flipping the prod tag.
4. Plan a longer maintenance window (30 min minimum) — even if the upgrade itself is fast, you want time to verify and roll back if needed.
5. Watch the logs and `bitagent_*` metrics for the first hour.

## See also

- [operations/backup-restore.md](backup-restore.md)
- [project/changelog.md](../project/changelog.md)
- [troubleshooting.md](../troubleshooting.md)
- [deployment.md](../deployment.md)
