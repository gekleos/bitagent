from __future__ import annotations

import time

import httpx

from config import settings
from database import get_db

TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w300"
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def get_poster(tmdb_id: str, media_type: str = "movie") -> dict | None:
    if not settings.tmdb_api_key or not tmdb_id:
        return None

    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT poster_url, title, year FROM poster_cache WHERE tmdb_id = ?",
        (tmdb_id,),
    )
    if rows:
        return {"poster_url": rows[0][0], "title": rows[0][1], "year": rows[0][2]}

    client = _get_client()
    try:
        resp = await client.get(
            f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}",
            params={"api_key": settings.tmdb_api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        poster_path = data.get("poster_path")
        poster_url = f"{TMDB_IMG_BASE}{poster_path}" if poster_path else None
        title = data.get("title") or data.get("name", "")
        year = (data.get("release_date") or data.get("first_air_date") or "")[:4]

        await db.execute(
            "INSERT OR REPLACE INTO poster_cache (tmdb_id, poster_url, title, year, fetched_at) VALUES (?, ?, ?, ?, ?)",
            (tmdb_id, poster_url, title, year, time.time()),
        )
        await db.commit()
        return {"poster_url": poster_url, "title": title, "year": year}
    except httpx.HTTPError:
        return None
