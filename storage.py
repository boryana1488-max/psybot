"""
storage.py — PostgreSQL через asyncpg.
Слоты хранят конкретную дату: "15.04 Пятница 10:00"
"""
import asyncpg
import os
from config import SLOT_TEMPLATES

_pool: asyncpg.Pool | None = None


async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    async with _pool.acquire() as conn:

        # ── Создаём таблицы ───────────────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                lang    TEXT DEFAULT 'ru',
                name    TEXT DEFAULT '',
                tz      TEXT DEFAULT 'tz_kyiv'
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id           SERIAL PRIMARY KEY,
                user_id      BIGINT,
                name         TEXT,
                phone        TEXT,
                slot         TEXT,
                slot_date    DATE,
                lang         TEXT DEFAULT 'ru',
                reminded     BOOLEAN DEFAULT FALSE,
                reminded_1h  BOOLEAN DEFAULT FALSE,
                pay_reminded BOOLEAN DEFAULT FALSE,
                paid         BOOLEAN DEFAULT FALSE,
                cancelled    BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS slots (
                id        SERIAL PRIMARY KEY,
                slot      TEXT UNIQUE,
                slot_date DATE,
                slot_time TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id      SERIAL PRIMARY KEY,
                user_id BIGINT,
                name    TEXT,
                rating  INT,
                comment TEXT
            );

            CREATE TABLE IF NOT EXISTS mood_entries (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT,
                name       TEXT,
                mood       INT,
                created_at DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS diary_entries (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT,
                name       TEXT,
                location   TEXT,
                sensation  TEXT,
                intensity  INT,
                emotion    TEXT,
                created_at DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS checkin_entries (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT,
                name       TEXT,
                text       TEXT,
                created_at DATE DEFAULT CURRENT_DATE
            );

            CREATE TABLE IF NOT EXISTS checkin_subscribed (
                user_id BIGINT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS admin_notes (
                user_id BIGINT PRIMARY KEY,
                note    TEXT
            );

            CREATE TABLE IF NOT EXISTS reschedule_requests (
                id       SERIAL PRIMARY KEY,
                user_id  BIGINT,
                name     TEXT,
                old_slot TEXT,
                new_slot TEXT,
                done     BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS questionnaires (
                user_id BIGINT PRIMARY KEY,
                goal    TEXT DEFAULT '',
                request TEXT DEFAULT '',
                source  TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS completed_sessions (
                id           SERIAL PRIMARY KEY,
                booking_id   INT,
                completed_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Миграции: добавляем колонки если их нет ───────────────────────────
        migrations = [
            "ALTER TABLE users     ADD COLUMN IF NOT EXISTS tz           TEXT    DEFAULT 'tz_kyiv'",
            "ALTER TABLE bookings  ADD COLUMN IF NOT EXISTS slot_date    DATE",
            "ALTER TABLE bookings  ADD COLUMN IF NOT EXISTS reminded_1h  BOOLEAN DEFAULT FALSE",
            "ALTER TABLE bookings  ADD COLUMN IF NOT EXISTS pay_reminded BOOLEAN DEFAULT FALSE",
            "ALTER TABLE bookings  ADD COLUMN IF NOT EXISTS paid         BOOLEAN DEFAULT FALSE",
            "ALTER TABLE slots     ADD COLUMN IF NOT EXISTS slot_date    DATE",
            "ALTER TABLE slots     ADD COLUMN IF NOT EXISTS slot_time    TEXT    DEFAULT ''",
        ]
        for sql in migrations:
            try:
                await conn.execute(sql)
            except Exception:
                pass  # колонка уже есть


def _conn():
    return _pool.acquire()


# ─── Users ────────────────────────────────────────────────────────────────────

async def register_user(user_id: int, lang: str, name: str = "", tz: str = "tz_kyiv"):
    async with _conn() as conn:
        await conn.execute(
            """
            INSERT INTO users(user_id, lang, name, tz) VALUES($1,$2,$3,$4)
            ON CONFLICT(user_id) DO UPDATE
            SET lang=$2, tz=$4,
                name=CASE WHEN $3='' THEN users.name ELSE $3 END
            """,
            user_id, lang, name, tz
        )

async def get_all_users() -> dict:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT user_id, lang, name, tz FROM users")
        return {
            r["user_id"]: {"lang": r["lang"], "name": r["name"], "tz": r["tz"]}
            for r in rows
        }


# ─── Slots ────────────────────────────────────────────────────────────────────

async def get_all_slots() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT slot, slot_date, slot_time FROM slots ORDER BY slot_date NULLS LAST, slot_time"
        )
        return [dict(r) for r in rows]

async def get_free_slots() -> list[dict]:
    return await get_all_slots()

async def add_slot(slot: str, slot_date=None, slot_time: str = "") -> bool:
    async with _conn() as conn:
        try:
            await conn.execute(
                "INSERT INTO slots(slot, slot_date, slot_time) VALUES($1,$2,$3)",
                slot, slot_date, slot_time
            )
            return True
        except asyncpg.UniqueViolationError:
            return False

async def remove_slot(slot: str) -> bool:
    async with _conn() as conn:
        result = await conn.execute("DELETE FROM slots WHERE slot=$1", slot)
        return result != "DELETE 0"

async def get_booked_slots() -> set[str]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT slot FROM bookings WHERE cancelled=FALSE")
        return {r["slot"] for r in rows}

async def generate_slots_for_week():
    """Генерирует слоты на ближайшие 2 недели из шаблонов."""
    from datetime import date, timedelta
    DAYS = {
        "Понедельник": 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
        "Пятница": 4, "Суббота": 5, "Воскресенье": 6,
    }
    today = date.today()
    booked = await get_booked_slots()
    existing = {s["slot"] for s in await get_all_slots()}

    for template in SLOT_TEMPLATES:
        for day_name, day_num in DAYS.items():
            if template.startswith(day_name):
                time_part = template.replace(day_name, "").strip()
                days_ahead = (day_num - today.weekday()) % 7 or 7
                for week in range(2):
                    slot_date = today + timedelta(days=days_ahead + week * 7)
                    slot_str = f"{slot_date.strftime('%d.%m')} {template}"
                    if slot_str not in existing and slot_str not in booked:
                        await add_slot(slot_str, slot_date, time_part)
                break


# ─── Bookings ─────────────────────────────────────────────────────────────────

async def add_booking(user_id: int, name: str, phone: str, slot: str, lang: str):
    await register_user(user_id, lang, name)
    async with _conn() as conn:
        row = await conn.fetchrow("SELECT slot_date FROM slots WHERE slot=$1", slot)
        slot_date = row["slot_date"] if row else None
        await conn.execute(
            """
            INSERT INTO bookings(user_id, name, phone, slot, slot_date, lang)
            VALUES($1,$2,$3,$4,$5,$6)
            """,
            user_id, name, phone, slot, slot_date, lang
        )
        await conn.execute("DELETE FROM slots WHERE slot=$1", slot)

async def get_all_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bookings WHERE cancelled=FALSE ORDER BY slot_date NULLS LAST, id"
        )
        return [dict(r) for r in rows]

async def get_booking_by_user(user_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bookings WHERE user_id=$1 AND cancelled=FALSE ORDER BY id DESC LIMIT 1",
            user_id
        )
        return dict(row) if row else None

async def get_user_bookings(user_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bookings WHERE user_id=$1 ORDER BY id DESC",
            user_id
        )
        return [dict(r) for r in rows]

async def get_booking_by_index(n: int) -> dict | None:
    bookings = await get_all_bookings()
    if 1 <= n <= len(bookings):
        return bookings[n - 1]
    return None

async def cancel_booking(booking: dict):
    from datetime import date
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET cancelled=TRUE WHERE id=$1", booking["id"])
        if booking.get("slot_date") and booking["slot_date"] >= date.today():
            await conn.execute(
                "INSERT INTO slots(slot, slot_date) VALUES($1,$2) ON CONFLICT DO NOTHING",
                booking["slot"], booking["slot_date"]
            )

async def change_booking_slot(booking: dict, new_slot: str):
    from datetime import date
    async with _conn() as conn:
        if booking.get("slot_date") and booking["slot_date"] >= date.today():
            await conn.execute(
                "INSERT INTO slots(slot, slot_date) VALUES($1,$2) ON CONFLICT DO NOTHING",
                booking["slot"], booking["slot_date"]
            )
        row = await conn.fetchrow("SELECT slot_date FROM slots WHERE slot=$1", new_slot)
        new_date = row["slot_date"] if row else None
        await conn.execute(
            "UPDATE bookings SET slot=$1, slot_date=$2 WHERE id=$3",
            new_slot, new_date, booking["id"]
        )
        await conn.execute("DELETE FROM slots WHERE slot=$1", new_slot)

async def mark_paid(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET paid=TRUE WHERE id=$1", booking["id"])

async def get_unreminded_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bookings WHERE cancelled=FALSE AND reminded=FALSE"
        )
        return [dict(r) for r in rows]

async def get_unreminded_1h_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bookings WHERE cancelled=FALSE AND reminded_1h=FALSE"
        )
        return [dict(r) for r in rows]

async def get_unpay_reminded_bookings() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bookings WHERE cancelled=FALSE AND pay_reminded=FALSE"
        )
        return [dict(r) for r in rows]

async def mark_reminded(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET reminded=TRUE WHERE id=$1", booking["id"])

async def mark_reminded_1h(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET reminded_1h=TRUE WHERE id=$1", booking["id"])

async def mark_pay_reminded(booking: dict):
    async with _conn() as conn:
        await conn.execute("UPDATE bookings SET pay_reminded=TRUE WHERE id=$1", booking["id"])

async def get_week_schedule() -> list[dict]:
    from datetime import date, timedelta
    async with _conn() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM bookings
            WHERE cancelled=FALSE
            AND slot_date >= $1 AND slot_date <= $2
            ORDER BY slot_date, id
            """,
            date.today(), date.today() + timedelta(days=7)
        )
        return [dict(r) for r in rows]

async def export_bookings_csv() -> str:
    bookings = await get_all_bookings()
    lines = ["#,Имя,Телефон,Слот,Дата,Оплачено"]
    for i, b in enumerate(bookings, 1):
        paid = "да" if b.get("paid") else "нет"
        lines.append(f"{i},{b['name']},{b['phone']},{b['slot']},{b.get('slot_date','')},{paid}")
    return "\n".join(lines)


# ─── Reschedule ───────────────────────────────────────────────────────────────

async def add_reschedule(user_id: int, name: str, old_slot: str, new_slot: str) -> dict:
    async with _conn() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO reschedule_requests(user_id, name, old_slot, new_slot)
            VALUES($1,$2,$3,$4) RETURNING *
            """,
            user_id, name, old_slot, new_slot
        )
        return dict(row)

async def get_pending_reschedules() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM reschedule_requests WHERE done=FALSE ORDER BY id"
        )
        return [dict(r) for r in rows]

async def resolve_reschedule(req: dict):
    async with _conn() as conn:
        await conn.execute(
            "UPDATE reschedule_requests SET done=TRUE WHERE id=$1", req["id"]
        )


# ─── Reviews ──────────────────────────────────────────────────────────────────

async def add_review(user_id: int, name: str, rating: int, comment: str):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO reviews(user_id, name, rating, comment) VALUES($1,$2,$3,$4)",
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
            "INSERT INTO mood_entries(user_id, name, mood) VALUES($1,$2,$3)",
            user_id, name, mood
        )

async def get_mood_entries() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT ON (user_id) * FROM mood_entries ORDER BY user_id, id DESC"
        )
        return [dict(r) for r in rows]

