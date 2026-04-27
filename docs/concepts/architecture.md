# Architecture

## System overview

BitAgent is a self-hosted indexer engineered for high-throughput metadata correlation and torrent discovery. The runtime splits across two repos: the Go core (`gekleos/bitagent`), which owns the indexing engine, networking stack, and protocol adapters; and the Python dashboard (`gekleos/bitagent-ui`), which handles operator configuration, monitoring, and posters.

The core operates as a stateful indexing service that bridges external client suites (Sonarr/Radarr/Prowlarr/Lidarr), exposes a GraphQL API, and persists discovered assets to PostgreSQL. The dashboard is a thin presentation layer communicating with the GraphQL API and a local SQLite sidecar for operator overrides + audit log + poster cache.

BitAgent is a 2026 fork of upstream `bitmagnet-io/bitmagnet` (which went dormant July 2025). We carried forward the DHT primitives and core indexing engine; we diverged with a redesigned classification pipeline, decoupled evidence ingestion, multi-tier auth, settings-write infrastructure, and stricter runtime boundaries.

## Architecture diagram

```mermaid
flowchart LR
  Clients["*arr suite (Sonarr/Radarr/Prowlarr/Lidarr)"]
  Torznab["Torznab adapter"]
  Core["BitAgent core (Go)"]
  DHT["DHT crawler<br/>(BEP-5/9/10/33/42/43/51)"]
  CEL["CEL classifier"]
  LLM["optional LLM rerank"]
  PG[("Postgres<br/>(schema_versions table)")]
  GQL["GraphQL API"]
  UI["bitagent-ui<br/>(Python FastAPI)"]
  Webhook["evidence webhook"]
  TMDB["TMDB<br/>(poster art, optional)"]
  SQL[("SQLite sidecar<br/>(overrides + audit + posters)")]

  Clients --> Torznab
  Torznab --> Core
  Core --> DHT
  Core --> CEL
  CEL --> LLM
  Core <--> PG
  Core --> GQL
  GQL --> UI
  Clients --> Webhook
  Webhook --> Core
  UI <--> TMDB
  UI <--> SQL
```

## Component walkthrough

**DHT crawler** — Strict compliance with BEP-5, BEP-9, BEP-10, BEP-33, BEP-42, BEP-43, BEP-51. Maintains a dynamic peer table sized to available RAM; bootstraps from a deterministic node list with DHT fallback after the first gossip cycle. Periodically refreshes the routing table and applies exponential backoff during failure bursts. UDP sockets bind to ephemeral ranges; packet TTLs limit DHT amplification.

**Torznab adapter** — Protocol boundary for the *arr ecosystem. Implements the full Torznab caps endpoint, exposing supported search modes (`tv-search`, `movie-search`, `music-search`, `book-search`) and category mappings aligned with Newznab standards. Validates `TORZNAB_API_KEY` per request via constant-time compare; rate limits per client; serves XML responses with full metadata.

**CEL classifier** — Evaluates torrent metadata against a compiled CEL policy. Rules execute in a deterministic priority order; a high-confidence ground-truth match (from the evidence pipeline) preempts the rule chain entirely. When the rule chain is exhausted without a definitive label, an optional LLM rerank gate triggers and feeds structured metadata to a model for semantic disambiguation. Final score is cached and indexed for GraphQL exposure.

**Evidence pipeline** — Ingests webhook payloads from Sonarr/Radarr (`POST /evidence/arr/<instance>`). Successful download events propagate ground-truth labels backward to the originating evidence record; failures apply penalty weights. The pipeline deduplicates rapid bursts, normalises timestamp formats across *arr versions, and runs asynchronously to keep webhook latency low.

**Postgres data layer** — Managed via GORM. Schema versions tracked in a `schema_versions` table; migrations are forward-only. Core tables: `torrents` (global asset registry), `releases` (versioned metadata snapshots), `evidence` (webhook events), `wants` (operator-defined search targets). Indexes optimise lookups on infohash, category, and classification timestamp.

**GraphQL API** — Primary query surface. Authenticated at the middleware layer with scoped tokens. Common queries: `searchTorrents`, `getReleaseDetails`, `listEvidenceEvents`, `updateWants`. Resolvers fetch from cache or Postgres and apply real-time classification adjustments before serializing.

**bitagent-ui** — FastAPI + vanilla-JS frontend. The 4-tier auth resolver (api-key → reverse-proxy headers → forwarded-user → SSO cookie) gates every endpoint. Read-only relative to BitAgent core: never mutates indexing data. All data fetches route through the GraphQL API.

**Settings persistence** — SQLite sidecar at `/data/bitagent-ui.db`. A custom `pydantic-settings` source reads runtime overrides first, falling back to env, then defaults. Every change writes an audit row (key, old, new, actor, timestamp). Hot-reload on the next request — no process restart needed.

## Why two repos

`bitagent` (Go) owns indexing, DHT networking, classification, and persistence — built for performance and strict concurrency. `bitagent-ui` (Python) contains only the dashboard, FastAPI routing, and SQLite sidecar — optimised for rapid iteration and developer ergonomics.

A hard scope boundary: `bitagent-ui` is read-only relative to BitAgent state. It never mutates indexing data, triggers crawls, or rewrites classifier rules directly. All structural changes flow through the GraphQL API, ensuring auditability and preventing cross-component drift.

Independent release cadences. The dashboard ships UI fixes in days; the indexer engine ships protocol/correctness fixes on its own clock.

## Data flow examples

**Torrent discovered via DHT.** The crawler resolves an announce, fetches metainfo via BEP-9 from peers, hands the parsed metadata to the CEL classifier. Rules evaluate; ground-truth-evidence preempts; if unresolved, the optional LLM gate runs. The core persists to Postgres, updates `releases`, exposes via GraphQL. On Torznab query, the adapter assembles the magnet URI and metadata response.

**Sonarr requests an episode.** Sonarr's poll triggers `GET /torznab?t=tvsearch&q=...&season=...&ep=...&apikey=$KEY`. The adapter normalises params and queries the core's search graph against Postgres. Results are ranked by classifier confidence + evidence score + release freshness. Top matches serialise to Torznab XML; Sonarr selects, downloads, and emits an evidence webhook closing the feedback loop.

**Operator changes a setting.** Dashboard form → `PUT /api/settings/overrides/<key>` (auth required). FastAPI validates the field is in the `MUTABLE_FIELDS` allowlist, writes to SQLite, appends an audit row. Next request reads the override via the custom `pydantic-settings` source — no restart.

