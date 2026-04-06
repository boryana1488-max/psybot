# Простое хранилище в памяти (данные живут пока бот запущен)
# Для постоянного хранения можно заменить на SQLite

from config import SLOTS as _DEFAULT_SLOTS

bookings: list[dict] = []       # {"user_id", "name", "phone", "slot", "lang", "reminded", "cancelled"}
booked_slots: set[str] = set()  # занятые слоты
custom_slots: list[str] = list(_DEFAULT_SLOTS)
all_users: dict[int, dict] = {} # user_id -> {"lang": ..., "name": ...}
reviews: list[dict] = []        # {"user_id", "name", "rating", "comment"}


# ─── Users ────────────────────────────────────────────────────────────────────

def register_user(user_id: int, lang: str, name: str = ""):
    all_users[user_id] = {"lang": lang, "name": name}

def get_all_users() -> dict:
    return all_users


# ─── Bookings ─────────────────────────────────────────────────────────────────

def add_booking(user_id: int, name: str, phone: str, slot: str, lang: str):
    register_user(user_id, lang, name)
    bookings.append({
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "slot": slot,
        "lang": lang,
        "reminded": False,
        "cancelled": False,
    })
    booked_slots.add(slot)

def get_all_bookings() -> list[dict]:
    return [b for b in bookings if not b.get("cancelled")]

def get_booking_by_user(user_id: int) -> dict | None:
    for b in reversed(bookings):
        if b["user_id"] == user_id and not b.get("cancelled"):
            return b
    return None

def cancel_booking_by_user(user_id: int) -> dict | None:
    for b in reversed(bookings):
        if b["user_id"] == user_id and not b.get("cancelled"):
            b["cancelled"] = True
            booked_slots.discard(b["slot"])
            return b
    return None

def get_unreminded_bookings() -> list[dict]:
    return [b for b in bookings if not b.get("cancelled") and not b.get("reminded")]

def mark_reminded(booking: dict):
    booking["reminded"] = True


# ─── Slots ────────────────────────────────────────────────────────────────────

def is_slot_taken(slot: str) -> bool:
    return slot in booked_slots

def get_free_slots(all_slots: list[str] | None = None) -> list[str]:
    slots = all_slots if all_slots is not None else custom_slots
    return [s for s in slots if s not in booked_slots]

def add_slot(slot: str) -> bool:
    if slot in custom_slots:
        return False
    custom_slots.append(slot)
    return True

def remove_slot(slot: str) -> bool:
    if slot not in custom_slots:
        return False
    custom_slots.remove(slot)
    booked_slots.discard(slot)
    return True

def get_all_slots() -> list[str]:
    return custom_slots


# ─── Reviews ──────────────────────────────────────────────────────────────────

def add_review(user_id: int, name: str, rating: int, comment: str):
    reviews.append({"user_id": user_id, "name": name, "rating": rating, "comment": comment})

def get_all_reviews() -> list[dict]:
    return reviews


# ─── Mood tracker ─────────────────────────────────────────────────────────────

mood_entries: list[dict] = []  # {"user_id", "name", "mood": 1-5}


def save_mood(user_id: int, name: str, mood: int):
    mood_entries.append({"user_id": user_id, "name": name, "mood": mood})


def get_mood_entries() -> list[dict]:
    return mood_entries


# ─── Diary of sensations ──────────────────────────────────────────────────────

diary_entries: list[dict] = []


def save_diary(user_id: int, name: str, location: str, sensation: str, intensity: int, emotion: str):
    diary_entries.append({
        "user_id": user_id, "name": name,
        "location": location, "sensation": sensation,
        "intensity": intensity, "emotion": emotion,
    })


def get_diary_entries() -> list[dict]:
    return diary_entries
