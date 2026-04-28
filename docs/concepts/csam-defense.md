# CSAM defense

> **Status:** Implemented and shipping. This page is the operator + reviewer guide.

## Our position

BitAgent indexes the public BitTorrent DHT. The DHT carries everything users put on it — and a small fraction of that is child sexual abuse material (CSAM). We treat that as a non-negotiable blocker, not a tradeoff.

Our goal is plainly stated:

> **A BitAgent operator should never participate in a CSAM swarm, even momentarily, and should never serve CSAM metadata to anyone, ever.**

No "we'll catch it post-fetch" handwave. No "log and ignore" middle ground. The architecture below exists to make that goal hold in practice, not just in policy.

## Why a post-fetch decision is too late

A typical DHT crawler discovers an infohash, then fetches the torrent's metadata over BEP-9 — a real TCP/uTP connection to a peer in the swarm — before it can read the title or file list and decide whether to keep it.

Peer-tracking services log every IP they see in a swarm. By the time a post-fetch classifier could reject CSAM, the operator's IP has already been recorded participating. For ordinary content this is fine; your IP appears in countless swarms. For CSAM it is not acceptable under any operational tradeoff.

The defense therefore has to fire **before** the metadata fetch.

## Why double-hash, not plaintext blocklists

A public list of plaintext CSAM infohashes would itself be a CSAM directory — it would tell anyone where to look. That can't ship.

A public list of **SHA-256-of-(SHA-1 infohash)** is one-way:

- Operators compute the same double-hash on every infohash they discover and check membership.
- Nobody can run the list backwards to find content.
- Two cooperating operators converge to the same blocklist without either of them ever exchanging plaintext infohashes.

This is the only credible shape for a public anti-CSAM blocklist for DHT crawlers, and it is what BitAgent ships.

## The pipeline

Every newly-discovered infohash flows through these stages, in order:

```text
DHT discovery
    │
    ▼
[1] Pre-fetch blocklist  ── community feeds (double-hashes)
    │   reject silently before any swarm-touching network call
    │   O(1) Bloom-filter-backed; default false-positive rate 0.1%
    │
    ▼
[2] Pre-fetch blocklist  ── this instance's own confirmed history
    │   anything we've previously confirmed locally is never re-fetched
    │
    ▼
[3] BEP-9 metadata fetch  ── only happens for everything else
    │   (defense-in-depth: a second blocklist check fires here in case a
    │    feed refresh added the hash mid-flight)
    │
    ▼
[4] CEL classifier  ── post-fetch, sees the title + file paths
    │   title or file path matching the banned-keyword regex
    │   produces an immediate hard delete
    │
    ▼
[5] Confirmed-CSAM observation  ── recorded as a one-way double-hash
        for this instance's future pre-fetch rejection (back to [2])
        and, if the operator opts in, contributed to a community feed
        as a seed for other instances' [1]
```

The key property: **once a confirmed-CSAM infohash exists in any feed an instance subscribes to, no operator running BitAgent ever touches the swarm.** The first instance globally to ever see a brand-new CSAM infohash still incurs one BEP-9 fetch; the defense converges as observations propagate.

## Honest limits

- **First observation per network.** The very first instance ever to discover a new CSAM infohash still does one BEP-9 fetch. The defense converges as observations propagate into community feeds — it does not eliminate that single first fetch globally.
- **Bloom filter false positives.** The default false-positive rate is 0.1% (`0.001`). At that rate, a non-CSAM infohash has a 1-in-1000 chance of being incorrectly rejected and never indexed by this instance. That is a curation miss, not a safety issue. Operators can tighten the FPR at the cost of memory.
- **Trust in feed sources.** A compromised or malicious feed could publish hashes that aren't actually CSAM. Operators are responsible for which feed URLs they configure. The instance exposes per-feed entry counts and refresh-outcome metrics so an anomalous feed (e.g. one suddenly flooding the blocklist) is visible.

## Wire format

Feeds are plain text, one entry per line:

```text
# This is a comment line.
# Anything after `#` is ignored to end-of-line.

de47c9b27eb8d300dbb5f2c353e632c393262cf06340c4fa7f1b40c4cbd36f90
0a1b2c3d...                       (64 lowercase hex chars)
```

- One double-hash per line, 64 lowercase hex characters (SHA-256 = 256 bits).
- Comment lines start with `#` (after optional whitespace).
- Blank lines are skipped.
- Non-conforming lines are counted as parse errors but do not abort ingest of the rest of the feed.
- Maximum body size defaults to 64 MiB (~1M entries); configurable via `CSAM_BLOCKLIST_FEED_MAX_BYTES`.

The double-hash function is **SHA-256 of the raw 20-byte SHA-1 infohash bytes** — not the hex-encoded string. Feeds using a different hash function will not match. The wire format is intentionally simple so that any compatible implementation, including any future upstream effort, can interoperate.

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

When the post-fetch classifier confirms CSAM (title or file paths matching the banned-keyword regex), one JSONL line is appended to `EXPORT_FILE_PATH`:

```json
{"ts":"2026-04-27T03:14:15.926Z","double_hash":"de47c9b2...","reason":"banned_keyword"}
```

The raw infohash is never written. The title and file paths are never written. The log itself is non-useful as a CSAM directory if it leaks: it has the same shape as a public feed.

If `EXPORT_UPSTREAM_URL` is set, the same JSON object is POSTed to the configured endpoint with `Content-Type: application/json` and the optional `Authorization` header. POST failures are counted and logged but do not affect the local append.

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
```

The operator should see `feed_entries{feed="localhost:18080/feed.txt"}=1` within a refresh interval.

## Reporting

If you discover that a BitAgent operator (yourself, or someone else's deployment) ever indexes or serves CSAM-classified content, please:

1. Open a private report via [GitHub Security Advisories](https://github.com/gekleos/bitagent/security/advisories/new) — see [SECURITY.md](../../SECURITY.md) at the repo root.
2. If the content involves a real-world identifiable victim, also report to the appropriate national authority (NCMEC in the US, IWF in the UK, INHOPE for other jurisdictions). Local-authority reporting is not optional regardless of what BitAgent's classifier did.

## See also

- [Configuration](../configuration.md) — `CSAM_BLOCKLIST_*` env vars
- [Operations / Security](../operations/security.md)
- [Reference / Metrics](../reference/metrics.md)
- [`SECURITY.md`](../../SECURITY.md) at the repo root — supported versions + threat model
