# Простое хранилище в памяти (данные живут пока бот запущен)
# Для постоянного хранения можно заменить на SQLite

from config import SLOTS as _DEFAULT_SLOTS

bookings: list[dict] = []  # {"user_id": ..., "name": ..., "slot": ..., "lang": ...}
booked_slots: set[str] = set()  # занятые слоты
custom_slots: list[str] = list(_DEFAULT_SLOTS)  # динамические слоты (можно менять командами)


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


def get_free_slots(all_slots: list[str] | None = None) -> list[str]:
    slots = all_slots if all_slots is not None else custom_slots
    return [s for s in slots if s not in booked_slots]


def add_slot(slot: str) -> bool:
    """Добавить слот. Возвращает False если уже существует."""
    if slot in custom_slots:
        return False
    custom_slots.append(slot)
    return True


def remove_slot(slot: str) -> bool:
    """Удалить слот. Возвращает False если не найден."""
    if slot not in custom_slots:
        return False
    custom_slots.remove(slot)
    booked_slots.discard(slot)
    return True


def get_all_slots() -> list[str]:
    return custom_slots


