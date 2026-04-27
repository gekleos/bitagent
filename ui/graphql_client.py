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


SEARCH_TORRENTS = """
query SearchTorrents($query: String, $limit: Int, $offset: Int, $contentType: String) {
    searchTorrents(query: $query, limit: $limit, offset: $offset, contentType: $contentType) {
        totalCount
        items {
            infoHash
            name
            size
            seeders
            leechers
            contentType
            classifierScore
            discoveredAt
            files { path size }
            release { title year quality source }
        }
    }
}
"""

TORRENT_DETAIL = """
query TorrentDetail($infoHash: String!) {
    torrent(infoHash: $infoHash) {
        infoHash name size seeders leechers contentType
        classifierScore discoveredAt magnetUri
        files { path size }
        release { title year quality source imdbId tmdbId }
        evidence { id source result timestamp }
    }
}
"""

EVIDENCE_EVENTS = """
query EvidenceEvents($limit: Int, $offset: Int) {
    listEvidenceEvents(limit: $limit, offset: $offset) {
        totalCount
        items {
            id source infoHash result timestamp
            torrentName contentType
        }
    }
}
"""

SYSTEM_STATS = """
query SystemStats {
    systemStats {
        totalTorrents totalReleases totalEvidence
        dhtPeerCount indexerThroughput cacheHitRatio
        uptimeSeconds lastCrawlAt
        categoryBreakdown { category count }
    }
}
"""
