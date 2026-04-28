# Frequently Asked Questions

## What BitAgent is

### Q: How is BitAgent different from bitmagnet?

A: BitAgent is a hardened, indexer-focused fork of bitmagnet engineered specifically for the *arr ecosystem integration pipeline. It strips unnecessary daemon layers, replaces the default SQL backend with optimized PostgreSQL schemas, and ships with strict Torznab compliance by default. Unlike upstream, it enforces rate limiting and exposes structured evidence fields directly to indexer clients. See `bitagent.dev/docs/architecture` for the full component comparison.

### Q: How does it compare to Prowlarr indexers?

A: Prowlarr aggregates external HTTP tracker APIs, while BitAgent crawls the DHT network directly to build a self-contained torrent index. It operates without subscription walls or API key dependencies, relying entirely on local peer discovery and BEP routing. You run it as a standalone HTTP service that exposes a compliant Torznab endpoint for *arr clients.

### Q: Can BitAgent replace Prowlarr entirely?

A: No. BitAgent complements Prowlarr rather than replacing it. You should configure BitAgent as a secondary indexer to supplement your existing tracker list with high-entropy DHT results. Prowlarr still manages your primary HTTP-based indexers, while BitAgent fills gaps in the swarm.

### Q: What protocols does BitAgent actually index?

A: BitAgent primarily indexes BitTorrent v2 and standard v1 torrents via DHT, BEP-09 fast resume, and peer exchange. It parses .torrent files, magnet URIs, and tracker announces to extract metadata like size, seeders, and file lists. It does not index Usenet, HTTP trackers, or direct download links out of the box.

### Q: How does it differ from standard DHT crawlers?

A: Generic DHT crawlers dump raw k-bucket entries and lack parsing logic, whereas BitAgent runs a full classifier pipeline that normalizes releases into structured evidence objects. It deduplicates via InfoHash, maps custom formats automatically, and persists data in a query-optimized store. This transforms raw swarm noise into *arr-ready results.

## Setup + deployment

### Q: What are the Docker Compose prerequisites?

A: You need Docker 24.0+, Docker Compose v2.24+, and a minimum of 2 vCPUs and 512MB RAM allocated to the service. Ensure your host kernel supports `net.ipv4.ip_forward=1` and `net.core.somaxconn=65535` for DHT binding. Create `/var/lib/bitagent/data` and `/etc/bitagent` before mounting volumes.

### Q: How do I initialize the Postgres database?

A: BitAgent auto-migrates tables on first boot if the schema is missing. Set `DATABASE_URL=postgres://user:pass@postgres:5432/bitagent` in your compose environment block. For external Postgres, run `CREATE DATABASE bitagent OWNER bitagent;` and verify connectivity with `pg_isready -h db -U bitagent` before starting.

### Q: How do I fix pg_ctl startup errors?

A: Check `/var/log/bitagent/pg_ctl.log` for lockfile conflicts or insufficient `shared_buffers` before rebooting. Run `pg_ctlcluster 16 main restart` if systemd is involved, or remove `/var/lib/postgresql/data/PG_VERSION` if the cluster is corrupted. Ensure `postgresql.conf` matches your `shmmax` kernel parameter.

### Q: How should persistent volumes be configured?

A: Mount `/var/lib/bitagent/data` for the object store and `/var/lib/postgresql/data` for WAL files inside the compose file. Use `volumes: - ./data:/var/lib/bitagent/data` in `docker-compose.yml` with `chown 1000:1000`. Set `BITAGENT_DATA_DIR=/var/lib/bitagent/data` to avoid permission denied errors during classifying.

### Q: What network mode is required for DHT?

A: Use `network_mode: host` or map UDP 4413 explicitly to expose your DHT node to the public tracker network. BitAgent binds UDP to `0.0.0.0:4413` by default and will silently drop announcements if NAT traversal fails. Add `BITAGENT_DHT_BIND_ADDR=0.0.0.0:4413` and verify connectivity with `dig +short k.bittorrent.org`.

## Auth + security

### Q: What authentication modes are supported?

