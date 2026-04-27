from __future__ import annotations
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings, MUTABLE_FIELDS
from auth import require_auth
from database import (
    get_db, get_all_overrides, set_override, get_audit_log,
    delete_override,
)
import graphql_client as gql
import tmdb


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import get_db
    await get_db()
    yield


app = FastAPI(title="BitAgent Dashboard", version="1.0.0", lifespan=lifespan)

BASE = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


# ── Health ────────────────────────────────────────────────────────────

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "ts": time.time()}


# ── Auth ──────────────────────────────────────────────────────────────

@app.get("/api/me")
async def me(identity: dict = Depends(require_auth)):
    return identity


# ── Dashboard page ────────────────────────────────────────────────────

@app.get("/")
async def dashboard(request: Request, identity: dict = Depends(require_auth)):
    return templates.TemplateResponse("index.html", {
        "request": request, "identity": identity, "active_tab": "dashboard",
    })


# ── API: System stats ────────────────────────────────────────────────

@app.get("/api/stats")
async def api_stats(identity: dict = Depends(require_auth)):
    result = await gql.query(gql.SYSTEM_STATS)
    data = (result.get("data") or {}).get("systemStats")
    if data:
        return data
    return {
        "totalTorrents": 0, "totalReleases": 0, "totalEvidence": 0,
        "dhtPeerCount": 0, "indexerThroughput": 0, "cacheHitRatio": 0,
        "uptimeSeconds": 0, "lastCrawlAt": None,
        "categoryBreakdown": [],
    }


@app.get("/api/metrics")
async def api_metrics(identity: dict = Depends(require_auth)):
    raw = await gql.fetch_metrics()
    lines = {}
    for line in raw.strip().splitlines():
        if line.startswith("#"):
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            lines[parts[0]] = parts[1]
    return lines


# ── API: Library / Torrents ───────────────────────────────────────────

@app.get("/api/torrents")
async def api_torrents(
    q: str = "",
    content_type: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    identity: dict = Depends(require_auth),
):
    result = await gql.query(gql.SEARCH_TORRENTS, {
        "query": q, "limit": limit, "offset": offset,
        "contentType": content_type or None,
    })
    data = (result.get("data") or {}).get("searchTorrents")
    if data:
        return data
    return {"totalCount": 0, "items": []}


@app.get("/api/torrents/{info_hash}")
async def api_torrent_detail(info_hash: str, identity: dict = Depends(require_auth)):
    result = await gql.query(gql.TORRENT_DETAIL, {"infoHash": info_hash})
    data = (result.get("data") or {}).get("torrent")
    if not data:
        raise HTTPException(404, "Torrent not found")
    return data


# ── API: Evidence ─────────────────────────────────────────────────────

@app.get("/api/evidence")
async def api_evidence(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    identity: dict = Depends(require_auth),
):
    result = await gql.query(gql.EVIDENCE_EVENTS, {"limit": limit, "offset": offset})
    data = (result.get("data") or {}).get("listEvidenceEvents")
    if data:
        return data
    return {"totalCount": 0, "items": []}


# ── API: Wants ────────────────────────────────────────────────────────

class WantCreate(BaseModel):
    title: str
    content_type: str = "any"
    query: str
    priority: int = 50
    notes: str = ""


class WantUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    priority: int | None = None
    notes: str | None = None


@app.get("/api/wants")
async def api_wants(identity: dict = Depends(require_auth)):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, title, content_type, query, status, priority, created_at, updated_at, notes "
        "FROM wants ORDER BY priority DESC, created_at DESC"
    )
    return [
        {"id": r[0], "title": r[1], "content_type": r[2], "query": r[3],
         "status": r[4], "priority": r[5], "created_at": r[6],
         "updated_at": r[7], "notes": r[8]}
        for r in rows
    ]


