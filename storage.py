"""
storage.py — PostgreSQL через asyncpg.
Все функции async. Вызывать только из async контекста.
"""
import asyncpg
import os
import json
from config import SLOTS as _DEFAULT_SLOTS

_pool: asyncpg.Pool | None = None


async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                name TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name TEXT,
                phone TEXT,
                slot TEXT,
                lang TEXT DEFAULT 'ru',
                reminded BOOLEAN DEFAULT FALSE,
                pay_reminded BOOLEAN DEFAULT FALSE,
                cancelled BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS slots (
                slot TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name TEXT,
                rating INT,
                comment TEXT
            );

            CREATE TABLE IF NOT EXISTS mood_entries (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name TEXT,
                mood INT,
                created_at DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS diary_entries (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name TEXT,
                location TEXT,
                sensation TEXT,
                intensity INT,
                emotion TEXT,
                created_at DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS checkin_entries (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name TEXT,
                text TEXT,
                created_at DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS checkin_subscribed (
                user_id BIGINT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS admin_notes (
                user_id BIGINT PRIMARY KEY,
                note TEXT
            );

            CREATE TABLE IF NOT EXISTS reschedule_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name TEXT,
                old_slot TEXT,
                new_slot TEXT,
                done BOOLEAN DEFAULT FALSE
            );
        """)

        # Заполняем слоты по умолчанию если таблица пустая
        count = await conn.fetchval("SELECT COUNT(*) FROM slots")
        if count == 0:
            for slot in _DEFAULT_SLOTS:
                await conn.execute("INSERT INTO slots(slot) VALUES($1) ON CONFLICT DO NOTHING", slot)


def _conn():
    return _pool.acquire()


# ─── Users ────────────────────────────────────────────────────────────────────

async def register_user(user_id: int, lang: str, name: str = ""):
    async with _conn() as conn:
        await conn.execute("""
            INSERT INTO users(user_id, lang, name) VALUES($1,$2,$3)
            ON CONFLICT(user_id) DO UPDATE SET lang=$2, name=CASE WHEN $3='' THEN users.name ELSE $3 END
        """, user_id, lang, name)

async def get_all_users() -> dict:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT user_id, lang, name FROM users")
        return {r["user_id"]: {"lang": r["lang"], "name": r["name"]} for r in rows}


# ─── Bookings ─────────────────────────────────────────────────────────────────

async def add_booking(user_id: int, name: str, phone: str, slot: str, lang: str):
    await register_user(user_id, lang, name)
    async with _conn() as conn:
        await conn.execute("""
            INSERT INTO bookings(user_id,name,phone,slot,lang)
            VALUES($1,$2,$3,$4,$5)
        """, user_id, name, phone, slot, lang)
        await conn.execute("DELETE FROM slots WHERE slot=$1", slot)

async def get_all_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM bookings WHERE cancelled=FALSE ORDER BY id")
        return [dict(r) for r in rows]

async def get_booking_by_user(user_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE user_id=$1 AND cancelled=FALSE ORDER BY id DESC LIMIT 1",
            user_id
        )
        return dict(row) if row else None

async def get_booking_by_index(n: int) -> dict | None:
    bookings = await get_all_bookings()
    if 1 <= n <= len(bookings):
        return bookings[n - 1]
    return None

async def cancel_booking(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET cancelled=TRUE WHERE id=$1", booking["id"])
        await conn.execute("INSERT INTO slots(slot) VALUES($1) ON CONFLICT DO NOTHING", booking["slot"])

async def change_booking_slot(booking: dict, new_slot: str):
    async with _conn() as conn:
        await conn.execute("INSERT INTO slots(slot) VALUES($1) ON CONFLICT DO NOTHING", booking["slot"])
        await conn.execute("UPDATE bookings SET slot=$1 WHERE id=$2", new_slot, booking["id"])
        await conn.execute("DELETE FROM slots WHERE slot=$1", new_slot)

async def get_unreminded_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM bookings WHERE cancelled=FALSE AND reminded=FALSE")
        return [dict(r) for r in rows]

async def get_unpay_reminded_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM bookings WHERE cancelled=FALSE AND pay_reminded=FALSE")
        return [dict(r) for r in rows]

async def mark_reminded(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET reminded=TRUE WHERE id=$1", booking["id"])

async def mark_pay_reminded(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET pay_reminded=TRUE WHERE id=$1", booking["id"])


# ─── Slots ────────────────────────────────────────────────────────────────────

async def get_all_slots() -> list[str]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT slot FROM slots ORDER BY slot")
        return [r["slot"] for r in rows]

async def get_free_slots() -> list[str]:
    return await get_all_slots()

async def add_slot(slot: str) -> bool:
    async with _conn() as conn:
        try:
            await conn.execute("INSERT INTO slots(slot) VALUES($1)", slot)
            return True
        except asyncpg.UniqueViolationError:
            return False

async def remove_slot(slot: str) -> bool:
    async with _conn() as conn:
        result = await conn.execute("DELETE FROM slots WHERE slot=$1", slot)
        return result != "DELETE 0"

# booked_slots — для совместимости (список занятых)
async def get_booked_slots() -> set[str]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT slot FROM bookings WHERE cancelled=FALSE")
        return {r["slot"] for r in rows}


# ─── Reschedule ───────────────────────────────────────────────────────────────

async def add_reschedule(user_id: int, name: str, old_slot: str, new_slot: str) -> dict:
    async with _conn() as conn:
        row = await conn.fetchrow("""
            INSERT INTO reschedule_requests(user_id,name,old_slot,new_slot)
            VALUES($1,$2,$3,$4) RETURNING *
        """, user_id, name, old_slot, new_slot)
        return dict(row)

async def get_pending_reschedules() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM reschedule_requests WHERE done=FALSE ORDER BY id")
        return [dict(r) for r in rows]

async def get_reschedule_by_index(idx: int) -> dict | None:
    pending = await get_pending_reschedules()
    if 0 <= idx < len(pending):
        return pending[idx]
    return None

async def resolve_reschedule(req: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE reschedule_requests SET done=TRUE WHERE id=$1", req["id"])


# ─── Reviews ──────────────────────────────────────────────────────────────────

async def add_review(user_id: int, name: str, rating: int, comment: str):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO reviews(user_id,name,rating,comment) VALUES($1,$2,$3,$4)",
            user_id, name, rating, comment
        )

async def get_all_reviews() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM reviews ORDER BY id")
        return [dict(r) for r in rows]


# ─── Mood ─────────────────────────────────────────────────────────────────────

async def save_mood_with_date(user_id: int, name: str, mood: int):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO mood_entries(user_id,name,mood) VALUES($1,$2,$3)",
            user_id, name, mood
        )

async def get_mood_entries() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT DISTINCT ON (user_id) * FROM mood_entries ORDER BY user_id, id DESC")
        return [dict(r) for r in rows]

async def get_user_mood_history(user_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mood_entries WHERE user_id=$1 ORDER BY id DESC LIMIT 7",
            user_id
        )
        return [dict(r) for r in reversed(rows)]


# ─── Diary ────────────────────────────────────────────────────────────────────

async def save_diary(user_id: int, name: str, location: str, sensation: str, intensity: int, emotion: str):
    async with _conn() as conn:
        await conn.execute("""
            INSERT INTO diary_entries(user_id,name,location,sensation,intensity,emotion)
            VALUES($1,$2,$3,$4,$5,$6)
        """, user_id, name, location, sensation, intensity, emotion)

async def get_diary_entries() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM diary_entries ORDER BY id DESC LIMIT 50")
        return [dict(r) for r in rows]


# ─── Checkin ──────────────────────────────────────────────────────────────────

async def subscribe_checkin(user_id: int):
    async with _conn() as conn:
        await conn.execute("INSERT INTO checkin_subscribed(user_id) VALUES($1) ON CONFLICT DO NOTHING", user_id)

async def unsubscribe_checkin(user_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM checkin_subscribed WHERE user_id=$1", user_id)

async def is_checkin_subscribed(user_id: int) -> bool:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT 1 FROM checkin_subscribed WHERE user_id=$1", user_id)
        return row is not None

async def get_subscribed_users() -> list[int]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT user_id FROM checkin_subscribed")
        return [r["user_id"] for r in rows]

async def save_checkin(user_id: int, name: str, text: str):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO checkin_entries(user_id,name,text) VALUES($1,$2,$3)",
            user_id, name, text
        )

async def get_checkin_entries() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM checkin_entries ORDER BY id DESC LIMIT 50")
        return [dict(r) for r in rows]


# ─── Admin notes ──────────────────────────────────────────────────────────────

async def set_note(user_id: int, note: str):
    async with _conn() as conn:
        await conn.execute("""
            INSERT INTO admin_notes(user_id,note) VALUES($1,$2)
            ON CONFLICT(user_id) DO UPDATE SET note=$2
        """, user_id, note)

async def get_note(user_id: int) -> str:
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT note FROM admin_notes WHERE user_id=$1", user_id)
        return row["note"] if row else ""

async def get_all_notes() -> dict:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM admin_notes")
        return {r["user_id"]: r["note"] for r in rows}


# ─── Analytics ────────────────────────────────────────────────────────────────

async def get_analytics() -> dict:
    async with _conn() as conn:
        return {
            "users": await conn.fetchval("SELECT COUNT(*) FROM users"),
            "bookings": await conn.fetchval("SELECT COUNT(*) FROM bookings WHERE cancelled=FALSE"),
            "slots_free": await conn.fetchval("SELECT COUNT(*) FROM slots"),
            "reviews": await conn.fetchval("SELECT COUNT(*) FROM reviews"),
            "avg_rating": await conn.fetchval("SELECT AVG(rating) FROM reviews") or 0,
            "avg_mood": await conn.fetchval("SELECT AVG(mood) FROM mood_entries") or 0,
            "diary": await conn.fetchval("SELECT COUNT(*) FROM diary_entries"),
            "checkins": await conn.fetchval("SELECT COUNT(*) FROM checkin_entries"),
        }
