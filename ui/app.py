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

_START_TIME = time.time()

# Sliding-window snapshots of /metrics for instantaneous rate calc.
# Each entry is (monotonic_ts, dict[bare_metric_name -> sum_across_labels]).
# Sized so a 10s polling cadence covers ~5 minutes — enough to smooth
# DHT request bursts while staying responsive to throughput drops.
_METRIC_HISTORY: list[tuple[float, dict[str, float]]] = []
_METRIC_HISTORY_MAX = 32

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
    """Real stats: totalTorrents + categoryBreakdown from GraphQL,
    dhtPeerCount + indexerThroughput from /metrics, totalEvidence
    from the local SQLite, uptime from process start time.

    The schema does NOT have a `systemStats` query — that was a
    placeholder. Real fields below all map to live core endpoints.
    """
    # GraphQL: count + category breakdown
    gql_data = (await gql.query(gql.SYSTEM_STATS)).get("data") or {}
    search_block = (gql_data.get("torrentContent") or {}).get("search") or {}
    total_torrents = search_block.get("totalCount") or 0
    aggs = (search_block.get("aggregations") or {}).get("contentType") or []
    category_breakdown = [{"category": a["value"], "count": a["count"]} for a in aggs]

    # /metrics: parse Prometheus exposition for the values we surface.
    # Two views: metric_sum (labels collapsed) for the all-labels-summed
    # values and metric_lines (full label set) for label-keyed lookups.
    raw = await gql.fetch_metrics()
    metric_sum: dict[str, float] = {}
    metric_lines: dict[str, float] = {}  # key includes labels
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        key, val = parts
        bare = key.split("{", 1)[0]
        try:
            v = float(val)
        except ValueError:
            continue
        metric_sum[bare] = metric_sum.get(bare, 0.0) + v
        metric_lines[key] = v

    def labeled_sum(metric_name: str, label_filter: str) -> float:
        """Sum metric values whose label set contains label_filter substring.
        e.g. labeled_sum('bitagent_liveness_observations_total', 'class="alive"')
        sums across all outcome= variants."""
        total = 0.0
        prefix = metric_name + "{"
        for k, v in metric_lines.items():
            if k.startswith(prefix) and label_filter in k:
                total += v
        return total

    # Push this snapshot onto the sliding window; trim to last N entries.
    now_mono = time.monotonic()
    _METRIC_HISTORY.append((now_mono, metric_sum))
    if len(_METRIC_HISTORY) > _METRIC_HISTORY_MAX:
        del _METRIC_HISTORY[: len(_METRIC_HISTORY) - _METRIC_HISTORY_MAX]

    def rate_per_min(metric_name: str, *, default: float = 0.0) -> float:
        """Instantaneous rate per minute computed from the oldest available
        snapshot to now. Returns 0.0 until we have ≥2 samples ≥10s apart.

        Counter-reset guard: if the current value is less than any historical
        value, the upstream counter restarted (container recycle). In that
        case we use the most recent post-restart sample as the baseline so
        the rate stays non-negative and converges quickly to the true rate.
        """
        if len(_METRIC_HISTORY) < 2:
            return default
        cur = metric_sum.get(metric_name, 0.0)
        # Walk forward from the oldest, dropping any snapshots taken
        # before a reset (i.e. with a value > current).
        baseline_ts, baseline_val = _METRIC_HISTORY[0]
        for ts, snap in _METRIC_HISTORY:
            if snap.get(metric_name, 0.0) <= cur:
                baseline_ts, baseline_val = ts, snap.get(metric_name, 0.0)
                break
        dt = now_mono - baseline_ts
        if dt < 10:
            return default
        rate = (cur - baseline_val) / dt * 60.0
        return max(rate, 0.0)

    # DHT peer count: in-flight DHT request concurrency is a live proxy
    dht_peers = int(metric_sum.get("bitagent_dht_client_request_concurrency", 0))

    # Crawl rate: DHT request rate per minute (sample_infohashes + get_peers
    # request count is a true measure of how much of the network the crawler
    # is touching per unit time).
    crawl_rate_per_min = int(
        rate_per_min("bitagent_dht_client_request_duration_seconds_count")
    )
    # Indexer throughput: classifier-examined rate per minute (instantaneous
    # if we have enough samples, lifetime-average fallback otherwise).
    examined = metric_sum.get("bitagent_contentfilter_examined_total", 0)
    uptime_s = max(int(time.time() - _START_TIME), 1)
    throughput_per_min = int(
        rate_per_min(
            "bitagent_contentfilter_examined_total",
            default=(examined / uptime_s) * 60,
        )
    )

    # Cache hit ratio (classifier LLM cache; 0.0 when LLM tier is idle)
    hits = metric_sum.get("bitagent_classifier_llm_cache_hits_total", 0)
    misses = metric_sum.get("bitagent_classifier_llm_cache_misses_total", 0)
    cache_hit_ratio = (hits / (hits + misses)) if (hits + misses) > 0 else 0.0

    # ── Liveness pipeline (counters emitted by the bitagent core's
    # internal/evidence/liveness module — see gekleos/bitmagnet feat/liveness-
    # blocklist). The core uses labelled counters: observations_total has
    # {class,outcome} labels and revalidations_total has {outcome}. We sum
    # across the orthogonal dimension(s) we don't care about. All values
    # are 0 when the module is absent or disabled. ──
    obs_alive = labeled_sum("bitagent_liveness_observations_total", 'class="alive"')
    obs_suspect = labeled_sum("bitagent_liveness_observations_total", 'class="suspect"')
    blacklist_size = int(metric_sum.get("bitagent_liveness_blacklist_size", 0))
    excluded_total = metric_sum.get("bitagent_liveness_torznab_excluded_total", 0)
    revalid_alive = labeled_sum("bitagent_liveness_revalidations_total", 'outcome="alive_again"')
    revalid_dead = labeled_sum("bitagent_liveness_revalidations_total", 'outcome="still_dead"')

    # Block rate: how often the Torznab filter is dropping a stale infohash.
    block_rate_per_min = int(rate_per_min("bitagent_liveness_torznab_excluded_total"))

    # Success rate: of the alive+suspect observations we have, what fraction
    # are alive. This is the operator's "did the system actually deliver
    # working torrents" KPI. Cumulative over the lifetime of the dashboard
    # DB; resets when bitagent_ui_data volume is destroyed.
    obs_total = obs_alive + obs_suspect
    success_rate = (obs_alive / obs_total) if obs_total > 0 else 0.0

    # Re-validation effectiveness: of the dead torrents we re-checked, what
    # % came back to life (signal that our threshold isn't tuned right if
    # this number is high — we're killing torrents that recover).
    revalid_total = revalid_alive + revalid_dead
    revalid_recovery_rate = (revalid_alive / revalid_total) if revalid_total > 0 else 0.0

    # Local SQLite: evidence count (degrade gracefully if table is missing)
    total_evidence = 0
    try:
        db = await get_db()
        cur = await db.execute("SELECT COUNT(*) FROM evidence")
        row = await cur.fetchone()
        await cur.close()
        if row:
            total_evidence = row[0]
    except Exception:
        pass

    return {
        "totalTorrents": total_torrents,
        "totalReleases": total_torrents,
        "totalEvidence": total_evidence,
        "dhtPeerCount": dht_peers,
        "crawlRatePerMin": crawl_rate_per_min,
        "indexerThroughput": throughput_per_min,
        "cacheHitRatio": cache_hit_ratio,
        "uptimeSeconds": uptime_s,
        "lastCrawlAt": None,
        "categoryBreakdown": category_breakdown,
        "version": gql_data.get("version") or "",
        "liveness": {
            "blacklistSize": blacklist_size,
            "blockRatePerMin": block_rate_per_min,
            "totalExcluded": int(excluded_total),
            "observationsAlive": int(obs_alive),
            "observationsSuspect": int(obs_suspect),
            "successRate": success_rate,
            "revalidations": {
                "aliveAgain": int(revalid_alive),
                "stillDead": int(revalid_dead),
                "recoveryRate": revalid_recovery_rate,
            },
        },
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
    """Wraps the core's torrentContent.search.

    Output shape stays {totalCount, items[...]} for the v1 frontend; we
    flatten the nested torrent { name, size, filesCount } onto each item
    so the existing JS can read .name / .size / .filesCount directly.
    """
    search_input: dict = {
        "queryString": q,
        "limit": limit,
        "offset": offset,
        "totalCount": True,
    }
    if content_type:
        search_input["facets"] = {"contentType": {"filter": [content_type]}}
    result = await gql.query(gql.SEARCH_TORRENTS, {"input": search_input})
    block = ((result.get("data") or {}).get("torrentContent") or {}).get("search") or {}

    # Operator block phrases applied as a post-filter on the title.
    # Hits per phrase are tracked so the operator can see which patterns
    # are actually doing work in the Block Lists tab.
    block_phrases = await _load_block_phrases()
    items = []
    excluded_count = 0
    for it in block.get("items") or []:
        torrent = it.get("torrent") or {}
        title = (it.get("title") or torrent.get("name") or "")
        title_lower = title.lower()
        matched_phrase_id = None
        for bp in block_phrases:
            if bp["pattern"] in title_lower:
                matched_phrase_id = bp["id"]
                break
        if matched_phrase_id is not None:
            await _bump_block_phrase_hit(matched_phrase_id)
            excluded_count += 1
            continue
        items.append({
            "infoHash": it.get("infoHash"),
            "name": title,
            "title": it.get("title"),
            "size": torrent.get("size") or 0,
            "filesCount": torrent.get("filesCount") or 0,
            "seeders": it.get("seeders") or 0,
            "leechers": it.get("leechers") or 0,
            "contentType": it.get("contentType"),
            "contentSource": it.get("contentSource"),
            "discoveredAt": it.get("createdAt"),
            "updatedAt": it.get("updatedAt"),
        })
    return {
        "totalCount": (block.get("totalCount") or 0) - excluded_count,
        "items": items,
        "excludedByBlockPhrases": excluded_count,
    }


async def _load_block_phrases() -> list[dict]:
    """All operator block phrases, lowercased, ordered by id. Cached at the
    request scope (cheap — typically <50 rows; SQLite handles it fine)."""
    db = await get_db()
    cur = await db.execute(
        "SELECT id, pattern, scope, note, hits FROM block_phrases ORDER BY id"
    )
    rows = await cur.fetchall()
    await cur.close()
    return [
        {"id": r[0], "pattern": (r[1] or "").lower(), "scope": r[2], "note": r[3] or "", "hits": r[4]}
        for r in rows
    ]


async def _bump_block_phrase_hit(phrase_id: int) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE block_phrases SET hits = hits + 1 WHERE id = ?", (phrase_id,)
    )
    await db.commit()


