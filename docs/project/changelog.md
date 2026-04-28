# Changelog

Release history for BitAgent. Newest first. The longer-form decision log lives in [`HISTORY.md`](https://github.com/gekleos/bitagent/blob/main/HISTORY.md) at the repo root.

## v1.0.0 — 2026-04-28 — First public release

The first publicly-shipped BitAgent release. Sidebar UI complete, real-data integration verified, MIT licensed, documentation site live.

- Sidebar UI shipped (Dashboard / Library / Wants / Evidence / Settings / System tabs)
- Real-data integration verified (3M+ torrents indexed, 325 DHT peers, full category breakdown across audiobook / ebook / movie / music / tv_show)
- 14 doc guides + screenshots pushed
- `gekleos/bitagent` on GitHub goes public, MIT licensed
- Pages site live at <https://gekleos.github.io/bitagent/>

**Highlights.** This is the cut where BitAgent transitions from advanced tooling to a public release. The dashboard's six-tab sidebar layout, the public-quickstart compose file, and the docs site all date from this version.

## v1.17 — 2026-04-26 — Quality evidence baseline

Production-deployed cut where the first end-to-end quality measurements were captured. Used as the reference baseline for the BEP-9 and wantbridge improvement workstreams.

- 60 K/day classified throughput
- 2,533 torrents/hr indexer rate
- BEP-9 success rate 3.2% (improvements roadmap targets 8–15%)
- TMDB-classified content; FP fix verified

**Highlights.** Quality numbers shipped a week of stability after the v1.1.0 features (preempt + retention + LLM stage) had time to compound on real data.

## v1.1.0 — 2026-04-21 — Classifier preempt + retention + LLM stage

Four large branches landed in one cut. Defaults are conservative; live-apply flags are off. Deploy-and-observe was the explicit posture.

- **Canonical-label preempt** (`internal/classifier/runner_canonical.go`) — short-circuits the CEL chain when a ground-truth label exists from `*arr` evidence. New metrics `bitagent_classifier_preempt_*`.
- **Retention pipeline** (`internal/retention`) — two-layer opt-in (`Enabled` + `EnablePurge`), conservative predicate (no canonical, no evidence, > 60 days old, every source reports `seeders=0`). New metrics `bitagent_retention_*`.
- **LLM rerank stage** (`internal/classifier/llmstage`) — fallback after CEL `ErrUnmatched`. Two-layer opt-in (`Enabled` + `EnableLive`). Aggressive gate chain (config → inner-unmatched → plausibility → privacy). sha256 LRU cache. Strict JSON `{category, confidence}` response. New metrics `bitagent_classifier_llm_*`.
- **Ops contract** (`ops/CARDS.md`, `ops/client.py`, `ops/promql.yml`) — lifted the dashboard interface contract out of the core repo so the dashboard could iterate independently.

**Highlights.** This cut is where BitAgent diverged irreversibly from upstream — the preempt + LLM stage architecture has no upstream equivalent.

## Pre-rebrand divergence

Below are the change sets that landed under the old `bitmagnet` name during the fork-establishment + divergence phase. Retained for context; not actionable for upgraders.

### 2026-04-24 — Phase 2 rebrand: Prometheus namespace

Metric namespace migrated from `bitmagnet_*` to `bitagent_*` with a dual-emit window so legacy dashboards keep working.

- New package `internal/telemetry/dualemit` provides drop-in replacements for `prometheus.NewCounterVec` / `NewGaugeVec` / `NewHistogramVec` and their scalar counterparts. Each constructor creates two collectors, one per namespace; every `Observe` / `Inc` / `Set` is teed.
- All call sites migrated: `pgstats`, `evidence`, `retention`, `dht/ktable`, `dht/server`, `dht/responder`, `dht/client`, `metainforequester`, `externalip`, `classifier/llmstage`, `classifier/runner_canonical`, `dhtcrawler`.
- Downstream migrated in lockstep: Grafana dashboard, PromQL ops contract, deploy README panel list.
- `dualemit.EmitLegacy` defaults to `true`. Flipping to `false` ends the dual-emit window — a one-line change with no call-site touch.

**Cost.** ~2× map lookups + atomic increments per observation. Negligible vs the DHT socket and DB write that dominate the request path.

### 2026-04-24 — Rebrand: gekleos/bitmagnet → gekleos/bitagent

- Go module path: `github.com/bitmagnet-io/bitmagnet` → `github.com/gekleos/bitagent`
- Binary name: `bitmagnet` → `bitagent`
- DHT client ID suffix on the wire: `-BM0001-` → `-BA0001-`
- CLI app name flip
- `UPSTREAM_DIFF.md` → `HISTORY.md`
- Container registry path stays `gekleos/bitmagnet` due to GitLab refusing project rename when the registry is non-empty (would have destroyed 13 historical image tags). Build artefact is a BitAgent binary; only the storage path keeps the legacy name.

**Deliberately not changed in Phase 1.** Postgres default DB name (`bitmagnet`), XDG config path (`~/.config/bitmagnet/config.yml`), and protobuf internal package name. All have separate-migration cost reasons.

### 2026-04-20 — Strip Angular webui + Jekyll docs

Removed the upstream-shipped Angular webui and the Jekyll-based marketing site. The dashboard moved to a separate FastAPI app; docs moved to MkDocs.

- Deleted `webui/`, `internal/webui/`, `bitmagnet.io/`, `graphql/` (TS client codegen).
- `internal/app/appfx/module.go` no longer imports or registers `webui.New`.
- Binary size: 63.4 MB → 58.0 MB.

### 2026-04-20 — Add `pgstats` Prometheus collector

- New package `internal/database/pgstats` + `internal/database/pgstats/pgstatsfx`.
- 14 new metrics scoped `bitmagnet_postgres_*` (now `bitagent_postgres_*`): database size, per-table size / rows-estimate / dead-tuples / autovacuum-age / analyze-age, connection-state breakdown, pgx pool utilisation.
- Scrape-driven; 5 s per-scrape timeout.
- Registered into the shared `prometheus_collectors` fx group.

### 2026-04-20 — Add evidence ingestor

- New migration `00021_label_evidence.sql` — `label_evidence` and `torrent_canonical_labels` tables.
- New package `internal/evidence` + submodules `store`, `sources/arrwebhook`, `sources/qbpoller`, `sources/arrpoller`, `evidencefx`.
- New config section `evidence` in `configfx`.
- Exposes `POST /evidence/arr/:instance` webhook endpoint (shared-secret auth via `X-Evidence-Token`).
- Worker registry gains `evidence_qb_poller` and `evidence_arr_poller`.
- Metrics scoped `bitmagnet_evidence_*` (now `bitagent_evidence_*`).

**Design premise.** Canonical labels preempt the classifier entirely; the classifier runs only when no authoritative label exists for a given infohash. Classifier integration landed in the v1.1.0 cut.

### 2026-04-20 — Fork established

- Base: commit `2b9e8ea` (2025-07-01 upstream) plus all subsequent main-branch commits and tags through `v0.10.0`.
- Upstream went dormant 2025-07-01 (last `main` commit).
- The fork is now independent. The `upstream` remote remains configured for ad-hoc reference (security-fix surveillance) but imports are no longer on a schedule.

## Lineage

BitAgent is a 2026 fork of [bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet), base commit `2b9e8ea` (2025-07-01). After 9+ months of upstream dormancy, "fork" framing was no longer accurate; on 2026-04-24 the project rebranded to BitAgent and pursues an independent roadmap. The DHT primitives and core indexing engine were carried forward; everything above the classifier line is divergent.
