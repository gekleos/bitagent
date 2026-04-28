# BitAgent Dashboard API Reference

This document describes the REST API exposed by the BitAgent dashboard.
All endpoints are served from the dashboard's base URL. Responses use
JSON unless otherwise noted. Authenticated endpoints require a valid
session; unauthenticated requests receive a `401 Unauthorized` response.

---

## Health

### GET /healthz

Returns the current health status of the dashboard service.

**Authentication:** None required.

**Response:**

```json
{
  "status": "ok",
  "ts": "2026-04-27T14:30:00.000Z"
}
```

| Field    | Type   | Description                            |
|----------|--------|----------------------------------------|
| `status` | string | Service status. `"ok"` when healthy.   |
| `ts`     | string | ISO-8601 timestamp of the health check.|

---

## Auth

### GET /api/me

Returns the identity of the currently authenticated user.

**Response:**

```json
{
  "id": "usr_abc123",
  "method": "api_key",
  "display": "snorton"
}
```

| Field     | Type   | Description                                    |
|-----------|--------|------------------------------------------------|
| `id`      | string | Unique identifier for the authenticated user.  |
| `method`  | string | Authentication method (e.g. `api_key`, `oidc`).|
| `display` | string | Human-readable display name.                   |

---

## Stats

### GET /api/stats

Returns aggregate system statistics from the BitAgent core.

**Response:**

```json
{
  "totalTorrents": 142857,
  "totalReleases": 98412,
  "totalEvidence": 310044,
  "dhtPeerCount": 2048,
  "indexerThroughput": 320.5,
  "cacheHitRatio": 0.87,
  "uptimeSeconds": 604800,
  "lastCrawlAt": "2026-04-27T12:00:00.000Z",
  "categoryBreakdown": {
    "movie": 42000,
    "tv": 35000,
    "music": 21412
  }
}
```

| Field                 | Type   | Description                                       |
|-----------------------|--------|---------------------------------------------------|
| `totalTorrents`       | number | Total number of tracked torrents.                 |
| `totalReleases`       | number | Total number of identified releases.              |
| `totalEvidence`       | number | Total evidence records collected.                 |
| `dhtPeerCount`        | number | Current number of DHT peers.                      |
| `indexerThroughput`   | number | Indexer processing rate (items per second).        |
| `cacheHitRatio`       | number | Cache hit ratio between 0 and 1.                  |
| `uptimeSeconds`       | number | Seconds since the BitAgent core last started.     |
| `lastCrawlAt`         | string | ISO-8601 timestamp of the most recent crawl.      |
| `categoryBreakdown`   | object | Map of content category to torrent count.         |

### GET /api/metrics

Proxies Prometheus-format metrics from the BitAgent core.

**Response:** `text/plain` — standard Prometheus exposition format.

---

## Library

### GET /api/torrents

Search and paginate the torrent library.

**Query Parameters:**

| Parameter      | Type   | Default | Description                              |
|----------------|--------|---------|------------------------------------------|
| `q`            | string | `""`    | Free-text search query.                  |
| `content_type` | string | `""`    | Filter by content type (e.g. `movie`).   |
| `limit`        | number | `50`    | Maximum items to return (1--500).        |
| `offset`       | number | `0`     | Number of items to skip for pagination.  |

**Response:**

```json
{
  "totalCount": 1420,
  "items": [
    {
      "info_hash": "a1b2c3d4e5f6...",
      "title": "Example Release",
      "content_type": "movie",
      "size_bytes": 1073741824,
      "created_at": "2026-04-20T08:00:00.000Z"
    }
  ]
}
```

| Field        | Type   | Description                              |
|--------------|--------|------------------------------------------|
| `totalCount` | number | Total matching results (before paging).  |
| `items`      | array  | Array of torrent summary objects.        |

### GET /api/torrents/{info_hash}

Returns full detail for a single torrent, including its file list,
associated evidence records, and a pre-built magnet URI.

**Path Parameters:**

| Parameter   | Type   | Description                            |
|-------------|--------|----------------------------------------|
| `info_hash` | string | The torrent's unique info hash (hex).  |

**Response:**

```json
{
  "info_hash": "a1b2c3d4e5f6...",
  "title": "Example Release",
  "content_type": "movie",
  "size_bytes": 1073741824,
  "created_at": "2026-04-20T08:00:00.000Z",
  "magnet_uri": "magnet:?xt=urn:btih:a1b2c3d4e5f6...",
  "files": [
    {
      "path": "Example.Release.2026.mkv",
      "size_bytes": 1073741824
    }
  ],
  "evidence": [
    {
      "id": "ev_001",
      "source": "dht",
      "recorded_at": "2026-04-21T10:15:00.000Z"
    }
  ]
}
```

