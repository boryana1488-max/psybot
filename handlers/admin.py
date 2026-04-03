from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID
from texts import t
import storage

router = Router()

# Фильтр по ID — явное сравнение int
def is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID


@router.message(Command("bookings"))
async def show_bookings(message: Message):
    if not is_admin(message):
        return
    all_bookings = storage.get_all_bookings()
    if not all_bookings:
        await message.answer(t("ru", "admin_bookings_empty"))
        return
    text = t("ru", "admin_bookings_header", count=len(all_bookings))
    for i, b in enumerate(all_bookings, 1):
        text += t("ru", "admin_booking_item", n=i, name=b["name"], phone=b["phone"], slot=b["slot"])
    await message.answer(text)


@router.message(Command("slots"))
async def show_slots(message: Message):
    if not is_admin(message):
        return
    all_slots = storage.get_all_slots()
    taken = storage.booked_slots
    if not all_slots:
        await message.answer("📅 Слотов пока нет.\n\nДобавь через /addslot")
        return
    lines = ["📅 Слоты:\n"]
    for s in all_slots:
        icon = "🔴" if s in taken else "🟢"
        lines.append(f"{icon} {s}")
    lines.append("\n➕ /addslot Пятница 15:00")
    lines.append("➖ /removeslot Пятница 15:00")
    await message.answer("\n".join(lines))


@router.message(Command("addslot"))
async def add_slot(message: Message):
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Пример:\n/addslot Пятница 15:00")
        return
    slot = parts[1].strip()
    ok = storage.add_slot(slot)
    if ok:
        await message.answer(f"✅ Слот добавлен: *{slot}*", parse_mode="Markdown")
    else:
        await message.answer(f"⚠️ Слот «{slot}» уже существует.")


@router.message(Command("removeslot"))
async def remove_slot(message: Message):
    if not is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Пример:\n/removeslot Пятница 15:00\n\nВсе слоты: /slots")
        return
    slot = parts[1].strip()
    ok = storage.remove_slot(slot)
    if ok:
        await message.answer(f"🗑 Слот удалён: *{slot}*", parse_mode="Markdown")
    else:
        await message.answer(f"⚠️ Слот «{slot}» не найден.\n\nВсе слоты: /slots")


@router.message(Command("mood"))
async def show_mood(message: Message):
    if not is_admin(message):
        return
    entries = storage.get_mood_entries()
    if not entries:
        await message.answer("😶 Записей настроения пока нет.")
        return

    # Группируем по пользователям — берём последнюю запись каждого
    by_user: dict[int, dict] = {}
    for e in entries:
        by_user[e["user_id"]] = e

    lines = [f"📊 Настроение клиентов ({len(by_user)} чел.):\n"]
    emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
    for e in sorted(by_user.values(), key=lambda x: x["mood"]):
        emoji = emojis.get(e["mood"], "❓")
        lines.append(f"{emoji} {e['name']} — {e['mood']}/5")

    avg = sum(e["mood"] for e in by_user.values()) / len(by_user)
    lines.append(f"\nСреднее: {avg:.1f} ⭐")
    await message.answer("\n".join(lines))