async def get_user_mood_history(user_id: int) -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mood_entries WHERE user_id=$1 ORDER BY id DESC LIMIT 7",
            user_id
        )
        return [dict(r) for r in reversed(rows)]


# ─── Diary ────────────────────────────────────────────────────────────────────

async def save_diary(user_id: int, name: str, location: str, sensation: str,
                     intensity: int, emotion: str):
    async with _conn() as conn:
        await conn.execute(
            """
            INSERT INTO diary_entries(user_id, name, location, sensation, intensity, emotion)
            VALUES($1,$2,$3,$4,$5,$6)
            """,
            user_id, name, location, sensation, intensity, emotion
        )

async def get_diary_entries() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM diary_entries ORDER BY id DESC LIMIT 50"
        )
        return [dict(r) for r in rows]


# ─── Checkin ──────────────────────────────────────────────────────────────────

async def subscribe_checkin(user_id: int):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO checkin_subscribed(user_id) VALUES($1) ON CONFLICT DO NOTHING",
            user_id
        )

async def unsubscribe_checkin(user_id: int):
    async with _conn() as conn:
        await conn.execute("DELETE FROM checkin_subscribed WHERE user_id=$1", user_id)

async def is_checkin_subscribed(user_id: int) -> bool:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM checkin_subscribed WHERE user_id=$1", user_id
        )
        return row is not None

