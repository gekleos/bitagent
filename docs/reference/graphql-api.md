# GraphQL API reference

BitAgent exposes a GraphQL endpoint at `:3333/graphql`. The schema is generated from `internal/gql/gqlgen.yml` via [gqlgen](https://github.com/99designs/gqlgen) and supports full introspection.

## Overview

| Property | Value |
|---|---|
| Endpoint | `POST http://<host>:3333/graphql` |
| Playground | `GET http://<host>:3333/graphql` (renders the gqlgen playground) |
| Auth | none by default — front with a reverse proxy for public exposure |
| Schema introspection | enabled |

Tools that work out of the box: Altair, Insomnia, Bruno, IntelliJ HTTP client, the gqlgen playground.

## Top-level Query fields

| Field | Type | Purpose |
|---|---|---|
| `torrent` | `TorrentQuery` | Torrent-centric reads — files, sources, metrics, tag suggestions |
| `torrentContent` | `TorrentContentQuery` | Search across enriched content (movies / TV / music / books) |
| `queue` | `QueueQuery` | Queue / job state |
| `workers` | `WorkersQuery` | Worker registry |
| `health` | `HealthQuery` | DB / queue / torrent health |

### `TorrentQuery` fields

| Field | Returns | Purpose |
|---|---|---|
| `files(input)` | `TorrentFilesQueryResult` | List files for given infohashes |
| `listSources()` | `TorrentListSourcesResult` | Distinct torrent sources known to the indexer |
| `metrics(input)` | `TorrentMetricsQueryResult` | Bucketed counts over time |
| `suggestTags(input)` | `TorrentSuggestTagsResult` | Tag suggestions for filtering |

### `TorrentContentQuery` fields

| Field | Returns | Purpose |
|---|---|---|
| `search(input: TorrentContentSearchQueryInput)` | `TorrentContentSearchResult` | Primary search |

`TorrentContentSearchResult` shape:

| Field | Purpose |
|---|---|
| `items` | The matched torrent-content rows |
| `totalCount` | Estimated or exact count, see next field |
| `totalCountIsEstimate` | If `true`, `totalCount` came from a planner estimate |
| `hasNextPage` | True when `offset+limit` < `totalCount` |
| `aggregations` | Facet counts: `contentType`, `language`, `releaseYear`, `torrentFileType`, `torrentSource`, `torrentTag`, `videoResolution`, `videoSource` |

## Common queries

### Search torrents by free text

```graphql
query Search {
  torrentContent {
    search(input: { queryString: "the matrix", limit: 25 }) {
      items {
        infoHash
        title
        contentType
        publishedAt
        torrentSource
      }
      totalCount
      hasNextPage
    }
  }
}
```

### Category facet counts (no item rows)

Useful for the dashboard sidebar and for cardinality probes.

```graphql
query Facets {
  torrentContent {
    search(input: { queryString: "matrix", limit: 0 }) {
      totalCount
      aggregations {
        contentType {
          value
          label
          count
          isEstimate
        }
      }
    }
  }
}
```

### List the 10 most-recent torrents

```graphql
query MostRecent {
  torrentContent {
    search(input: { limit: 10, orderBy: { field: published_at, descending: true } }) {
      items {
        infoHash
        title
        publishedAt
      }
    }
  }
}
```

### Files for a specific infohash

```graphql
query Files {
  torrent {
    files(input: { infoHashes: ["a1b2c3d4e5f67890123456789012345678901234"] }) {
      items {
        infoHash
        path
        size
        index
        extension
        fileType
      }
    }
  }
}
```

### Health check

```graphql
query Health {
  health {
    db
    queue
    torrent
  }
}
```

### Worker list

```graphql
query Workers {
  workers {
    listAll {
      workers {
        key
        started
      }
    }
  }
}
```

## Top-level Mutation fields

| Field | Type | Purpose |
|---|---|---|
| `torrent` | `TorrentMutation` | Torrent management — delete / tag / reprocess |
| `queue` | `QueueMutation` | Queue management — purge / enqueue reprocess batches |

### `TorrentMutation` fields

| Field | Args | Returns |
|---|---|---|
| `delete` | `infoHashes: [Hash20!]!` | `Boolean!` |
| `setTags` | `infoHashes, tagNames` | `Boolean!` |
| `putTags` | `infoHashes, tagNames` | `Boolean!` (additive) |
| `deleteTags` | `infoHashes, tagNames` | `Boolean!` |
| `reprocess` | `input: TorrentReprocessInput` | `Boolean!` |

### `QueueMutation` fields

| Field | Args | Returns |
|---|---|---|
| `purgeJobs` | `input: QueuePurgeJobsInput` | `Boolean!` |
| `enqueueReprocessTorrentsBatch` | `input: QueueEnqueueReprocessTorrentsBatchInput` | `Boolean!` |

## Common mutations

### Apply tags to a torrent

```graphql
mutation Tag {
  torrent {
    setTags(
      infoHashes: ["a1b2c3d4e5f67890123456789012345678901234"]
      tagNames: ["operator-curated", "trusted"]
    )
  }
}
```

### Delete a torrent by infohash

```graphql
mutation Delete {
  torrent {
    delete(infoHashes: ["a1b2c3d4e5f67890123456789012345678901234"])
  }
}
```

### Reprocess after editing the classifier

```graphql
mutation Reprocess {
  torrent {
    reprocess(input: { classifierFlags: { reclassifyAll: true } })
  }
}
```

(For bulk reprocess across the whole corpus, use the `bitagent reprocess` CLI command instead — it's transactional.)

## Custom scalars

| Scalar | Description |
|---|---|
| `Hash20` | 40-character hex info_hash |
| `DateTime` | RFC3339 |
| `Date` | `YYYY-MM-DD` |
| `Year` | Integer year |
| `Duration` | ISO 8601 duration |
| `ContentType` | Enum: `movie`, `tv_show`, `music`, `audiobook`, `ebook`, `comic`, `software`, `game`, `xxx`, `other` |
| `FileType` | Enum: video / audio / archive / document / image / executable / subtitle / other |
| `VideoResolution` | Enum: `v480p`, `v720p`, `v1080p`, `v2160p`, ... |
| `VideoSource` | Enum: `webdl`, `bluray`, `dvd`, `cam`, `ts`, ... |
| `VideoCodec` | Enum: `h264`, `h265`, `av1`, ... |
| `Video3D`, `VideoModifier` | Enum |
| `LanguageInfo` | Object: `code`, `name`, `nativeName` |

## Pagination

Set `input.offset` and `input.limit`. The result's `hasNextPage` is true when more rows exist; loop until it goes false.

```graphql
query Page {
  torrentContent {
    search(input: { queryString: "ubuntu", limit: 50, offset: 100 }) {
      items { infoHash title }
      hasNextPage
      totalCount
    }
  }
}
```

`limit` should not exceed `200` for interactive queries — the resolver does not impose a cap, but Postgres planner cost grows fast on large pages.

## Error handling

GraphQL errors come back in the standard `errors[]` array:

```json
{
  "data": null,
  "errors": [
    {
      "message": "input: torrent.delete: at least one infoHash required",
      "path": ["torrent", "delete"],
      "locations": [{ "line": 3, "column": 5 }]
    }
  ]
}
```

Field-level errors return `data` with the partial result and a non-empty `errors[]`.

## See also

- [Dashboard API reference](dashboard-api.md)
- [Torznab API reference](torznab-api.md)
- [CLI reference](cli.md) — many GraphQL operations have a CLI equivalent (`reprocess`, `classifier show`)
- [Configuration](../configuration.md)
