# CSAM defense

> **Status:** Implemented and shipping. This document is the operator + reviewer guide; design rationale lives in `internal/csamblocklist/doc.go` in the bitagent core repo.

## The problem

A standard DHT crawler discovers infohashes via DHT `get_peers` / `announce_peer` traffic, then fetches the torrent's metadata via the BEP-9 extension protocol over a real TCP/uTP connection to a peer claiming to seed the content. Only after the metadata fetch can the classifier inspect the title and file paths and decide to drop the torrent.

That post-fetch decision is too late for one specific concern. Peer-tracking services (e.g. "I know what you download") record every IP they see participating in a swarm. By the time the classifier has the title, the operator's IP has already been seen connecting to the swarm. For most content this is fine — your IP appears in countless swarms — but for **CSAM** it is not acceptable under any operational tradeoff.

The community discussion (originally [bitmagnet-io/bitmagnet#494](https://github.com/bitmagnet-io/bitmagnet/issues/494)) settled on a **double-hashed public blocklist** as the only credible defense:

- A public list of plaintext CSAM infohashes would itself be a directory of CSAM. Distributing such a list is harmful.
- A public list of **SHA-256-of-(SHA-1 infohash)** is one-way: receivers can compute the same double-hash on every infohash they discover and reject matches; nobody can run the list backwards to find content.

This is the defense BitAgent implements.

## Layered defense

In execution order on every newly-discovered infohash:

```text
DHT discovery
    │
    ▼
[1] csamblocklist.Manager.Filter ─── community-feed double-hashes
    │   reject pre-fetch
    │
    ▼
[2] BlockingManager.Filter ─── this instance's own observations
    │   reject pre-fetch
    │
    ▼
[3] BEP-9 metadata fetch ─── the swarm-touching network call
    │   (defense-in-depth: csamblocklist.IsBlocked re-checks here
    │   in case a feed refresh introduced the hash after triage)
    │
    ▼
[4] CEL classifier ─── post-fetch, sees the title + files
    │   `keywords.banned` regex → ErrDeleteTorrent
    │
    ▼
[5] processor → BlockingManager.Block ─── feed observation back
    │   into [2] for this instance's future filtering
    │
    ▼
[6] csamblocklist.Exporter.Record ─── re-checks banned-keyword regex,
        appends double-hash to local JSONL log,
        optional POST to community upstream
        (closes the loop: this instance's observation
         is published as a community-feed seed, so other
         instances catch the hash at [1] going forward)
```text
## Honest limits

- **First observation across the network** still incurs one BEP-9 fetch per network. The defense converges as observations propagate into community feeds — it does not eliminate.
- **Bloom filter false positives** can reject a non-CSAM infohash that collides with a feed entry. With the default FPR of `0.001` and feeds in the 1k–100k range, the practical FP rate is very low. An FP causes one infohash to never be indexed by this instance — not a safety issue, just a curation miss. Operators can lower FPR at the cost of memory.
- **Compromised feeds** could publish hashes that aren't actually CSAM. Operators are responsible for the trust they place in any feed URL they configure. The package exposes `feed_refresh_total{outcome}` and per-feed `feed_entries` metrics so an operator can spot a feed flooding the blocklist.

## Wire format

Feed body is plain text, one entry per line:

```text
# This is a comment line.
# Anything after `#` is ignored to end-of-line.

de47c9b27eb8d300dbb5f2c353e632c393262cf06340c4fa7f1b40c4cbd36f90
0a1b2c3d...                       (64 lowercase hex chars)
```text
- One double-hash per line, `64` lowercase hex chars (SHA-256 = 256 bits).
- Comment lines start with `#` (after optional whitespace).
- Blank lines are skipped.
- Non-conforming lines are counted as parse errors but do not abort ingest of the rest of the feed.
- Maximum body size defaults to 64 MiB (~1M entries); configurable via `CSAM_BLOCKLIST_FEED_MAX_BYTES`.

The double-hash function is **SHA-256 of the raw 20-byte SHA-1 infohash bytes** — not the hex-encoded string. Feeds using a different hash function will not match.

## Operator config

All variables are env-prefix `CSAM_BLOCKLIST_*`:

| Variable | Default | Meaning |
|---|---|---|
| `ENABLED` | `true` | Master switch. `false` makes the package a NoOp. |
| `FEED_URLS` | *(empty)* | Comma/space-separated feed URLs. Empty = NoOp. |
| `FEED_REFRESH_INTERVAL` | `6h` | How often to re-poll all feeds. |
| `FEED_FETCH_TIMEOUT` | `30s` | Per-feed HTTP timeout. |
| `FEED_MAX_BYTES` | `67108864` | Per-feed body cap (64 MiB). |
| `BLOOM_CAPACITY` | `1000000` | Bloom filter capacity. |
| `BLOOM_FALSE_POSITIVE_RATE` | `0.001` | Target FPR. |
| `EXPORT_ENABLED` | `true` | Self-export of confirmed observations. |
| `EXPORT_FILE_PATH` | `data/csam-double-hashes.jsonl` | Local JSONL log path. |
| `EXPORT_UPSTREAM_URL` | *(empty)* | Optional outbound POST endpoint. |
| `EXPORT_UPSTREAM_AUTH_HEADER` | *(empty)* | Full `Authorization` header value. |
| `EXPORT_UPSTREAM_TIMEOUT` | `10s` | Per-POST timeout. |

### Recommended starting profile

- `CSAM_BLOCKLIST_ENABLED=true` (default)
- `CSAM_BLOCKLIST_FEED_URLS=` — opt into a feed when one becomes available you trust
- `CSAM_BLOCKLIST_EXPORT_ENABLED=true` (default) — local log only
- `CSAM_BLOCKLIST_EXPORT_UPSTREAM_URL=` — leave empty until a community collection endpoint exists you want to contribute to

## Metrics

All under namespace `bitagent_csam_blocklist_`:

- `prefetch_blocks_total` — counter. Hashes rejected pre-fetch.
- `lookups_total` — counter. Total hot-path lookups.
- `feed_refresh_total{feed,outcome}` — counter. `outcome=success|error`.
- `feed_refresh_duration_seconds{feed}` — histogram.
- `feed_entries{feed}` — gauge. Per-feed entry count.
- `entries` — gauge. Total entries across all feeds.
- `export_total{outcome}` — counter. `outcome=local_ok|local_err|upstream_ok|upstream_err|skipped_no_match`.

See [reference/metrics.md](../reference/metrics.md) for the catalogue context.

## Self-export observation log

When the post-fetch CEL classifier emits `ErrDeleteTorrent` AND the title or file paths match the banned-keyword regex, one JSONL line is appended to `EXPORT_FILE_PATH`:

```json
{"ts":"2026-04-27T03:14:15.926Z","double_hash":"de47c9b2...","reason":"banned_keyword"}
```text
The raw infohash is never written. The title and file paths are never written. The log itself is non-useful as a CSAM directory if it leaks: it is the same shape as a public feed.

If `EXPORT_UPSTREAM_URL` is set, the same JSON object is POSTed to the configured endpoint with `Content-Type: application/json` and the optional `Authorization` header. POST failures are counted + logged but do not affect the local append.

## Testing the wiring

A minimal end-to-end smoke test (operator-side):

```bash
# Stand up a one-shot feed
mkdir -p /tmp/csamfeed
cat > /tmp/csamfeed/feed.txt <<EOF
# test feed
de47c9b27eb8d300dbb5f2c353e632c393262cf06340c4fa7f1b40c4cbd36f90
EOF
python3 -m http.server -d /tmp/csamfeed 18080 &

# Configure bitagent
CSAM_BLOCKLIST_FEED_URLS="http://localhost:18080/feed.txt" \
  ./bitagent worker run --all

# Watch metrics
curl -s localhost:3333/metrics | grep csam_blocklist
```text
The operator should see `feed_entries{feed="localhost:18080/feed.txt"}=1` within a refresh interval.

## Relationship to upstream

The original issue is open at `bitmagnet-io/bitmagnet#494`. As of the BitAgent fork (2026-04-24), there is no upstream movement on the proposal. This is BitAgent's independent implementation. If upstream later ships a compatible mechanism, the wire format is intentionally simple (plain-text lowercase hex, one per line) so feed compatibility is likely.

## See also

- [Configuration](../configuration.md) — `CSAM_BLOCKLIST_*` env vars
- [Operations / Security](../operations/security.md)
- [Reference / Metrics](../reference/metrics.md)
- `SECURITY.md` at the repo root — supported versions + threat model