async def get_subscribed_users() -> list[int]:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT user_id FROM checkin_subscribed")
        return [r["user_id"] for r in rows]

async def save_checkin(user_id: int, name: str, text: str):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO checkin_entries(user_id, name, text) VALUES($1,$2,$3)",
            user_id, name, text
        )

async def get_checkin_entries() -> list[dict]:
    async with _conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM checkin_entries ORDER BY id DESC LIMIT 50"
        )
        return [dict(r) for r in rows]


# ─── Admin notes ──────────────────────────────────────────────────────────────

async def set_note(user_id: int, note: str):
    async with _conn() as conn:
        await conn.execute(
            """
            INSERT INTO admin_notes(user_id, note) VALUES($1,$2)
            ON CONFLICT(user_id) DO UPDATE SET note=$2
            """,
            user_id, note
        )

async def get_note(user_id: int) -> str:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT note FROM admin_notes WHERE user_id=$1", user_id
        )
        return row["note"] if row else ""

async def get_all_notes() -> dict:
    async with _conn() as conn:
        rows = await conn.fetch("SELECT * FROM admin_notes")
        return {r["user_id"]: r["note"] for r in rows}


# ─── Questionnaire ────────────────────────────────────────────────────────────

async def save_questionnaire(user_id: int, goal: str, request: str, source: str):
    async with _conn() as conn:
        await conn.execute(
            """
            INSERT INTO questionnaires(user_id, goal, request, source)
            VALUES($1,$2,$3,$4)
            ON CONFLICT(user_id) DO UPDATE SET goal=$2, request=$3, source=$4
            """,
            user_id, goal, request, source
        )

