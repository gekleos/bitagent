# Prometheus metrics

BitAgent exposes raw Prometheus metrics on the HTTP port (`3333`) at `/metrics` with no auth. For public exposure, place a reverse proxy in front. A scrape interval of `30s` is recommended — it balances telemetry granularity with backend overhead.

The metric namespace was migrated from `bitmagnet_*` to `bitagent_*` on 2026-04-24. During the dual-emit window, every metric fires under both namespaces simultaneously. Operators using legacy `bitmagnet_*` names in dashboards or alerts continue to receive data; migrate at your own pace. The legacy emit will be turned off (one-line code change) once we have signal that downstreams are migrated — there is no fixed deadline.

## Scrape configuration

Add this job to your Prometheus `scrape_configs`:

```yaml
- job_name: bitagent
  metrics_path: /metrics
  scrape_interval: 30s
  scrape_timeout: 15s
  static_configs:
    - targets: ['localhost:3333']
      labels:
        instance: apollo
        service: bitagent
```

Replace `localhost:3333` with the remote host IP or service hostname when scraping from a different host.

## Dual-emit window

Every metric below is emitted under **two** namespaces during the migration:

- `bitagent_<rest>` — primary, the new canonical name
- `bitmagnet_<rest>` — legacy, kept alive while operators migrate

Cost is negligible (two map lookups + two atomic increments per observation, vs the DHT socket and Postgres write that dominate the request path). Plan to migrate dashboards/alerts to `bitagent_*` at your convenience; we'll announce the cutover date in `HISTORY.md` before flipping.

## `bitagent_dht_*` — DHT crawler

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_dht_crawler_persisted_total` | counter | `entity` | Cumulative entities (torrents) successfully persisted via the DHT crawl path. |
| `bitagent_dht_ktable_hashes_added_total` | counter | — | Cumulative node hashes added to the Kademlia routing table — the headline crawler-pulse metric. |
| `bitagent_dht_client_request_concurrency` | gauge | varies | Active DHT requests in flight. Sum across labels = your effective DHT peer count. |
| `bitagent_dht_client_request_duration_seconds_count` | counter | — | Total DHT request observations (histogram count companion). |
| `bitagent_dht_client_request_duration_seconds_bucket` | histogram | `le` | Cumulative bucketed request-duration observations. |

## `bitagent_postgres_*` — pgstats collector

Scrape-driven, 5-second per-scrape timeout.

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_postgres_database_size_bytes` | gauge | — | Total on-disk size of the database. |
| `bitagent_postgres_table_size_bytes` | gauge | `table` | Per-table on-disk size. Common labels: `torrents`, `torrent_contents`, `label_evidence`, `torrent_canonical_labels`. |
| `bitagent_postgres_table_rows_estimate` | gauge | `table` | `pg_class.reltuples` row estimate per table. |
| `bitagent_postgres_table_dead_tuples` | gauge | `table` | Dead tuples awaiting autovacuum. |
| `bitagent_postgres_table_live_tuples` | gauge | `table` | Live tuples per table. |
| `bitagent_postgres_table_last_autovacuum_age_seconds` | gauge | `table` | Seconds since the last autovacuum on this table. |
| `bitagent_postgres_table_last_analyze_age_seconds` | gauge | `table` | Seconds since the last `ANALYZE` on this table. |
| `bitagent_postgres_connections_state` | gauge | `state` | Active backend connections grouped by state. |
| `bitagent_postgres_pgxpool_*` | gauge | varies | pgx connection pool — acquired, idle, waiting, total. |

## `bitagent_evidence_*` — `*arr` evidence ingest

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_evidence_events_persisted_total` | counter | `source` | Successful evidence persists. `source` ∈ {`arrwebhook`, `arrpoller`, `qbpoller`}. |
| `bitagent_evidence_events_duplicated_total` | counter | — | Events deduplicated against existing rows. |
| `bitagent_evidence_events_rejected_total` | counter | — | Events rejected (auth, parse, schema). |
| `bitagent_evidence_source_errors_total` | counter | `source`, `stage` | Error count per source/stage; dashboard alert candidate. |
| `bitagent_evidence_source_poll_duration_seconds` | histogram | — | Poll latency distribution per source. |

## `bitagent_classifier_*` — base classifier

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_classifier_examined_total` | counter | — | Torrents passed through the classifier. |
| `bitagent_classifier_decision_total` | counter | `decision` | Decision distribution (matched, dropped, ambiguous, etc.). |
| `bitagent_classifier_duration_seconds` | histogram | — | Classifier-stage latency. |

## `bitagent_classifier_preempt_*` — canonical-label preempt

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_classifier_preempt_lookup_total` | counter | `result` | Lookups against the canonical-label cache. `result` ∈ {`hit`, `miss`, `error`}. |
| `bitagent_classifier_preempt_apply_total` | counter | — | Cumulative preempt applications (CEL chain skipped). |
| `bitagent_classifier_preempt_lookup_duration_seconds` | histogram | — | Lookup latency. |

## `bitagent_classifier_llm_*` — LLM rerank stage (optional)

Only fires when the LLM stage is enabled and the inner CEL classifier returned `ErrUnmatched`.

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_classifier_llm_invocations_total` | counter | `result` | LLM invocation outcomes. `result` ∈ {`success`, `gated`, `error`}. |
| `bitagent_classifier_llm_cache_hits_total` | counter | — | Hits in the sha256 LRU cache. |
| `bitagent_classifier_llm_cache_misses_total` | counter | — | Misses (forced inference). |
| `bitagent_classifier_llm_duration_seconds` | histogram | — | End-to-end inference latency, including the gate chain. |
| `bitagent_classifier_llm_gates_total` | counter | `stage` | Per-gate rejections — `stage` ∈ {`config`, `inner_unmatched`, `plausibility`, `privacy`}. |