@app.get("/api/torrents/{info_hash}")
async def api_torrent_detail(info_hash: str, identity: dict = Depends(require_auth)):
    result = await gql.query(gql.TORRENT_DETAIL, {"infoHash": info_hash})
    data = result.get("data") or {}
    torrents = data.get("torrent") or []
    content = ((data.get("torrentContent") or {}).get("search") or {}).get("items") or []
    if not torrents and not content:
        raise HTTPException(404, "Torrent not found")
    t = torrents[0] if torrents else {}
    c = content[0] if content else {}
    return {
        "infoHash": info_hash,
        "name": c.get("title") or t.get("name"),
        "title": c.get("title"),
        "size": t.get("size") or 0,
        "filesCount": t.get("filesCount") or 0,
        "files": t.get("files") or [],
        "contentType": c.get("contentType"),
        "seeders": c.get("seeders") or 0,
        "leechers": c.get("leechers") or 0,
        "magnetUri": f"magnet:?xt=urn:btih:{info_hash}",
    }


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


# ── API: Filters status (read-only view of bitagent core contentfilter) ──

@app.get("/api/filters/status")
async def api_filters_status(identity: dict = Depends(require_auth)):
    """Aggregate counts emitted by the bitagent core's contentfilter chain.
    Read-only — toggling/configuring lives in env vars on the core stack.
    Returns zero values when the core is unreachable."""
    raw = await gql.fetch_metrics()
    metric_sum: dict[str, float] = {}
    blocked_ext: dict[str, int] = {}
    drop_reason: dict[str, int] = {}
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        key, val = parts
        try:
            v = float(val)
        except ValueError:
            continue
        bare = key.split("{", 1)[0]
        metric_sum[bare] = metric_sum.get(bare, 0.0) + v
        # Parse out specific labels we care about
        if bare == "bitagent_contentfilter_blocked_ext_total" and "ext=\"" in key:
            ext = key.split("ext=\"", 1)[1].split("\"", 1)[0]
            blocked_ext[ext] = int(v)
        if bare == "bitagent_contentfilter_drop_total" and "reason=\"" in key:
            reason = key.split("reason=\"", 1)[1].split("\"", 1)[0]
            drop_reason[reason] = int(v)

    return {
        "examined": int(metric_sum.get("bitagent_contentfilter_examined_total", 0)),
        "drops": {
            "blocked_extension": drop_reason.get("blocked_extension", 0),
            "non_latin_script": drop_reason.get("non_latin_script", 0),
            "nsfw_keyword": drop_reason.get("nsfw_keyword", 0),
        },
        "blockedExtensions": [
            {"ext": ext, "count": blocked_ext[ext]}
            for ext in sorted(blocked_ext.keys(), key=lambda k: -blocked_ext[k])
        ],
        "csam": {
            "blocklistEntries": int(metric_sum.get("bitagent_csam_blocklist_entries", 0)),
            "lookups": int(metric_sum.get("bitagent_csam_blocklist_lookups_total", 0)),
            "exports": int(metric_sum.get("bitagent_csam_blocklist_export_total", 0)),
        },
    }