async def get_questionnaire(user_id: int) -> dict | None:
    async with _conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM questionnaires WHERE user_id=$1", user_id
        )
        return dict(row) if row else None

async def has_questionnaire(user_id: int) -> bool:
    return (await get_questionnaire(user_id)) is not None


# ─── Sessions ─────────────────────────────────────────────────────────────────

async def complete_session(booking_id: int):
    async with _conn() as conn:
        await conn.execute(
            "INSERT INTO completed_sessions(booking_id) VALUES($1)", booking_id
        )
        await conn.execute(
            "UPDATE bookings SET cancelled=TRUE WHERE id=$1", booking_id
        )

async def get_client_stats(user_id: int) -> dict:
    async with _conn() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM bookings WHERE user_id=$1", user_id
        ) or 0
        paid = await conn.fetchval(
            "SELECT COUNT(*) FROM bookings WHERE user_id=$1 AND paid=TRUE", user_id
        ) or 0
        completed = await conn.fetchval(
            """
            SELECT COUNT(*) FROM completed_sessions cs
            JOIN bookings b ON b.id=cs.booking_id WHERE b.user_id=$1
            """,
            user_id
        ) or 0
        mood_row = await conn.fetchrow(
            "SELECT mood FROM mood_entries WHERE user_id=$1 ORDER BY id DESC LIMIT 1",
            user_id
        )
        return {
            "total": int(total),
            "paid": int(paid),
            "completed": int(completed),
            "last_mood": mood_row["mood"] if mood_row else None,
        }