**Error Responses:**

| Status | Description                                      |
|--------|--------------------------------------------------|
| `404`  | No torrent found with the specified `info_hash`. |

---

## Evidence

### GET /api/evidence

Returns a paginated list of webhook evidence events.

**Query Parameters:**

| Parameter | Type   | Default | Description                             |
|-----------|--------|---------|-----------------------------------------|
| `limit`   | number | `50`    | Maximum items to return (1--500).       |
| `offset`  | number | `0`     | Number of items to skip for pagination. |

**Response:**

```json
{
  "items": [
    {
      "id": "ev_001",
      "info_hash": "a1b2c3d4e5f6...",
      "source": "dht",
      "recorded_at": "2026-04-21T10:15:00.000Z",
      "payload": {}
    }
  ]
}
```

---

## Wants

Wants represent content the user is actively looking for. Each want
tracks a desired title, content type, search query, priority, and notes.

### GET /api/wants

Returns the full list of wants.

**Response:**

```json
[
  {
    "id": "w_001",
    "title": "Some Movie 2026",
    "content_type": "movie",
    "query": "some movie 2026 2160p",
    "priority": "high",
    "status": "active",
    "notes": "Prefer HDR release.",
    "created_at": "2026-04-15T09:00:00.000Z",
    "updated_at": "2026-04-15T09:00:00.000Z"
  }
]
```

### POST /api/wants

Creates a new want.

**Request Body:**

```json
{
  "title": "Some Movie 2026",
  "content_type": "movie",
  "query": "some movie 2026 2160p",
  "priority": "high",
  "notes": "Prefer HDR release."
}
```

| Field          | Type   | Required | Description                                   |
|----------------|--------|----------|-----------------------------------------------|
| `title`        | string | Yes      | Human-readable title of the desired content.  |
| `content_type` | string | Yes      | Content category (e.g. `movie`, `tv`).        |
| `query`        | string | Yes      | Search query used for automatic matching.     |
| `priority`     | string | Yes      | Priority level: `low`, `medium`, or `high`.   |
| `notes`        | string | No       | Free-text notes.                              |

**Response:** `201 Created` with the newly created want object.

### PUT /api/wants/{id}

Updates an existing want. Only the supplied fields are modified;
omitted fields retain their current values.

**Path Parameters:**

| Parameter | Type   | Description            |
|-----------|--------|------------------------|
| `id`      | string | The want's unique ID.  |

**Request Body (all fields optional):**

```json
{
  "title": "Updated Title",
  "status": "fulfilled",
  "priority": "low",
  "notes": "Found a good release."
}
```

| Field      | Type   | Description                                     |
|------------|--------|-------------------------------------------------|
| `title`    | string | Updated title.                                  |
| `status`   | string | New status (e.g. `active`, `fulfilled`).        |
| `priority` | string | New priority: `low`, `medium`, or `high`.       |
| `notes`    | string | Updated notes.                                  |

**Response:** `200 OK` with the updated want object.

**Error Responses:**

| Status | Description                              |
|--------|------------------------------------------|
| `404`  | No want found with the specified `id`.   |

### DELETE /api/wants/{id}

Deletes a want permanently.

**Path Parameters:**

| Parameter | Type   | Description            |
|-----------|--------|------------------------|
| `id`      | string | The want's unique ID.  |

**Response:** `204 No Content` on success.

**Error Responses:**

| Status | Description                              |
|--------|------------------------------------------|
| `404`  | No want found with the specified `id`.   |

---

## Settings

Settings are managed through a defaults-plus-overrides model. Each
setting has a default value defined by the system. Users can override
individual settings, and every change is recorded in the audit log.

### GET /api/settings

Returns all mutable settings with their default values, current
effective values, and override status.

**Response:**

```json
{
  "items": [
    {
      "key": "crawl_interval_seconds",
      "default": 3600,
      "value": 1800,
      "overridden": true
    },
    {
      "key": "max_concurrent_downloads",
      "default": 5,
      "value": 5,
      "overridden": false
    }
  ]
}
```

| Field        | Type    | Description                                       |
|--------------|---------|---------------------------------------------------|
| `key`        | string  | Unique setting identifier.                        |
| `default`    | any     | System-defined default value.                     |
| `value`      | any     | Current effective value (default or override).    |
| `overridden` | boolean | `true` if the user has set a custom override.     |

### PUT /api/settings/overrides/{key}

Sets a user override for a specific setting.

**Path Parameters:**

| Parameter | Type   | Description                   |
|-----------|--------|-------------------------------|
| `key`     | string | The setting key to override.  |