# ── API: Operator block phrases (CRUD) ───────────────────────────────

class BlockPhrasePayload(BaseModel):
    pattern: str
    note: str = ""


@app.get("/api/block-phrases")
async def api_block_phrases_list(identity: dict = Depends(require_auth)):
    db = await get_db()
    cur = await db.execute(
        "SELECT id, pattern, scope, note, hits, created_at "
        "FROM block_phrases ORDER BY hits DESC, id DESC"
    )
    rows = await cur.fetchall()
    await cur.close()
    return {
        "items": [
            {
                "id": r[0],
                "pattern": r[1],
                "scope": r[2],
                "note": r[3] or "",
                "hits": r[4],
                "createdAt": r[5],
            }
            for r in rows
        ]
    }


@app.post("/api/block-phrases")
async def api_block_phrases_create(
    payload: BlockPhrasePayload, identity: dict = Depends(require_auth)
):
    pattern = payload.pattern.strip()
    if not pattern:
        raise HTTPException(400, "pattern must be non-empty")
    if len(pattern) > 200:
        raise HTTPException(400, "pattern must be ≤200 chars")
    db = await get_db()
    try:
        cur = await db.execute(
            "INSERT INTO block_phrases (pattern, scope, note, hits, created_at) "
            "VALUES (?, 'title', ?, 0, ?)",
            (pattern, payload.note.strip(), time.time()),
        )
        await db.commit()
        return {"id": cur.lastrowid, "pattern": pattern}
    except Exception as e:
        # UNIQUE constraint = duplicate pattern
        if "UNIQUE" in str(e):
            raise HTTPException(409, "pattern already exists")
        raise


@app.delete("/api/block-phrases/{phrase_id}")
async def api_block_phrases_delete(
    phrase_id: int, identity: dict = Depends(require_auth)
):
    db = await get_db()
    cur = await db.execute("DELETE FROM block_phrases WHERE id = ?", (phrase_id,))
    await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "phrase not found")
    return {"deleted": phrase_id}


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