@app.post("/api/wants")
async def api_create_want(want: WantCreate, identity: dict = Depends(require_auth)):
    db = await get_db()
    now = time.time()
    cursor = await db.execute(
        "INSERT INTO wants (title, content_type, query, priority, notes, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
        (want.title, want.content_type, want.query, want.priority, want.notes, now, now),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "status": "created"}


@app.put("/api/wants/{want_id}")
async def api_update_want(want_id: int, update: WantUpdate, identity: dict = Depends(require_auth)):
    db = await get_db()
    fields, values = [], []
    for k, v in update.model_dump(exclude_none=True).items():
        fields.append(f"{k} = ?")
        values.append(v)
    if not fields:
        raise HTTPException(400, "No fields to update")
    fields.append("updated_at = ?")
    values.extend([time.time(), want_id])
    await db.execute(f"UPDATE wants SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    return {"status": "updated"}


@app.delete("/api/wants/{want_id}")
async def api_delete_want(want_id: int, identity: dict = Depends(require_auth)):
    db = await get_db()
    await db.execute("DELETE FROM wants WHERE id = ?", (want_id,))
    await db.commit()
    return {"status": "deleted"}


# ── API: Settings ─────────────────────────────────────────────────────

class SettingUpdate(BaseModel):
    value: str


@app.get("/api/settings")
async def api_settings(identity: dict = Depends(require_auth)):
    overrides = await get_all_overrides()
    fields = {}
    for key in MUTABLE_FIELDS:
        default = str(getattr(settings, key, ""))
        fields[key] = {
            "default": default,
            "current": overrides.get(key, default),
            "overridden": key in overrides,
        }
    return {"fields": fields, "mutable_keys": sorted(MUTABLE_FIELDS)}


@app.put("/api/settings/overrides/{key}")
async def api_set_override(key: str, body: SettingUpdate, identity: dict = Depends(require_auth)):
    if key not in MUTABLE_FIELDS:
        raise HTTPException(403, f"Field '{key}' is not mutable")
    result = await set_override(key, body.value, actor=identity.get("id", "unknown"))
    return result


@app.delete("/api/settings/overrides/{key}")
async def api_delete_override(key: str, identity: dict = Depends(require_auth)):
    if key not in MUTABLE_FIELDS:
        raise HTTPException(403, f"Field '{key}' is not mutable")
    ok = await delete_override(key, actor="operator")
    if not ok:
        raise HTTPException(404, "Override not found")
    return {"status": "deleted"}


@app.get("/api/settings/audit")
async def api_audit(
    limit: int = Query(100, ge=1, le=1000),
    identity: dict = Depends(require_auth),
):
    return await get_audit_log(limit)


# ── API: Notifications ────────────────────────────────────────────────

@app.get("/api/notifications")
async def api_notifications(identity: dict = Depends(require_auth)):
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, level, title, message, read, created_at FROM notifications ORDER BY created_at DESC LIMIT 50"
    )
    return [
        {"id": r[0], "level": r[1], "title": r[2], "message": r[3], "read": bool(r[4]), "at": r[5]}
        for r in rows
    ]


@app.put("/api/notifications/{nid}/read")
async def api_mark_read(nid: int, identity: dict = Depends(require_auth)):
    db = await get_db()
    await db.execute("UPDATE notifications SET read = 1 WHERE id = ?", (nid,))
    await db.commit()
    return {"status": "ok"}


# ── API: TMDB poster ─────────────────────────────────────────────────

@app.get("/api/poster/{tmdb_id}")
async def api_poster(tmdb_id: str, media_type: str = "movie"):
    data = await tmdb.get_poster(tmdb_id, media_type)
    if data:
        return data
    raise HTTPException(404, "Poster not found")


# ── API: GraphQL passthrough (for explorer) ───────────────────────────

class GQLRequest(BaseModel):
    query: str
    variables: dict | None = None


@app.post("/api/graphql")
async def api_graphql_proxy(body: GQLRequest, identity: dict = Depends(require_auth)):
    return await gql.query(body.query, body.variables)


