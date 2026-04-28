"""GraphQL + Prometheus client for the BitAgent core.

The core's GraphQL schema (bitagent / bitmagnet) exposes:
    version() -> String
    workers()
    health()
    queue()
    torrent(infoHash)
    torrentContent { search(input: TorrentContentSearchQueryInput) }

There is no `searchTorrents`, no `systemStats`, and no `listEvidenceEvents`
in the upstream schema — those were placeholders in the public-release prep.
This module wraps the real schema and derives the dashboard's stats from
torrentContent.search aggregations + the Prometheus /metrics scrape.
"""
from __future__ import annotations

import httpx
from config import settings

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def query(q: str, variables: dict | None = None) -> dict:
    client = _get_client()
    try:
        resp = await client.post(
            settings.bitagent_graphql_url,
            json={"query": q, "variables": variables or {}},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return {"data": None, "errors": [{"message": "GraphQL endpoint unreachable"}]}


async def fetch_metrics() -> str:
    client = _get_client()
    try:
        resp = await client.get(settings.bitagent_metrics_url)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError:
        return ""


# ── Real schema queries ──────────────────────────────────────────────────

SEARCH_TORRENTS = """
query Search($input: TorrentContentSearchQueryInput!) {
  torrentContent {
    search(input: $input) {
      totalCount
      hasNextPage
      items {
        infoHash
        title
        contentType
        contentSource
        contentId
        seeders
        leechers
        createdAt
        updatedAt
        torrent {
          name
          size
          filesCount
        }
      }
    }
  }
}
"""

TORRENT_DETAIL = """
query TorrentDetail($infoHash: Hash20!) {
  torrent(infoHashes: [$infoHash]) {
    infoHash
    name
    size
    filesCount
    files { path size }
  }
  torrentContent {
    search(input: { infoHashes: [$infoHash], limit: 1 }) {
      items {
        infoHash
        title
        contentType
        seeders
        leechers
      }
    }
  }
}
"""

# Stats: totalCount + per-contentType aggregations in one round-trip.
# `facets:{contentType:{aggregate:true}}` triggers the contentType array.
SYSTEM_STATS = """
query SystemStats {
  version
  torrentContent {
    search(input: {
      queryString: "",
      limit: 1,
      totalCount: true,
      facets: { contentType: { aggregate: true } }
    }) {
      totalCount
      aggregations {
        contentType { value count }
      }
    }
  }
}
"""

# Evidence events live in the local SQLite (populated by *arr webhooks),
# NOT in the bitagent core. The core has no concept of operator evidence.
# We keep the constant as a sentinel for any caller that imports it but
# the actual evidence list endpoint reads from database.py.
EVIDENCE_EVENTS = "# evidence comes from the local SQLite — see database.list_evidence()"