## `bitagent_retention_*` — retention pipeline

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_retention_examined_total` | counter | — | Torrents evaluated by the retention predicate. |
| `bitagent_retention_would_purge_total` | counter | — | Torrents that *would* be purged (dry-run signal). |
| `bitagent_retention_purged_total` | counter | — | Torrents actually deleted (only nonzero when `RETENTION_ENABLE_PURGE=true`). |
| `bitagent_retention_skipped_total` | counter | `reason` | Skip reasons — kept for operator transparency. |
| `bitagent_retention_run_duration_seconds` | histogram | — | Per-run pipeline latency. |

## `bitagent_csam_blocklist_*` — CSAM defense

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_csam_blocklist_prefetch_blocks_total` | counter | — | Pre-fetch rejects (the headline defense win — these never touched a swarm). |
| `bitagent_csam_blocklist_lookups_total` | counter | — | Lookups against the bloom filter. |
| `bitagent_csam_blocklist_feed_refresh_total` | counter | `feed`, `result` | Per-feed refresh outcomes. |
| `bitagent_csam_blocklist_feed_refresh_duration_seconds` | histogram | `feed` | Per-feed refresh latency. |
| `bitagent_csam_blocklist_feed_entries` | gauge | `feed` | Active entries from each feed. |
| `bitagent_csam_blocklist_entries` | gauge | — | Total bloom filter entries (sum of all feeds, deduplicated). |
| `bitagent_csam_blocklist_export_total` | counter | `result` | Per-export outcomes (local JSONL append + optional upstream POST). |

See [concepts/csam-defense.md](../concepts/csam-defense.md) for the full architecture.

## `bitagent_liveness_*` — torrent liveness

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_liveness_observations_total` | counter | `class` | Liveness observations per class. `class` ∈ {`suspect`, `live`, `dead`}. |
| `bitagent_liveness_blacklist_size` | gauge | — | Current size of the in-memory blacklist (seeders=0 for too long). |
| `bitagent_liveness_torznab_excluded_total` | counter | — | Torznab response items filtered out for liveness. |

## `bitagent_contentfilter_*` — content filter

Active when `CONTENT_FILTER_ENABLED=true` (shadow) or `..._ENFORCE=true` (apply).

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bitagent_contentfilter_examined_total` | counter | — | Torrents evaluated by the filter. |
| `bitagent_contentfilter_drop_total` | counter | `reason` | Drops by reason (`non_english`, `non_latin`, `blocked_ext`, `nsfw_keyword`, etc.). |

## Recommended dashboard panels

Queries below assume the `bitagent_*` namespace; rewrite the prefix if you're still on legacy.

- **Crawl health** — `rate(bitagent_dht_ktable_hashes_added_total[5m])`
- **Active DHT requests** — `sum(bitagent_dht_client_request_concurrency)` (proxy for DHT peer count)
- **DB size** — `bitagent_postgres_database_size_bytes`, `bitagent_postgres_table_size_bytes{table="torrents"}`, `...{table="torrent_contents"}`, `...{table="label_evidence"}`, `...{table="torrent_canonical_labels"}`
- **Evidence flow** — `rate(bitagent_evidence_events_persisted_total[5m])` by `source`, alongside `events_duplicated_total` + `events_rejected_total`
- **Canonical coverage** — `sum(bitagent_postgres_table_rows_estimate{table="torrent_canonical_labels"}) / sum(bitagent_postgres_table_rows_estimate{table="torrents"})` — what fraction of indexed torrents have a ground-truth label
- **Autovacuum health** — `bitagent_postgres_table_last_autovacuum_age_seconds` — alert if `> 86400` on a high-churn table
- **Dead tuple pressure** — `bitagent_postgres_table_dead_tuples / bitagent_postgres_table_live_tuples`
- **External source health** — `rate(bitagent_evidence_source_errors_total[5m])` by `source`, `stage`
- **Poll latency p95** — `histogram_quantile(0.95, sum by (le) (rate(bitagent_evidence_source_poll_duration_seconds_bucket[5m])))`

## Cardinality notes

The only label that grows with operator scale is `table` on `bitagent_postgres_*` metrics — bounded by the number of tables in the schema (currently ~25). All other labels are enumerated (e.g., `result`, `decision`, `class`, `source`, `stage`, `reason`) and have small bounded cardinality.

`feed` labels on `bitagent_csam_blocklist_*` metrics scale with the number of configured CSAM feeds — typically ≤ 5. Not a cardinality concern.

## Grafana dashboard

A pre-configured Grafana dashboard ships in the bitagent-core repo at `observability/grafana-dashboards/bitagent.json`. Import the JSON directly into your Grafana instance, point it at your Prometheus datasource, and the panels above render with sensible defaults.

## See also

- [operations/monitoring.md](../operations/monitoring.md)
- [configuration.md](../configuration.md)
- [deployment.md](../deployment.md)
- [concepts/csam-defense.md](../concepts/csam-defense.md)