**Request Body:**

```json
{
  "value": 1800
}
```

| Field   | Type | Required | Description            |
|---------|------|----------|------------------------|
| `value` | any  | Yes      | The new override value. |

**Response:** `200 OK` with the updated setting object.

**Error Responses:**

| Status | Description                                    |
|--------|------------------------------------------------|
| `400`  | Invalid value type or out-of-range value.      |
| `404`  | No setting found with the specified `key`.     |

### DELETE /api/settings/overrides/{key}

Removes a user override, reverting the setting to its default value.

**Path Parameters:**

| Parameter | Type   | Description                          |
|-----------|--------|--------------------------------------|
| `key`     | string | The setting key to reset to default. |

**Response:** `200 OK` with the setting restored to its default value.

**Error Responses:**

| Status | Description                                |
|--------|--------------------------------------------|
| `404`  | No setting found with the specified `key`. |

### GET /api/settings/audit

Returns an audit log of setting changes.

**Query Parameters:**

| Parameter | Type   | Default | Description                          |
|-----------|--------|---------|--------------------------------------|
| `limit`   | number | `100`   | Maximum entries to return (1--1000). |

**Response:**

```json
{
  "items": [
    {
      "key": "crawl_interval_seconds",
      "action": "override_set",
      "old_value": 3600,
      "new_value": 1800,
      "changed_by": "snorton",
      "changed_at": "2026-04-27T11:00:00.000Z"
    }
  ]
}
```

---

## Notifications

### GET /api/notifications

Returns the list of notifications for the current user.

**Response:**

```json
{
  "items": [
    {
      "id": "n_001",
      "type": "want_fulfilled",
      "message": "Want 'Some Movie 2026' has been fulfilled.",
      "read": false,
      "created_at": "2026-04-27T13:00:00.000Z"
    }
  ]
}
```

### PUT /api/notifications/{id}/read

Marks a notification as read.

**Path Parameters:**

| Parameter | Type   | Description                       |
|-----------|--------|-----------------------------------|
| `id`      | string | The notification's unique ID.     |

**Response:** `200 OK` with the updated notification object.

**Error Responses:**

| Status | Description                                         |
|--------|-----------------------------------------------------|
| `404`  | No notification found with the specified `id`.      |

---

## TMDB

### GET /api/poster/{tmdb_id}

Returns a cached poster image URL for the given TMDB identifier.
Results are cached server-side to avoid repeated TMDB API calls.

**Path Parameters:**

| Parameter | Type   | Description             |
|-----------|--------|-------------------------|
| `tmdb_id` | string | The TMDB identifier.    |

**Query Parameters:**

| Parameter    | Type   | Default   | Description                              |
|--------------|--------|-----------|------------------------------------------|
| `media_type` | string | `"movie"` | Media type: `movie` or `tv`.             |

**Response:**

```json
{
  "tmdb_id": "12345",
  "media_type": "movie",
  "poster_url": "https://image.tmdb.org/t/p/w500/example.jpg"
}
```

---

## GraphQL

### POST /api/graphql

Proxies a GraphQL request to the BitAgent core engine. This endpoint
allows the dashboard to execute arbitrary queries and mutations
supported by the core's GraphQL schema.

**Request Body:**

```json
{
  "query": "query { torrents(limit: 10) { info_hash title } }",
  "variables": {}
}
```

| Field       | Type   | Required | Description                        |
|-------------|--------|----------|------------------------------------|
| `query`     | string | Yes      | The GraphQL query or mutation.     |
| `variables` | object | No       | Variables referenced by the query. |

**Response:** Standard GraphQL response envelope:

```json
{
  "data": {
    "torrents": [
      {
        "info_hash": "a1b2c3d4e5f6...",
        "title": "Example Release"
      }
    ]
  },
  "errors": null
}
```

---

## Seed

### POST /api/seed-demo

Populates the system with demo data for presentation or testing
purposes. This endpoint is idempotent; calling it multiple times
will not create duplicate records.

**Authentication:** Required.

**Request Body:** None.

**Response:** `200 OK`

```json
{
  "seeded": true,
  "counts": {
    "torrents": 50,
    "evidence": 150,
    "wants": 5,
    "notifications": 10
  }
}
```

---

## Common Error Responses

All endpoints may return the following standard errors:

| Status | Description                                                   |
|--------|---------------------------------------------------------------|
| `400`  | Bad request. The request body or parameters are malformed.    |
| `401`  | Unauthorized. Authentication is required or has expired.      |
| `404`  | Not found. The requested resource does not exist.             |
| `500`  | Internal server error. An unexpected condition was encountered.|