A: BitAgent supports `none`, `apikey`, `forms`, and `external` (reverse-proxy / SSO). Configure via `AUTH_METHOD=apikey` in your environment. The `apikey` mode validates `Authorization: Bearer <key>` or `?apikey=<key>` against the `DASHBOARD_API_KEY`. The `external` mode trusts headers from an upstream proxy that already authenticated the user.

### Q: Why is apikey the default auth method?

A: API keys provide stateless, low-overhead validation ideal for *arr indexer clients. They avoid session cookie parsing, reduce attack surface, and integrate natively with Sonarr/Radarr/Prowlarr indexer tokens. The key is validated via header on every Torznab request with constant-time compare.

### Q: What does the threat model cover?

A: The model assumes untrusted *arr clients on internal networks and focuses on API endpoint hardening and rate limiting. It mitigates credential stuffing via rate limiting and prevents path traversal via strict input sanitization. It does not cover host kernel vulnerabilities or DHT network-level eavesdropping.

### Q: How do I rotate API keys safely?

A: Hit `POST /api/settings/regenerate-api-key` from the dashboard while authenticated. The new key takes effect on the next request; the old key is immediately invalidated. Update your *arr indexer configuration with the new key. For zero-downtime rotation, use the dual-key window with `BITAGENT_API_KEY_NEW` env var.

### Q: What reverse proxy guidance applies?

A: Place BitAgent behind Caddy, Traefik, or Nginx with `proxy_set_header X-Real-IP $remote_addr` enabled. If exposing to the public internet, set `TRUST_NPM_HEADERS=false` so that client-supplied `X-Auth-User-Id` headers cannot bypass the API key. Always terminate TLS at the proxy.

## Sonarr/Radarr integration

### Q: What Torznab URL format is required?

A: Configure your indexer as `http://bitagent.example.com:3333/torznab` in the *arr dashboard. Append `apikey=<TORZNAB_API_KEY>` or set the API Key field. Ensure the protocol matches your container port mapping and DNS resolution.

### Q: How do I map evidence to custom formats?

A: BitAgent returns structured `<info>` attributes containing `resolution`, `hdr`, `audio_channels`, and `encoder` fields that *arr can match via custom format IDs. Import the BitAgent evidence manifest from `bitagent.dev/static/evidence-format.json` into *arr and align IDs with your library standards.

### Q: How do I fix search timeouts in *arr?

A: Increase `BITAGENT_SEARCH_TIMEOUT=15s` in your environment and ensure Postgres `statement_timeout` exceeds it. Add `BITAGENT_CACHING=true` to memoize frequent queries and reduce classifier execution time. Monitor `/api/v1/metrics` for `search_duration_seconds` spikes.

### Q: How do I set up the evidence webhook?

A: Set `BITAGENT_EVIDENCE_WEBHOOK_URL=https://internal-collector:9200/batch` and `BITAGENT_EVIDENCE_BATCH_SIZE=250` to stream classified releases to your monitoring stack. BitAgent POSTs JSON payloads with `Content-Type: application/json` and retries up to 3 times on `5xx`.

### Q: Should BitAgent be primary or fallback?

A: BitAgent's DHT coverage is broad but less curated than private trackers, so fallback placement (priority `50–60`) prevents false positives from dominating. Use `Fallback to` settings to trigger BitAgent only when higher-priority indexers return empty. For dedicated DHT-only setups, set BitAgent as primary.

## Resource usage

### Q: What are the baseline resources for 100k torrents?

A: Allocate 2 vCPUs, 512MB RAM, and 40GB NVMe disk for a stable 100k-entry index. Expect ~0.8% CPU usage during idle crawls and peak 1.2 cores during classifier runs. SSD latency under 5ms is mandatory for WAL replay.

### Q: How does library growth scale resources?

A: RAM scales linearly at ~4MB per 10k entries for the in-memory LRU cache. Disk grows ~1.5GB per 10k entries due to evidence cache and Postgres TOAST bloat. Add storage before hitting 80% inode usage or 4GB heap pressure.

### Q: When should I scale horizontally?

A: Scale when DHT node count exceeds 15k or search latency breaches 15s. Run read replicas via `BITAGENT_DB_REPLICA_URL` and distribute traffic across instances. Do not split the write path; the classifier requires single-writer serialization.

