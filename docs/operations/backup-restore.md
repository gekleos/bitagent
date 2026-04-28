# Backup and restore

BitAgent persists everything to Postgres. The single non-recreatable artefact is the database; everything else (DHT routing table, classifier rules, TMDB poster cache, Prometheus metrics) regenerates on its own.

If you remember nothing else from this page: **`pg_dump` your Postgres volume on a daily cron, keep two weeks.** That's the entire backup story for most operators.

## What needs backing up

| Asset | Where it lives | Recoverable from scratch? |
|---|---|---|
| **Indexed corpus + classifier state** | Postgres (`bitmagnet` DB) | No — back it up. |
| **DHT routing table** | in-memory | Yes — rebuilds in ~3 min on restart. |
| **CEL classifier rules** | bundled in the BitAgent image | Yes — they're in the binary. |
| **TMDB poster cache** | dashboard's SQLite sidecar | Yes — refetches on demand. |
| **Prometheus metrics** | Prometheus's own TSDB | Backed up by Prometheus, not BitAgent. |
| **Dashboard SQLite sidecar** | `/data/bitagent-ui.db` in `bitagent-ui` | Optional — operator overrides + audit log. Most operators don't bother. |

So in practice, your backup target is one Postgres database.

## Quick logical dump

The most common pattern is a nightly `pg_dump` to a compressed file. The Postgres container in the bundled compose stack is `bitagent-postgres` (or `postgres` depending on your service name); adjust if yours is different.

```bash
docker exec bitagent-postgres pg_dump -U bitmagnet bitmagnet \
  | gzip > "bitagent-$(date +%F).sql.gz"
```

Output is a `.sql.gz` file (typically a few hundred MB to a few GB depending on corpus size and seasoning). It's portable across Postgres 14+ targets.

## Restore from logical dump

Restore into a fresh, empty database. If you're replacing in place, drop and recreate first:

```bash
docker exec bitagent-postgres psql -U bitmagnet -c 'DROP DATABASE IF EXISTS bitmagnet;'
docker exec bitagent-postgres psql -U bitmagnet -c 'CREATE DATABASE bitmagnet OWNER bitmagnet;'
gunzip -c bitagent-2026-04-28.sql.gz \
  | docker exec -i bitagent-postgres psql -U bitmagnet bitmagnet
```

Restart BitAgent after the restore — it auto-reconnects, schema migrations re-apply if the dump pre-dates a migration.

## Cron-driven nightly backup

Drop this script as `/etc/cron.daily/bitagent-backup` (chmod +x):

```bash
#!/bin/sh
set -euo pipefail

DEST=/var/backups/bitagent
STAMP=$(date +%F-%H%M)

mkdir -p "$DEST"
docker exec bitagent-postgres pg_dump -U bitmagnet bitmagnet \
  | gzip > "$DEST/bitagent-$STAMP.sql.gz"

# Retain 14 days
find "$DEST" -name 'bitagent-*.sql.gz' -mtime +14 -delete
```

Verify it ran the next morning:

```bash
ls -lh /var/backups/bitagent/
```

If you want offsite, follow up with a `rclone copy /var/backups/bitagent <remote>:bitagent-backups/` line in the same script.

## Verifying a backup

`gunzip -t` checks file integrity (cheap):

```bash
gunzip -t /var/backups/bitagent/bitagent-2026-04-28.sql.gz && echo OK
```

A real restore test (every quarter or so) is the only way to know your dumps actually round-trip:

```bash
# Throwaway sidecar Postgres
docker run --rm -d --name pg-restore-test -e POSTGRES_PASSWORD=test -p 55432:5432 postgres:16-alpine

# Restore into it
gunzip -c bitagent-2026-04-28.sql.gz \
  | docker exec -i pg-restore-test psql -U postgres -c "CREATE DATABASE bitmagnet;" \
  || true
gunzip -c bitagent-2026-04-28.sql.gz \
  | docker exec -i pg-restore-test psql -U postgres bitmagnet

# Smoke check
docker exec pg-restore-test psql -U postgres bitmagnet -c \
  "SELECT count(*) FROM torrents;"

docker rm -f pg-restore-test
```

## Full base backup (PITR)

For point-in-time recovery use `pg_basebackup` + WAL archiving. This is standard Postgres territory; nothing BitAgent-specific.

1. Configure `archive_command` in `postgresql.conf` (or via `ALTER SYSTEM`):

   ```conf
   archive_mode = on
   archive_command = 'cp %p /var/lib/postgresql/wal-archive/%f'
   ```

2. Take a base backup periodically:

   ```bash
   docker exec bitagent-postgres pg_basebackup \
     -D /var/lib/postgresql/basebackup-$(date +%F) \
     -U bitmagnet -v -P -X stream
   ```

3. Restore by stopping the container, replacing the data directory with the base backup, and replaying WAL up to the desired point.

Refer to the [Postgres 16 backup docs](https://www.postgresql.org/docs/16/backup.html) for the full procedure. Most BitAgent operators don't need PITR — a daily logical dump is sufficient.

## Disaster recovery checklist

When restoring after a host loss:

1. Stand up a new host with Docker + Compose.
2. Restore Postgres from the most recent dump (procedure above).
3. Pull or re-build the BitAgent image: `docker compose -f examples/docker-compose.public.yml up -d`.
4. Wait ~3 min for DHT bootstrap.
5. Verify:
   - `curl -sf http://localhost:3333/healthz` returns `200`.
   - `curl -s "http://localhost:3333/torznab/api?t=caps&apikey=$TORZNAB_API_KEY"` returns valid XML.
   - The dashboard's Library tab shows the restored corpus.
6. Reconnect `*arr` indexers — they should re-test green without configuration changes.
7. Re-enable `*arr` Connect → Webhook entries (the URL changed if your host did).

## Optional: dashboard sidecar (`bitagent-ui.db`)

The `bitagent-ui` container keeps a small SQLite at `/data/bitagent-ui.db` for operator-set overrides, the dashboard's audit log, and the TMDB poster cache. Most operators skip backing this up — overrides are easy to re-enter, audit log is nice-to-have, posters refetch.

If you do want to back it up:

```bash
docker cp bitagent-ui:/data/bitagent-ui.db ./bitagent-ui-$(date +%F).db
```

Restore (with `bitagent-ui` stopped):

```bash
docker compose stop bitagent-ui
docker cp ./bitagent-ui-2026-04-28.db bitagent-ui:/data/bitagent-ui.db
docker compose start bitagent-ui
```

## What NOT to back up

- The DHT routing table — it's ephemeral and rebuilds in 3 min.
- TMDB poster cache — regenerates on demand.
- Prometheus TSDB — that's Prometheus's job, not BitAgent's.
- Container logs — capture them in your log aggregator if you care, but don't snapshot them via this script.

## See also

- [operations/upgrade.md](upgrade.md) — pre-upgrade backup checklist
- [deployment.md](../deployment.md) — the compose layouts
- [troubleshooting.md](../troubleshooting.md)
