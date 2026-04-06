from config import SLOTS as _DEFAULT_SLOTS

bookings: list[dict] = []
booked_slots: set[str] = set()
custom_slots: list[str] = list(_DEFAULT_SLOTS)
all_users: dict[int, dict] = {}
reviews: list[dict] = []
mood_entries: list[dict] = []
diary_entries: list[dict] = []
reschedule_requests: list[dict] = []  # запросы на перенос


# ─── Users ────────────────────────────────────────────────────────────────────

def register_user(user_id: int, lang: str, name: str = ""):
    all_users[user_id] = {"lang": lang, "name": name}

def get_all_users() -> dict:
    return all_users


# ─── Bookings ─────────────────────────────────────────────────────────────────

def add_booking(user_id: int, name: str, phone: str, slot: str, lang: str):
    register_user(user_id, lang, name)
    bookings.append({
        "user_id": user_id, "name": name, "phone": phone,
        "slot": slot, "lang": lang, "reminded": False, "cancelled": False,
    })
    booked_slots.add(slot)

def get_all_bookings() -> list[dict]:
    return [b for b in bookings if not b.get("cancelled")]

def get_booking_by_user(user_id: int) -> dict | None:
    for b in reversed(bookings):
        if b["user_id"] == user_id and not b.get("cancelled"):
            return b
    return None

def get_booking_by_index(n: int) -> dict | None:
    active = get_all_bookings()
    if 1 <= n <= len(active):
        return active[n - 1]
    return None

def cancel_booking(booking: dict):
    booking["cancelled"] = True
    booked_slots.discard(booking["slot"])

def change_booking_slot(booking: dict, new_slot: str):
    booked_slots.discard(booking["slot"])
    booking["slot"] = new_slot
    booked_slots.add(new_slot)

def get_unreminded_bookings() -> list[dict]:
    return [b for b in bookings if not b.get("cancelled") and not b.get("reminded")]

def mark_reminded(booking: dict):
    booking["reminded"] = True


# ─── Reschedule requests ──────────────────────────────────────────────────────

def add_reschedule(user_id: int, name: str, old_slot: str, new_slot: str) -> dict:
    req = {"user_id": user_id, "name": name, "old_slot": old_slot, "new_slot": new_slot, "done": False}
    reschedule_requests.append(req)
    return req

def get_pending_reschedules() -> list[dict]:
    return [r for r in reschedule_requests if not r["done"]]

def resolve_reschedule(req: dict):
    req["done"] = True


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


# ─── Mood ─────────────────────────────────────────────────────────────────────

def save_mood(user_id: int, name: str, mood: int):
    mood_entries.append({"user_id": user_id, "name": name, "mood": mood})

def get_mood_entries() -> list[dict]:
    return mood_entries


# ─── Diary ────────────────────────────────────────────────────────────────────

def save_diary(user_id: int, name: str, location: str, sensation: str, intensity: int, emotion: str):
    diary_entries.append({
        "user_id": user_id, "name": name, "location": location,
        "sensation": sensation, "intensity": intensity, "emotion": emotion,
    })

def get_diary_entries() -> list[dict]:
    return diary_entries


# ─── Evening check-in ─────────────────────────────────────────────────────────

checkin_entries: list[dict] = []  # {user_id, name, text, date}
checkin_subscribed: set[int] = set()  # кто подписан на вечерний чек-ин


def subscribe_checkin(user_id: int):
    checkin_subscribed.add(user_id)

def unsubscribe_checkin(user_id: int):
    checkin_subscribed.discard(user_id)

def is_checkin_subscribed(user_id: int) -> bool:
    return user_id in checkin_subscribed

def save_checkin(user_id: int, name: str, text: str):
    from datetime import date
    checkin_entries.append({"user_id": user_id, "name": name, "text": text, "date": str(date.today())})

def get_checkin_entries() -> list[dict]:
    return checkin_entries

def get_subscribed_users() -> set[int]:
    return checkin_subscribed


# ─── Mood history (for progress) ─────────────────────────────────────────────

mood_history: list[dict] = []  # {user_id, name, mood, date}


def save_mood_with_date(user_id: int, name: str, mood: int):
    from datetime import date
    mood_history.append({"user_id": user_id, "name": name, "mood": mood, "date": str(date.today())})
    # Обновляем и общий список
    mood_entries.append({"user_id": user_id, "name": name, "mood": mood})

def get_user_mood_history(user_id: int) -> list[dict]:
    return [e for e in mood_history if e["user_id"] == user_id][-7:]  # последние 7


# ─── Admin notes ──────────────────────────────────────────────────────────────

admin_notes: dict[int, str] = {}  # user_id -> note


def set_note(user_id: int, note: str):
    admin_notes[user_id] = note

def get_note(user_id: int) -> str:
    return admin_notes.get(user_id, "")

def get_all_notes() -> dict:
    return admin_notes
