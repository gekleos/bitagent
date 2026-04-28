# Wants — Operator-Defined Search Targets

![Wants tab](assets/screenshots/tab-wants.png)

Wants are persistent search targets that tell BitAgent what content the operator actually cares about. Without wants, the DHT crawler is a fire-hose: it admits anything BEP-9 metadata gives it that the classifier doesn't reject. With wants, BitAgent's classifier biases admission, prioritises matching torrents in the Library view, and flags fresh hits in Recent Activity. Think of them as `*arr`-style quality profiles, but at the indexer layer instead of the downloader.

## Adding a Want

Click **Add Want** in the top-right of the Wants tab. The modal has four fields:

- **Title** — the human-readable label that appears in the table (e.g. *Breaking Bad S05E16*).
- **Query** — the lowercase free-text string the classifier matches against torrent names. Be specific: `breaking bad s05e16 ozymandias` matches one episode; `breaking bad` matches the entire series and is noisier.
- **Type** — one of `movie`, `tv_show`, `music`, `ebook`. Used to bias the right Torznab category back to the right `*arr`.
- **Priority** — slider 0-100 (default 50). Higher wins.

Query conventions:

- TV: `<show> s<NN>e<NN> [episode title]` — `severance s02 complete 1080p`
- Movies: `<title> <year> [resolution]` — `dune part two 2024 2160p`
- Music: `<artist> <album> [format]` — `pink floyd dark side moon flac`

## Priority Semantics

The priority scale is a 0-100 integer where **higher wins**. The classifier sorts active wants in descending priority order before evaluating any candidate.

Suggested bands:

| Range | Use it for |
| --- | --- |
| **90-100** | Episodes you're actively waiting on this week. The classifier admits matches almost unconditionally. |
| **70-89** | Currently airing or recently released series you're tracking. |
| **50-69** | Back-catalogue you're actively collecting. |
| **0-49** | Nice-to-have. Will benefit from passive crawling but won't crowd out higher-priority items. |

Don't overthink it — priority is a *bias*, not a strict ordering. The classifier still applies its quality and de-duplication rules; priority just resolves ties.

## Status Flow

Each want has a `status` of either `active` or `paused`.

- **active** — eligible for routing. Matching torrents are admitted, ranked, and flagged in Recent Activity.
- **paused** — preserved in the database but excluded from classifier scheduling. The row stays in the table, history stays intact, but no new matches accumulate against it.

Use **Pause** when a season finishes and you might rewatch later — keep the history, stop the indexing pressure. Use **Delete** only when you're sure you'll never want this content again; it's permanent.

## API Reference

All four CRUD operations are documented endpoints. The dashboard UI uses these same endpoints internally — anything you can do in the Wants tab you can script.

Set `DASHBOARD_API_KEY` in your environment, then:

### List wants

```bash
# All wants, default order (priority desc, created_at desc)
curl -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  https://bitagent.example.com/api/wants

# Filter to active TV-only wants
curl -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  "https://bitagent.example.com/api/wants?status=active&type=tv_show&limit=50"
```

### Create a want

```bash
curl -X POST https://bitagent.example.com/api/wants \
  -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Breaking Bad S05E16",
    "query": "breaking bad s05e16 ozymandias",
    "type": "tv_show",
    "priority": 95
  }'
```

The response is the full row including the auto-generated `id` and `created_at`.

### Update a want

```bash
# Drop priority + pause
curl -X PUT https://bitagent.example.com/api/wants/<id> \
  -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"priority": 60, "status": "paused"}'
```

Any subset of fields is accepted. Unset fields are left untouched.

### Delete a want

```bash
curl -X DELETE https://bitagent.example.com/api/wants/<id> \
  -H "Authorization: Bearer $DASHBOARD_API_KEY"
```

This is irreversible. Pause first if you might want it back.

## Wants vs Library

It's easy to conflate the two. The split:

- **Wants** are what you *want*. Forward-looking. Operator input.
- **Library** is what got *indexed*. Backward-looking. Crawler output.

A want is a target; the Library is the result of the classifier acting on the DHT firehose under that target's bias. You can have a want for content that hasn't been crawled yet — the want sits there waiting, and as soon as the DHT surfaces a matching infohash, the classifier admits it and it appears in the Library.

If you delete a want and the matching torrent is already in the Library, the Library entry stays — wants don't retroactively garbage-collect.

## Bulk operations

There's no bulk endpoint in v1.0.0. To bulk-load (e.g. seeding from a Sonarr "monitored" list), iterate POSTs from a script. The endpoint is idempotent on `(title, query)` — duplicate POSTs are silently de-duplicated, so retrying is safe.