# ─── Analytics ────────────────────────────────────────────────────────────────

async def get_analytics() -> dict:
    async with _conn() as conn:
        avg_rating = await conn.fetchval("SELECT AVG(rating) FROM reviews")
        avg_mood = await conn.fetchval("SELECT AVG(mood) FROM mood_entries")
        return {
            "users": await conn.fetchval("SELECT COUNT(*) FROM users") or 0,
            "bookings": await conn.fetchval(
                "SELECT COUNT(*) FROM bookings WHERE cancelled=FALSE"
            ) or 0,
            "paid": await conn.fetchval(
                "SELECT COUNT(*) FROM bookings WHERE cancelled=FALSE AND paid=TRUE"
            ) or 0,
            "slots_free": await conn.fetchval("SELECT COUNT(*) FROM slots") or 0,
            "reviews": await conn.fetchval("SELECT COUNT(*) FROM reviews") or 0,
            "avg_rating": float(avg_rating) if avg_rating else 0.0,
            "avg_mood": float(avg_mood) if avg_mood else 0.0,
            "diary": await conn.fetchval("SELECT COUNT(*) FROM diary_entries") or 0,
            "checkins": await conn.fetchval("SELECT COUNT(*) FROM checkin_entries") or 0,
        }


# ─── AI доступ ────────────────────────────────────────────────────────────────

async def _ensure_ai_table(conn):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_access (
            user_id        BIGINT PRIMARY KEY,
            sos_left       INT DEFAULT 10,
            practice_left  INT DEFAULT 10,
            reset_month    INT DEFAULT 0,
            reset_year     INT DEFAULT 0
        )
    """)
    # Миграция: добавить колонки если нет
    for col, default in [("reset_month","0"), ("reset_year","0")]:
        try:
            await conn.execute(
                f"ALTER TABLE ai_access ADD COLUMN IF NOT EXISTS {col} INT DEFAULT {default}"
            )
        except Exception:
            pass

async def _check_monthly_reset(conn, user_id: int):
    """Сбрасывает лимиты если наступил новый месяц."""
    from datetime import date
    now = date.today()
    row = await conn.fetchrow(
        "SELECT reset_month, reset_year FROM ai_access WHERE user_id=$1", user_id
    )
    if row and (row["reset_month"] != now.month or row["reset_year"] != now.year):
        await conn.execute(
            "UPDATE ai_access SET sos_left=10, practice_left=10, "
            "reset_month=$2, reset_year=$3 WHERE user_id=$1",
            user_id, now.month, now.year
        )

async def get_ai_access(user_id: int) -> dict | None:
    from datetime import date
    now = date.today()
    async with _conn() as conn:
        try:
            await _ensure_ai_table(conn)
            # Создаём запись если нет
            await conn.execute("""
                INSERT INTO ai_access(user_id, sos_left, practice_left, reset_month, reset_year)
                VALUES($1, 10, 10, $2, $3)
                ON CONFLICT(user_id) DO NOTHING
            """, user_id, now.month, now.year)
            await _check_monthly_reset(conn, user_id)
            row = await conn.fetchrow(
                "SELECT * FROM ai_access WHERE user_id=$1", user_id
            )
            return dict(row) if row else None
        except Exception:
            return None

async def decrement_ai_sos(user_id: int) -> int:
    async with _conn() as conn:
        try:
            await _ensure_ai_table(conn)
            await _check_monthly_reset(conn, user_id)
            row = await conn.fetchrow(
                "UPDATE ai_access SET sos_left=GREATEST(sos_left-1,0) "
                "WHERE user_id=$1 RETURNING sos_left",
                user_id
            )
            return row["sos_left"] if row else 0
        except Exception:
            return 0

async def decrement_ai_practice(user_id: int) -> int:
    async with _conn() as conn:
        try:
            await _ensure_ai_table(conn)
            await _check_monthly_reset(conn, user_id)
            row = await conn.fetchrow(
                "UPDATE ai_access SET practice_left=GREATEST(practice_left-1,0) "
                "WHERE user_id=$1 RETURNING practice_left",
                user_id
            )
            return row["practice_left"] if row else 0
        except Exception:
            return 0


# ─── CRM теги / статусы ───────────────────────────────────────────────────────

async def set_client_tag(user_id: int, tag: str):
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS client_tags (
                user_id BIGINT PRIMARY KEY,
                tag     TEXT DEFAULT 'new',
                status  TEXT DEFAULT 'active'
            )
        """)
        await conn.execute("""
            INSERT INTO client_tags(user_id, tag)
            VALUES($1,$2)
            ON CONFLICT(user_id) DO UPDATE SET tag=$2
        """, user_id, tag)

