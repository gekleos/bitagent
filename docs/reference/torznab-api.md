# Torznab API Reference

BitAgent exposes a Newznab/Torznab-compatible feed at `/torznab/api`. The adapter follows the [Torznab spec 1.3 draft](https://torznab.github.io/spec-1.3-draft/), which is itself an extension of the Newznab API.

This page is the user-facing reference. For per-`*arr` setup walkthroughs see the [Integrations](../integrations/sonarr.md) section.

## Overview

| Property | Value |
|---|---|
| Base URL | `http://<host>:3333/torznab/api` |
| Auth | `apikey=<TORZNAB_API_KEY>` query parameter (required when env var is set) |
| Response format | RSS 2.0 XML with `<newznab:attr>` extensions |
| Spec source | <https://torznab.github.io/spec-1.3-draft/external/newznab/api.html> |

## Authentication

BitAgent gates `/torznab/api` on the `TORZNAB_API_KEY` environment variable.

- **Empty `TORZNAB_API_KEY`** — endpoint is open. Use only on a tailnet or behind a reverse proxy that adds its own auth.
- **Non-empty `TORZNAB_API_KEY`** — every request must include `apikey=<value>` as a query parameter. The compare is constant-time (timing-safe).

A failed auth returns Newznab error code `100` (`Incorrect user credentials`) with HTTP `401`:

```xml
<error code="100" description="Incorrect user credentials"/>
```

The key may also be supplied via the `Authorization: Bearer <value>` header on clients that prefer header auth.

## Functions (`t=`)

The Torznab function is selected with the `t` query parameter.

| `t` value | Purpose |
|---|---|
| `caps` | Capabilities document — supported functions, categories, attributes |
| `search` | Generic free-text search |
| `tvsearch` | TV episode/season search |
| `movie` | Movie search |
| `music` | Music album/artist search |
| `book` | Book / audiobook search |

## Search parameters

Each function accepts a different parameter set.

| Function | Common params | Identifier params |
|---|---|---|
| `search` | `q`, `cat`, `limit`, `offset` | — |
| `tvsearch` | `q`, `season`, `ep`, `cat`, `limit`, `offset` | `tvdbid`, `imdbid`, `tvmazeid`, `traktid` |
| `movie` | `q`, `cat`, `limit`, `offset` | `imdbid`, `tmdbid` |
| `music` | `q`, `artist`, `album`, `cat`, `limit`, `offset` | — |
| `book` | `q`, `author`, `title`, `cat`, `limit`, `offset` | — |

Notes:

- `cat` is a comma-separated list of Newznab category IDs.
- `limit` defaults to 50; clients should not set it above 200.
- `offset` is for pagination.
- Identifier params take precedence over `q`. A `tvdbid` lookup is more reliable than a free-text query.

## Newznab categories

BitAgent emits the standard Newznab category tree.

| ID | Category |
|---|---|
| 1000 | Console |
| 2000 | Movies |
| 2010 | Movies / Foreign |
| 2020 | Movies / Other |
| 2030 | Movies / SD |
| 2040 | Movies / HD |
| 2045 | Movies / UHD |
| 2050 | Movies / BluRay |
| 2060 | Movies / 3D |
| 3000 | Audio |
| 3010 | Audio / MP3 |
| 3020 | Audio / Video |
| 3030 | Audio / Audiobook |
| 3040 | Audio / Lossless |
| 3050 | Audio / Other |
| 4000 | PC |
| 5000 | TV |
| 5020 | TV / Foreign |
| 5030 | TV / SD |
| 5040 | TV / HD |
| 5045 | TV / UHD |
| 5050 | TV / Other |
| 5060 | TV / Sport |
| 5070 | TV / Anime |
| 5080 | TV / Documentary |
| 6000 | XXX |
| 7000 | Books |
| 7020 | Books / Comics |
| 7030 | Books / Magazines |
| 7040 | Books / Technical / eBook |
| 7050 | Books / Other |
| 7060 | Books / Foreign |
| 8000 | Other |

The classifier maps each indexed torrent to one or more of these IDs. The full mapping table is in `internal/torznab/categories.gen.go`.

## Response format

Successful responses are RSS 2.0 XML with `<newznab:attr name="..." value="..."/>` per-item attributes.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:newznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <title>BitAgent</title>
    <link>http://localhost:3333/torznab/api</link>
    <description>Self-hosted DHT indexer</description>
    <item>
      <title>Example Release Title (2025) 1080p WEB-DL</title>
      <guid isPermaLink="false">{infohash}</guid>
      <pubDate>Mon, 28 Apr 2026 12:00:00 +0000</pubDate>
      <enclosure url="magnet:?xt=urn:btih:..." length="123456789" type="application/x-bittorrent"/>
      <newznab:attr name="category" value="2040"/>
      <newznab:attr name="seeders" value="142"/>
      <newznab:attr name="peers"   value="158"/>
      <newznab:attr name="infohash" value="..."/>
      <newznab:attr name="magneturl" value="magnet:?xt=urn:btih:..."/>
      <newznab:attr name="size" value="123456789"/>
      <newznab:attr name="files" value="1"/>
      <newznab:attr name="grabs" value="0"/>
      <newznab:attr name="language" value="english"/>
      <newznab:attr name="coverurl" value="https://image.tmdb.org/t/p/w500/..."/>
    </item>
  </channel>
</rss>
```

The full attribute list emitted per item:

| Attribute | Source |
|---|---|
| `category` | classifier |
| `seeders` / `peers` | DHT swarm health |
| `infohash` | hex |
| `magneturl` | computed |
| `size` | BEP-9 metainfo |
| `files` | BEP-9 metainfo |
| `grabs` | evidence pipeline (count of `*arr` grab webhooks for this infohash) |
| `language` | classifier |
| `coverurl` | TMDB enrichment (only when `TMDB_API_KEY` is set and the title resolved) |

## Error codes

Errors follow Newznab error semantics.

| Code | Meaning |
|---|---|
| 100 | Incorrect user credentials |
| 200 | Missing parameter |
| 201 | Invalid parameter |
| 202 | Function not available |
| 203 | Search failed |
| 300 | No item found |
| 500 | Request limit reached |
| 900 | Unknown error |
| 910 | API disabled |

Error response shape:

```xml
<error code="200" description="Missing parameter (q)"/>
```

## Examples

Set the API key once for these examples:

```bash
export TORZNAB_API_KEY=<your_key>
```

**Capabilities:**

```bash
curl -s "http://localhost:3333/torznab/api?t=caps&apikey=$TORZNAB_API_KEY"
```

**TV episode by tvdbid (Game of Thrones, S01):**

```bash
curl -s "http://localhost:3333/torznab/api?t=tvsearch&tvdbid=121361&season=1&apikey=$TORZNAB_API_KEY"
```

**TV episode with explicit season + episode:**

```bash
curl -s "http://localhost:3333/torznab/api?t=tvsearch&q=breaking%20bad&season=5&ep=14&apikey=$TORZNAB_API_KEY"
```

**Movie by IMDb ID (Interstellar):**

```bash
curl -s "http://localhost:3333/torznab/api?t=movie&imdbid=tt0816692&apikey=$TORZNAB_API_KEY"
```

**Movie by TMDB ID:**

```bash
curl -s "http://localhost:3333/torznab/api?t=movie&tmdbid=157336&apikey=$TORZNAB_API_KEY"
```

**Music album:**

```bash
curl -s "http://localhost:3333/torznab/api?t=music&artist=Radiohead&album=In+Rainbows&apikey=$TORZNAB_API_KEY"
```

**Book / audiobook:**

```bash
curl -s "http://localhost:3333/torznab/api?t=book&author=Brandon+Sanderson&title=Mistborn&apikey=$TORZNAB_API_KEY"
```

**Free-text search with category filter:**

```bash
curl -s "http://localhost:3333/torznab/api?t=search&q=ubuntu&cat=4000&apikey=$TORZNAB_API_KEY"
```

## Limits and rate-limiting

BitAgent does not impose internal rate limits on `/torznab/api`. Concurrency is bounded only by Postgres connection pool size and CPU. For public-internet exposure, place a reverse proxy (Caddy, Traefik, NPM) in front and configure rate-limiting there.

The `*arr` clients respect Torznab `Retry-After` headers; you can shed load by returning `429` from your reverse proxy.

## Discovery

There is no Torznab service-discovery endpoint. Clients are expected to be configured with the base URL and API key directly.

## See also

- [Sonarr integration](../integrations/sonarr.md)
- [Radarr integration](../integrations/radarr.md)
- [Prowlarr integration](../integrations/prowlarr.md)
- [Lidarr integration](../integrations/lidarr.md)
- [Readarr integration](../integrations/readarr.md)
- [Configuration](../configuration.md)
- [GraphQL API reference](graphql-api.md)
