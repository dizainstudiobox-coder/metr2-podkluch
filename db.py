"""SQLite-хранилище для бота МЕТР² ПОД КЛЮЧ."""
import os
import aiosqlite
from pathlib import Path

DB_PATH = Path(os.getenv("BOT_DB_PATH", "/tmp/metr2.sqlite3"))


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                project_id TEXT,
                name TEXT,
                phone TEXT,
                channel TEXT,
                timing TEXT,
                consent BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                project_id TEXT,
                event_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id);
            CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
        """)
        await db.commit()


async def upsert_user(tg_id, username, first_name, last_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (tg_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (tg_id, username, first_name, last_name),
        )
        await db.commit()


async def log_event(tg_id, project_id, event_type):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO events (tg_id, project_id, event_type) VALUES (?, ?, ?)",
            (tg_id, project_id, event_type),
        )
        await db.commit()


async def save_order(tg_id, project_id, name, phone, channel, timing):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (tg_id, project_id, name, phone, channel, timing) VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, project_id, name, phone, channel, timing),
        )
        await db.commit()
        return cur.lastrowid


async def _scalar(db, sql, *args):
    async with db.execute(sql, args) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        total_orders = await _scalar(db, "SELECT COUNT(*) FROM orders")
        total_users = await _scalar(db, "SELECT COUNT(*) FROM users")
        week_orders = await _scalar(db, "SELECT COUNT(*) FROM orders WHERE created_at >= datetime('now','-7 days')")
        total_views = await _scalar(db, "SELECT COUNT(*) FROM events WHERE event_type='project_view'")
        async with db.execute(
            "SELECT project_id, COUNT(*) c FROM orders GROUP BY project_id ORDER BY c DESC LIMIT 5"
        ) as cur:
            top_projects = await cur.fetchall()
        return {
            "total_orders": total_orders, "total_users": total_users,
            "week_orders": week_orders, "total_views": total_views,
            "top_projects": list(top_projects),
        }


async def get_recent_orders(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, tg_id, project_id, name, phone, channel, timing, created_at FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_project_counters():
    async with aiosqlite.connect(DB_PATH) as db:
        result = {}
        async with db.execute(
            "SELECT project_id, COUNT(*) FROM events WHERE event_type='project_view' GROUP BY project_id"
        ) as cur:
            for pid, cnt in await cur.fetchall():
                result.setdefault(pid, {})["views"] = cnt
        async with db.execute(
            "SELECT project_id, COUNT(*) FROM orders GROUP BY project_id"
        ) as cur:
            for pid, cnt in await cur.fetchall():
                result.setdefault(pid, {})["orders"] = cnt
        return result