async def set_client_status(user_id: int, status: str):
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS client_tags (
                user_id BIGINT PRIMARY KEY,
                tag     TEXT DEFAULT 'new',
                status  TEXT DEFAULT 'active'
            )
        """)
        await conn.execute("""
            INSERT INTO client_tags(user_id, status)
            VALUES($1,$2)
            ON CONFLICT(user_id) DO UPDATE SET status=$2
        """, user_id, status)

async def get_client_tag(user_id: int) -> dict:
    async with _conn() as conn:
        try:
            row = await conn.fetchrow(
                "SELECT tag, status FROM client_tags WHERE user_id=$1", user_id
            )
            return dict(row) if row else {"tag": "new", "status": "active"}
        except Exception:
            return {"tag": "new", "status": "active"}

async def get_clients_by_tag(tag: str) -> list[int]:
    async with _conn() as conn:
        try:
            rows = await conn.fetch(
                "SELECT user_id FROM client_tags WHERE tag=$1", tag
            )
            return [r["user_id"] for r in rows]
        except Exception:
            return []


# ─── История сообщений (reply log) ───────────────────────────────────────────

async def log_reply(admin_to_user: bool, user_id: int, text: str):
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reply_log (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT,
                direction  TEXT,
                text       TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        direction = "admin→client" if admin_to_user else "client→admin"
        await conn.execute(
            "INSERT INTO reply_log(user_id, direction, text) VALUES($1,$2,$3)",
            user_id, direction, text
        )

async def get_reply_log(user_id: int) -> list[dict]:
    async with _conn() as conn:
        try:
            rows = await conn.fetch(
                "SELECT direction, text, created_at FROM reply_log "
                "WHERE user_id=$1 ORDER BY id DESC LIMIT 20",
                user_id
            )
            return [dict(r) for r in rows]
        except Exception:
            return []


# ─── Пакеты сессий ───────────────────────────────────────────────────────────

async def add_session_package(user_id: int, count: int):
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS session_packages (
                user_id    BIGINT PRIMARY KEY,
                sessions   INT DEFAULT 0,
                used       INT DEFAULT 0
            )
        """)
        await conn.execute("""
            INSERT INTO session_packages(user_id, sessions)
            VALUES($1,$2)
            ON CONFLICT(user_id) DO UPDATE
            SET sessions=session_packages.sessions+$2
        """, user_id, count)

async def get_session_package(user_id: int) -> dict | None:
    async with _conn() as conn:
        try:
            row = await conn.fetchrow(
                "SELECT sessions, used FROM session_packages WHERE user_id=$1",
                user_id
            )
            return dict(row) if row else None
        except Exception:
            return None