### Q: What are slow-disk gotchas?

A: HDDs cause WAL writer stalls, triggering DB lock-timeout errors during heavy classification. Disable `BITAGENT_WAL_SYNC=true` only if using ZFS with `logbias=throughput`. Monitor `pg_stat_io` for await times >10ms and switch to block-backed storage.

### Q: How do I monitor heap and GC?

A: Enable `BITAGENT_METRICS_ADDR=:9100` and scrape `/metrics` with Prometheus. Watch `go_memstats_alloc_bytes` and `gc_pause_ns` for collection latency spikes. Alert when heap growth exceeds 200MB/hr or GC pauses breach 50ms.

## Privacy

### Q: Does BitAgent expose my IP on DHT?

A: Yes. The DHT protocol requires your node to announce its IP via BEP-05 and BEP-10 for routing table population. You cannot route DHT traffic through a proxy without breaking k-bucket consensus. Use a dedicated VM, network VLAN, or route through a VPN to isolate exposure.

### Q: Are TMDB queries cached or leaked?

A: BitAgent caches TMDB lookups in `poster_cache` (SQLite) for 7 days by default. Subsequent requests hit the local lookup table, not the external API. Clear the cache via the Settings tab to force fresh metadata fetches. Disable TMDB entirely by leaving `TMDB_API_KEY` empty.

### Q: What data leaves my host externally?

A: Only DHT announce packets, peer handshake payloads, and explicit API calls (TMDB if configured) exit the host. All internal classification, deduplication, and storage remain local. Set `BITAGENT_TELEMETRY=false` (default) to disable any usage reports.

### Q: How long are logs retained?

A: Application logs rotate daily at `/var/log/bitagent/app.log` with `maxsize=100M` and `maxage=3d`. Postgres WAL files are archived until `BITAGENT_WAL_RETENTION=7d` expires. Purge manually via `logrotate -f /etc/bitagent/logrotate.conf`.

### Q: How do I run in fully-offline mode?

A: Set `BITAGENT_DHT_ENABLED=false` and leave `TMDB_API_KEY` empty. Point `BITAGENT_EVIDENCE_SOURCE` to a local CSV or SQLite dump. Start with `--offline` flag to skip network bindings. Querying remains functional using only persisted objects.

## Troubleshooting

### Q: Why are search results empty?

A: Verify DHT peers are populated and the classifier is enabled. Run `/api/v1/status` and confirm `dht.peers_active > 100`. If `evidence_count=0`, trigger a full rescan and monitor classifier logs. Low peer counts cause search starvation; verify UDP port forwarding.

### Q: Why is evidence missing classifier tags?

A: The classifier may have skipped the record due to invalid UTF-8 in the announce string. Check classifier logs for `encoding_error` entries. Re-run with `BITAGENT_CLASSIFIER_STRIP_INVALID=true` to force normalization.

### Q: How do I fix BEP-9 choking?

A: Reduce `BITAGENT_DHT_PEER_LIMIT=48` and set `BITAGENT_DHT_KEEPALIVE=15s` to stabilize routing. Monitor `bitagent_dht_peers_choked_total` and reduce concurrency if spikes persist.

### Q: Why do *arr clients return 401/403?

A: The indexer token does not match `TORZNAB_API_KEY` or the route is blocked. Verify the header matches `Authorization: Bearer <key>` exactly. Enable debug auth logging to inspect raw request validation.

### Q: How do I recover from Postgres index corruption?

A: Run `REINDEX INDEX CONCURRENTLY bitagent_release_idx;` while BitAgent is running. Set `BITAGENT_READ_ONLY=true` temporarily to prevent write conflicts. Verify integrity with `pg_verifycluster` and restore from `pg_basebackup` if corruption persists.

## Performance tuning

### Q: How do I tune Postgres autovacuum?

A: Set `autovacuum_vacuum_scale_factor=0.05`, `autovacuum_analyze_scale_factor=0.02`, and `autovacuum_max_workers=3` for high-churn classifier tables. Increase `maintenance_work_mem=512MB` to accelerate index builds. Monitor `pg_stat_user_tables.n_dead_tup`.

### Q: What is the optimal classifier batch size?

