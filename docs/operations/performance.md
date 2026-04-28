# Performance tuning

BitAgent has three subsystems that matter for performance: the DHT crawler, Postgres, and (when enabled) the LLM rerank stage. This page gives concrete sizing guidance, the env vars that move the needle, and the metrics to watch.

Real measured numbers from the 2026-04-26 quality-evidence pass (see `HISTORY.md`) are at the bottom.

## Capacity sizing

Pick the row that matches your host. The numbers below are observed steady-state, not theoretical caps.

| Host class | `DHT_SCALING_FACTOR` | Indexed throughput | Suitable for |
|---|---|---|---|
| 4 GB / 2 vCPU | `1` | ~5–10 K torrents/day | Personal use, single `*arr` stack |
| 8 GB / 4 vCPU | `2`–`4` | ~20–40 K torrents/day | Household use, several `*arr` stacks |
| 16 GB / 8 vCPU | `4`–`8` | ~50–100 K torrents/day | Multi-user, larger media library |
| 32+ GB dedicated | `8`–`10` | 100 K+ torrents/day | Operator scale |

A few constants to size around:

- BitAgent steady-state RAM at `DHT_SCALING_FACTOR=10` is **~1.5 GB**.
- Postgres adds **200–500 MB** of cache depending on your `shared_buffers` setting.
- LLM stage cache (when enabled) adds **tens of MB** depending on cache hit ratio.
- Disk: 100 GB initial; grows ~5–15 GB/month at moderate scaling.

## DHT tuning

### What `DHT_SCALING_FACTOR` does

`DHT_SCALING_FACTOR` is a multiplier applied to internal worker counts: routing-table refresh workers, BEP-51 sample requesters, BEP-9 metainfo fetchers, classifier consumers. Higher = more concurrency = more throughput, more memory, more CPU, more network egress.

Default `1` is conservative and chosen so that `examples/docker-compose.public.yml` works on a small host without surprise OOMs. If you have headroom, you should raise it.

### When to bump

All of the following true:

- CPU usage `< 50%` (`docker stats`)
- Memory usage `< 50%` of allocated
- DHT peer count `> 100` and stable
- `bitagent_dht_client_request_duration_seconds` p95 `< 2s`

If the request duration p95 stays flat as you bump the scaling factor, you're not yet at saturation. Keep going.

### When to lower

Any of:

- Request duration p95 climbing past `5s`
- OOM kills in the container journal
- Postgres connection saturation (`bitagent_postgres_pgxpool_acquired / ..._total > 0.9`)

Back off one notch and re-measure.

## Postgres tuning

Postgres is the bottleneck on most disk-bound deployments. The default `postgres:16-alpine` image ships with conservative settings.

### Memory

```sql
-- 25% of host RAM for shared_buffers
ALTER SYSTEM SET shared_buffers = '4GB';   -- adjust for your host
-- 75% for effective_cache_size (a hint, not a hard alloc)
ALTER SYSTEM SET effective_cache_size = '12GB';
SELECT pg_reload_conf();
```

Apply via `psql -U bitmagnet bitmagnet`, then restart Postgres for `shared_buffers` to take effect.

### Autovacuum on high-churn tables

The two highest-churn tables are `torrents` (every metainfo fetch) and `label_evidence` (every `*arr` webhook). Tighter autovacuum thresholds keep them lean:

```sql
ALTER TABLE torrents          SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE label_evidence    SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE torrent_contents  SET (autovacuum_vacuum_scale_factor = 0.10);
```

Watch:

- `bitagent_postgres_table_dead_tuples / bitagent_postgres_table_live_tuples` — should stay `< 0.2`
- `bitagent_postgres_table_last_autovacuum_age_seconds{table="torrents"}` — alert if `> 86400` (24h)

### Indexes

The schema ships with the indexes BitAgent's queries actually use (`infohash`, `content_type`, `classification_timestamp`, the search GIN). Don't add custom indexes without first checking with `EXPLAIN ANALYZE` that they're load-bearing — extra indexes slow down writes.

