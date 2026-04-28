from __future__ import annotations
import time
import aiosqlite
from config import settings

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.db_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _init_tables(_db)
    return _db


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS settings_overrides (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            actor TEXT NOT NULL DEFAULT 'operator',
            timestamp REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS wants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'any',
            query TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            priority INTEGER NOT NULL DEFAULT 50,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            notes TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS poster_cache (
            tmdb_id TEXT PRIMARY KEY,
            poster_url TEXT,
            title TEXT,
            year TEXT,
            fetched_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL DEFAULT 'info',
            title TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            read INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        );
        -- Operator-managed text patterns that get filtered out of the
        -- Library tab (and, in a future MR, fed into the bitagent core's
        -- contentfilter chain via env). `pattern` is matched as a
        -- case-insensitive substring against the torrent title.
        -- scope is reserved for future use (currently always 'title').
        CREATE TABLE IF NOT EXISTS block_phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL UNIQUE,
            scope TEXT NOT NULL DEFAULT 'title',
            note TEXT DEFAULT '',
            hits INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        );
    """)
    await db.commit()


async def get_override(key: str) -> str | None:
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT value FROM settings_overrides WHERE key = ?", (key,)
    )
    return row[0][0] if row else None


async def set_override(key: str, value: str, actor: str = "operator") -> dict:
    db = await get_db()
    old_rows = await db.execute_fetchall(
        "SELECT value FROM settings_overrides WHERE key = ?", (key,)
    )
    old_value = old_rows[0][0] if old_rows else None
    now = time.time()
    await db.execute(
        "INSERT OR REPLACE INTO settings_overrides (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, now),
    )
    await db.execute(
        "INSERT INTO audit_log (key, old_value, new_value, actor, timestamp) VALUES (?, ?, ?, ?, ?)",
        (key, old_value, value, actor, now),
    )
    await db.commit()
    return {"key": key, "old": old_value, "new": value, "actor": actor, "at": now}


async def get_all_overrides() -> dict[str, str]:
    db = await get_db()
    rows = await db.execute_fetchall("SELECT key, value FROM settings_overrides")
    return {r[0]: r[1] for r in rows}


async def get_audit_log(limit: int = 100) -> list[dict]:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, key, old_value, new_value, actor, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    return [
        {"id": r[0], "key": r[1], "old": r[2], "new": r[3], "actor": r[4], "at": r[5]}
        for r in rows
    ]


async def delete_override(key: str, actor: str = "operator") -> bool:
    db = await get_db()
    old_rows = await db.execute_fetchall(
        "SELECT value FROM settings_overrides WHERE key = ?", (key,)
    )
    if not old_rows:
        return False
    now = time.time()
    await db.execute("DELETE FROM settings_overrides WHERE key = ?", (key,))
    await db.execute(
        "INSERT INTO audit_log (key, old_value, new_value, actor, timestamp) VALUES (?, ?, ?, ?, ?)",
        (key, old_rows[0][0], None, actor, now),
    )
    await db.commit()
    return True