A: Set `BITAGENT_CLASSIFIER_BATCH=500` and `BITAGENT_CLASSIFIER_CONCURRENCY=16` to balance memory and latency. Larger batches improve throughput but increase GC pressure. Monitor `go_gc_duration_seconds` and reduce if pauses exceed 200ms.

### Q: How does BEP-9 concurrency impact crawl speed?

A: Higher concurrency (`BITAGENT_DHT_CONCURRENCY=192`) increases crawl speed but triggers throttling on strict trackers. Keep at `96–128` for stable operation. Use `BITAGENT_DHT_BACKOFF=2s` for exponential delay on choke responses.

### Q: What retention policy prevents disk bloat?

A: Set `BITAGENT_RETENTION_DAYS=90`, `BITAGENT_CLASSIFIER_TTL=60d`. Run `bitagent prune --dry-run` before applying. Archive old evidence to cold storage if needed.

### Q: How do I tune Golang GOMAXPROCS?

A: Set `GOMAXPROCS=4` for 8-core hosts to avoid thread contention. Higher values yield diminishing returns. Verify with `pprof block` and `GODEBUG=gctrace=1`. Pin BitAgent to dedicated CPU cores via cgroups for latency-critical workloads.

## Customization

### Q: How do I write a CEL rule for filtering?

A: Create `$BITAGENT_DATA_DIR/config/rules.cel` with expressions like `release.source == "WEBRip" && release.confidence < 0.85` to suppress low-quality matches. Validate via `cel --expr-file rules.cel` and hot-reload with `bitagent reload rules`.

### Q: Where do I place custom classifier extensions?

A: Drop compiled Go plugins or WASM modules into `$BITAGENT_DATA_DIR/extensions/` and set `BITAGENT_EXTENSIONS_PATH=/var/lib/bitagent/extensions`. Load via `bitagent extensions load ./my_classifier.so`. Extensions implement the `Classifier` interface.

### Q: How do I add custom tags to the schema?

A: Extend `$BITAGENT_DATA_DIR/schema/tags.json` with `{"tag":"4K_DOLBY","weight":0.9,"match_regex":"(dolby\\s*vision|dovi)"}` and restart the classifier. Run `bitagent schema validate` to ensure regex compiles. Tags propagate to Torznab `<info>` attributes.

### Q: SQLite vs Postgres for evidence storage?

A: Postgres handles concurrent writes and large indexes efficiently for >50k entries. SQLite is acceptable for <20k caches but lacks connection pooling. Use SQLite only for single-writer dev or the `bitagent-ui` settings/poster cache.

### Q: How do I override the Torznab response template?

A: Copy `/opt/bitagent/templates/torznab.xml` to `$BITAGENT_DATA_DIR/templates/torznab-custom.xml` and set `BITAGENT_TORZNAB_TEMPLATE=...`. Validate XML structure with `xmllint --noout` before hot-reloading.

## Project + community

### Q: What license governs BitAgent?

A: BitAgent is licensed under the MIT License. You may modify, distribute, and sublicense the code commercially without restriction. Source compliance requires retaining the LICENSE file and copyright notices.

### Q: Is BitAgent a fork of bitmagnet?

A: Yes. BitAgent is a 2026 fork of `bitmagnet-io/bitmagnet` after upstream went dormant in July 2025. We share the DHT protocol implementation and core indexing primitives but have rewritten classifier preempt, evidence pipeline, auth, observability, and release scaffolding.

### Q: How do I submit patches?

A: Fork `gekleos/bitagent`, create a feature branch, run `make lint test` locally, and open a PR with a clear commit message and updated docs. PRs require passing lint, unit tests, and Docker build checks before review.

### Q: What is the procedure for security disclosures?

A: Email `security@bitagent.example.com` or use GitHub's private vulnerability reporting. Do not open public issues for vulnerabilities. We respond within 72 hours and provide CVE attribution upon patch.

### Q: How is governance structured?

A: A small core-maintainer council reviews proposals via RFC documents and quarterly release cadences. Roadmap items are tracked in `ROADMAP.md` and prioritized by operator feedback and stability requirements. Major architectural shifts require consensus among core contributors.
