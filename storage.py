# Простое хранилище в памяти (данные живут пока бот запущен)
# Для постоянного хранения можно заменить на SQLite

bookings: list[dict] = []  # {"user_id": ..., "name": ..., "slot": ..., "lang": ...}
booked_slots: set[str] = set()  # занятые слоты


def add_booking(user_id: int, name: str, phone: str, slot: str, lang: str):
    bookings.append({
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "slot": slot,
        "lang": lang,
    })
    booked_slots.add(slot)


def get_all_bookings() -> list[dict]:
    return bookings


def is_slot_taken(slot: str) -> bool:
    return slot in booked_slots


def get_free_slots(all_slots: list[str]) -> list[str]:
    return [s for s in all_slots if s not in booked_slots]