async def use_session_from_package(user_id: int) -> bool:
    async with _conn() as conn:
        try:
            row = await conn.fetchrow(
                "SELECT sessions, used FROM session_packages WHERE user_id=$1",
                user_id
            )
            if not row or (row["sessions"] - row["used"]) <= 0:
                return False
            await conn.execute(
                "UPDATE session_packages SET used=used+1 WHERE user_id=$1",
                user_id
            )
            return True
        except Exception:
            return False


# ─── Ежедневные послания (подписка) ──────────────────────────────────────────

async def toggle_daily_message(user_id: int) -> bool:
    """Переключает подписку. Возвращает True если теперь подписан."""
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_message_subscribed (
                user_id BIGINT PRIMARY KEY
            )
        """)
        row = await conn.fetchrow(
            "SELECT 1 FROM daily_message_subscribed WHERE user_id=$1", user_id
        )
        if row:
            await conn.execute(
                "DELETE FROM daily_message_subscribed WHERE user_id=$1", user_id
            )
            return False
        else:
            await conn.execute(
                "INSERT INTO daily_message_subscribed(user_id) VALUES($1) ON CONFLICT DO NOTHING",
                user_id
            )
            return True

async def get_daily_message_subscribers() -> list[int]:
    async with _conn() as conn:
        try:
            rows = await conn.fetch("SELECT user_id FROM daily_message_subscribed")
            return [r["user_id"] for r in rows]
        except Exception:
            return []

async def is_daily_subscribed(user_id: int) -> bool:
    async with _conn() as conn:
        try:
            row = await conn.fetchrow(
                "SELECT 1 FROM daily_message_subscribed WHERE user_id=$1", user_id
            )
            return row is not None
        except Exception:
            return False


# ─── Платёжный реестр ────────────────────────────────────────────────────────

async def log_payment(user_id: int, name: str, tx_id: str,
                      amount: int, purpose: str):
    async with _conn() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_log (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT,
                name       TEXT,
                tx_id      TEXT,
                amount     INT,
                purpose    TEXT,
                confirmed  BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute(
            "INSERT INTO payment_log(user_id, name, tx_id, amount, purpose)"
            " VALUES($1,$2,$3,$4,$5)",
            user_id, name, tx_id, amount, purpose
        )

async def confirm_payment(tx_id: str):
    async with _conn() as conn:
        try:
            await conn.execute(
                "UPDATE payment_log SET confirmed=TRUE WHERE tx_id=$1", tx_id
            )
        except Exception:
            pass

async def get_payment_log() -> list[dict]:
    async with _conn() as conn:
        try:
            rows = await conn.fetch(
                "SELECT * FROM payment_log ORDER BY id DESC LIMIT 100"
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

async def export_payments_csv() -> str:
    rows = await get_payment_log()
    lines = ["#,Имя,TX_ID,Сумма,Назначение,Подтверждено,Дата"]
    for i, r in enumerate(rows, 1):
        confirmed = "да" if r.get("confirmed") else "нет"
        lines.append(
            f"{i},{r['name']},{r['tx_id']},{r['amount']},"
            f"{r['purpose']},{confirmed},{str(r.get('created_at',''))[:10]}"
        )
    return "\n".join(lines)


# ─── Автоподтверждение оплаты ─────────────────────────────────────────────────

async def confirm_payment_by_tx(tx_id: str):
    async with _conn() as conn:
        try:
            await conn.execute(
                "UPDATE payment_log SET confirmed=TRUE WHERE tx_id=$1", tx_id
            )
        except Exception:
            pass

async def get_pending_payments() -> list[dict]:
    async with _conn() as conn:
        try:
            rows = await conn.fetch(
                "SELECT * FROM payment_log WHERE confirmed=FALSE ORDER BY id DESC"
            )
            return [dict(r) for r in rows]
        except Exception:
            return []
