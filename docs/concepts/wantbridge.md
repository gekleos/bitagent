# Wantbridge

Wantbridge is BitAgent's active-acquisition layer. Standard DHT crawlers are passive — they index whatever the network gossips. Wantbridge inverts that: it takes the list of things your `*arr` clients are *actively searching for* and biases the crawler toward finding those.

It is not magic. Wantbridge cannot create torrents that don't exist on the DHT; it just shortens the latency between "the DHT has it" and "BitAgent has indexed it". For new shows being crawled cold, that latency reduction is the difference between a Sonarr search returning results today vs. tomorrow.

## How wants enter the system

Two paths feed the wants table.

**Operator-defined.** You add a Want via the dashboard's [Wants tab](../wants.md) — "TV: Game of Thrones, S08, priority 100". This is the explicit knob; use it for high-value targets you want the crawler to chase aggressively.

**Auto-derived from `*arr` queries.** When Sonarr asks for `tvsearch?tvdbid=121361&season=8&ep=6`, the request is recorded as an implicit want for that show + season + episode. Same for Radarr movie searches and Lidarr album searches. Most operators get useful wantbridge behaviour without ever touching the Wants tab — the auto-derivation does the work.

Wants have a TTL: auto-derived wants age out after a week of `*arr` not asking for them. Operator-defined wants persist until you remove them.

## How wantbridge biases the crawler

Three levers, all in the same direction.

**DHT request biasing.** When the crawler issues `sample_infohashes` calls, it preferentially walks routing-table neighbourhoods that have historically yielded torrents matching active wants. Newly-discovered infohashes from those neighbourhoods get higher initial priority.

**BEP-9 fetch queue priority.** When a candidate infohash passes the pre-fetch filters (CSAM blocklist, classifier early-rejects), it goes into the BEP-9 fetch queue. Wantbridge reorders the queue so candidates *likely* to match an active want jump to the front. The likelihood signal is conservative — title regex match against the want, mostly — so it's a soft preference, not a hard skip of non-matches.

**Classifier priority lane.** Once metadata is fetched, the classifier processes a high-priority lane for wantbridge-matched torrents. They reach the Library and the Torznab feed milliseconds-to-seconds faster than background traffic.

The net effect: when Sonarr asks for an episode that BitAgent's DHT crawler is *about* to discover, wantbridge can collapse "discovery → indexed → searchable" from minutes to seconds.

## What wantbridge does NOT do

Worth being explicit:

- **It does not create torrents that don't exist on the DHT.** No DHT presence, no wantbridge magic.
- **It does not bypass the classifier or quality filters.** A wantbridge match still has to pass CEL rules and quality gates. Wants don't override curation.
- **It does not retroactively re-rank already-indexed torrents.** Adding a Want today doesn't rewrite history. For an existing torrent corpus, your `*arr` searches already find what's there. Wantbridge only changes what gets indexed *next*.
- **It does not affect Torznab response ordering.** Search ordering is based on classifier confidence + evidence score + freshness. Wants don't promote results.

## Status quo (as of v1.0.0)

Wantbridge is shipped but young. From the 2026-04-26 quality evidence pass:

- **Tier-0 wantbridge yield: 2.07%.** Target range: 30–50%. The current matching is too conservative, and the auto-derivation pipeline is biased toward Sonarr.
- **Source distribution: Sonarr 50, Radarr 0, Lidarr 0.** Sonarr's webhook + history-poll cadence is the only fully-wired feed today; Radarr and Lidarr are plumbed but their auto-derivation is still being tuned.

This is the focus area for the next minor release. The infrastructure works (wants land, biasing applies, the classifier priority lane fires); the heuristics that decide *what* to bias on need work. Improvements being tracked:

- Wider matching (currently regex-strict; switching to weighted tokens).
- Radarr + Lidarr auto-derivation parity with Sonarr.
- Per-show / per-album recency weighting (recent grabs > stale wants).

## Inspecting wantbridge

The dashboard exposes wantbridge state in three places.

- **Wants tab** — the operator-defined wants list. Add, edit, delete, prioritise. See [docs/wants.md](../wants.md).
- **Dashboard tab** — `wantbridge_yield_pct` is a top-line metric.
- **Library tab** — filter to "wantbridge-matched" to see what the system pulled in because of an active want.

Programmatic inspection via GraphQL is on the roadmap; for now, the dashboard is the canonical surface.

## Honest expectations

If you're new to BitAgent and wondering whether to tune wantbridge: don't, yet. Get the basic crawler running, let it index for a few days, and see whether your `*arr` searches return results. If they do, wantbridge is doing its job invisibly. If they don't, the gap is more likely a DHT or classifier issue than a wantbridge tuning question — go to [troubleshooting.md](../troubleshooting.md) first.

If you're an operator chasing a specific high-value title that BitAgent doesn't seem to find, *that* is a wantbridge tuning candidate: add an operator-defined want with priority 100 and see whether the crawl picks it up over the next 24 hours.

## See also

- [Wants tab guide](../wants.md)
- [Concepts / Classification](classification.md) — how matched torrents flow through the priority lane
- [Project / Improvements](../project/improvements.md)
- [Troubleshooting](../troubleshooting.md)