## Disk I/O

SSD strongly recommended for the Postgres data volume. A spinning disk at 100K torrents/day will have autovacuum constantly behind the writes.

```bash
# Check Postgres data dir is on the SSD you think it is
docker exec bitagent-postgres df -h /var/lib/postgresql/data
```

## Network

DHT is outbound-dominant. Egress bandwidth is the floor on throughput:

- 1 Mbps egress: enough for `DHT_SCALING_FACTOR=1` only
- 10 Mbps: enough for `4–8`
- 100+ Mbps: enough for `10` and beyond

`BITAGENT_PEER_PORT` symmetry (inbound forwarded) helps BEP-9 fetch success rate but isn't required. Behind a VPN with port-forward, set the forwarded port to `BITAGENT_PEER_PORT` and you'll see modest gains.

## LLM stage tuning (when enabled)

The LLM rerank stage is opt-in and disabled by default. When enabled, the only knob most operators care about is the cache hit ratio.

Watch:

- `bitagent_classifier_llm_cache_hits_total / (hits + misses)` — should be `> 0.5` in steady state, often `> 0.8` with stable prompts
- `bitagent_classifier_llm_invocations_total{result="error"}` — should stay near zero

If your LLM provider rate-limits, the gate chain (`config → inner_unmatched → plausibility → privacy`) drops requests preemptively, so you don't hammer their API.

The LRU cache size is sized internally; tens of MB at typical traffic. The cache key includes `(model, prompt_version, title, file_list_hash, size_bucket)` so a model or prompt change invalidates everything cleanly.

## Reprocess

`bitagent reprocess` re-classifies already-indexed torrents through the current classifier. It can saturate CPU at high `DHT_SCALING_FACTOR`. Two patterns:

- **Background reprocess.** Lower `DHT_SCALING_FACTOR` to half its normal value, run reprocess in the background, restore on completion.
- **Off-hours reprocess.** Run during your low-load window. Watch `bitagent_classifier_examined_total` for progress.

## Memory accounting

Steady-state breakdown at `DHT_SCALING_FACTOR=10`:

| Component | Memory |
|---|---|
| BitAgent core | ~1.5 GB |
| Postgres `shared_buffers` | configured (typically 25% of host) |
| Postgres connection pool | ~50 MB |
| LLM cache (when enabled) | ~50 MB |
| `bitagent-ui` dashboard | ~150 MB |

Total: roughly `2 GB + shared_buffers`. On a 16 GB host with `shared_buffers=4G`, you're using ~6 GB and have headroom.

## Real measured numbers (2026-04-26)

From the quality-evidence pass shortly after the v1.17 release:

| Metric | Observed | Target |
|---|---|---|
| Throughput | 2,533 torrents/hr | — |
| Daily projection | 60,800 torrents/day | — |
| BEP-9 success rate | 3.23% | 8–15% |
| BEP-9 baseline (pre-tuning) | 2.3% | — |
| Wantbridge yield (Tier-0) | 2.07% | 30–50% |
| Operator grab share in Sonarr history | 38.2% (191/500) | — |

The BEP-9 success rate and wantbridge yield are active improvement targets. Numbers improve as the wantbridge layer matures and the LLM stage gets tuned.

## Profiling

For deeper investigation:

- **Go pprof** — when enabled in build, `/debug/pprof/profile` returns a CPU profile. Feed it to `go tool pprof`.
- **Postgres EXPLAIN** — for slow Torznab searches, capture the SQL with `LOG_LEVEL=debug` and run `EXPLAIN ANALYZE` against it.
- **Prometheus + Grafana** — your first stop, every time. The shipped Grafana dashboard has the panels that catch most issues.

## See also

- [Operations / Monitoring](monitoring.md)
- [Operations / Backup-restore](backup-restore.md)
- [Configuration](../configuration.md) — every env var that matters here
- [Reference / Metrics](../reference/metrics.md)
- [Concepts / DHT crawler](../concepts/dht-crawler.md) — for `DHT_SCALING_FACTOR` semantics