# ── API: Demo data seeder ─────────────────────────────────────────────

@app.post("/api/seed-demo")
async def api_seed_demo(identity: dict = Depends(require_auth)):
    """Populate the dashboard with realistic demo data for presentation."""
    import random
    db = await get_db()

    # Seed wants
    demo_wants = [
        ("Breaking Bad S05E16", "tv_show", "breaking bad s05e16 ozymandias", 95),
        ("Dune Part Two (2024)", "movie", "dune part two 2024 2160p", 90),
        ("The Bear S03", "tv_show", "the bear s03 complete", 85),
        ("Oppenheimer (2023)", "movie", "oppenheimer 2023 bluray remux", 80),
        ("Shogun (2024)", "tv_show", "shogun 2024 s01", 75),
        ("Dark Side of the Moon FLAC", "music", "pink floyd dark side moon flac", 60),
        ("Severance S02", "tv_show", "severance s02 complete 1080p", 88),
        ("The Last of Us S02", "tv_show", "last of us s02", 92),
    ]
    now = time.time()
    for title, ct, query, prio in demo_wants:
        existing = await db.execute_fetchall("SELECT id FROM wants WHERE title = ?", (title,))
        if not existing:
            created = now - random.randint(3600, 86400 * 14)
            await db.execute(
                "INSERT INTO wants (title, content_type, query, priority, notes, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, '', ?, ?, ?)",
                (title, ct, query, prio, random.choice(["active", "active", "active", "paused"]), created, created),
            )

    # Seed notifications
    demo_notifs = [
        ("info", "DHT Bootstrap Complete", "Routing table initialized with 847 peers."),
        ("success", "Evidence Pipeline Active", "Sonarr webhook endpoint registered and receiving events."),
        ("warning", "High DHT Churn", "Peer table turnover exceeded 15% in the last hour."),
        ("info", "Classifier Updated", "CEL rule chain reloaded with 23 active rules."),
        ("success", "New Release Indexed", "Dune Part Two (2024) 2160p UHD BluRay matched with 94% confidence."),
        ("info", "Retention Sweep", "Purged 1,247 stale torrents older than 90 days."),
        ("warning", "Rate Limit Warning", "Approaching TMDB API rate limit (38/40 requests/10s)."),
        ("success", "Wantbridge Match", "Breaking Bad S05E16 matched via DHT direct seeder query."),
        ("info", "Metrics Export", "Prometheus scrape latency nominal at 12ms."),
        ("success", "Radarr Grab Confirmed", "Oppenheimer (2023) grab webhook confirmed by evidence pipeline."),
    ]
    for level, title, message in demo_notifs:
        existing = await db.execute_fetchall("SELECT id FROM notifications WHERE title = ?", (title,))
        if not existing:
            await db.execute(
                "INSERT INTO notifications (level, title, message, read, created_at) VALUES (?, ?, ?, ?, ?)",
                (level, title, message, 0, now - random.randint(60, 86400 * 3)),
            )

    # Seed some audit log entries
    demo_audits = [
        ("log_level", "info", "debug", "operator"),
        ("tmdb_api_key", None, "abc***redacted", "operator"),
        ("trust_forwarded_user", "false", "true", "admin"),
        ("bitagent_graphql_url", "http://localhost:3333/graphql", "http://bitagent:3333/graphql", "operator"),
        ("log_level", "debug", "info", "operator"),
    ]
    for key, old, new, actor in demo_audits:
        existing = await db.execute_fetchall(
            "SELECT id FROM audit_log WHERE key = ? AND new_value = ?", (key, new)
        )
        if not existing:
            await db.execute(
                "INSERT INTO audit_log (key, old_value, new_value, actor, timestamp) VALUES (?, ?, ?, ?, ?)",
                (key, old, new, actor, now - random.randint(300, 86400 * 7)),
            )

    await db.commit()
    return {"status": "seeded", "wants": len(demo_wants), "notifications": len(demo_notifs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=True)
