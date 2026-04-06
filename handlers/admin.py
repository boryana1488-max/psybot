from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID
import storage

router = Router()


@router.message(Command("myid"))
async def my_id(message: Message):
    """Диагностика — любой может узнать свой ID"""
    await message.answer(
        f"🆔 Ваш Telegram ID: `{message.from_user.id}`\n\n"
        f"Текущий ADMIN_ID в боте: `{ADMIN_ID}`\n"
        f"Совпадает: {'✅ Да' if message.from_user.id == ADMIN_ID else '❌ Нет — обновите ADMIN_ID в Railway'}",
        parse_mode="Markdown"
    )


def admin_only(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID


@router.message(Command("bookings"))
async def show_bookings(message: Message):
    if not admin_only(message):
        return
    all_bookings = storage.get_all_bookings()
    if not all_bookings:
        await message.answer("Записей пока нет.")
        return
    text = f"📋 Все записи ({len(all_bookings)}):\n\n"
    for i, b in enumerate(all_bookings, 1):
        text += f"#{i} {b['name']} | {b['phone']} | {b['slot']}\n"
    await message.answer(text)


@router.message(Command("slots"))
async def show_slots(message: Message):
    if not admin_only(message):
        return
    all_slots = storage.get_all_slots()
    taken = storage.booked_slots
    if not all_slots:
        await message.answer("Слотов нет.\n\nДобавь: /addslot Пятница 15:00")
        return
    lines = ["📅 Слоты:\n"]
    for s in all_slots:
        lines.append(f"{'🔴' if s in taken else '🟢'} {s}")
    lines.append("\n➕ /addslot Пятница 15:00")
    lines.append("➖ /removeslot Пятница 15:00")
    await message.answer("\n".join(lines))


@router.message(Command("addslot"))
async def add_slot(message: Message):
    if not admin_only(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Пример: /addslot Пятница 15:00")
        return
    ok = storage.add_slot(parts[1].strip())
    await message.answer(f"✅ Добавлен: {parts[1].strip()}" if ok else "⚠️ Уже существует.")


@router.message(Command("removeslot"))
async def remove_slot(message: Message):
    if not admin_only(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Пример: /removeslot Пятница 15:00")
        return
    ok = storage.remove_slot(parts[1].strip())
    await message.answer(f"🗑 Удалён: {parts[1].strip()}" if ok else "⚠️ Не найден. Список: /slots")


@router.message(Command("mood"))
async def show_mood(message: Message):
    if not admin_only(message):
        return
    entries = storage.get_mood_entries()
    if not entries:
        await message.answer("Записей настроения нет.")
        return
    by_user: dict = {}
    for e in entries:
        by_user[e["user_id"]] = e
    emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
    lines = [f"📊 Настроение ({len(by_user)} чел.):\n"]
    for e in sorted(by_user.values(), key=lambda x: x["mood"]):
        lines.append(f"{emojis.get(e['mood'], '❓')} {e['name']} — {e['mood']}/5")
    avg = sum(e["mood"] for e in by_user.values()) / len(by_user)
    lines.append(f"\nСреднее: {avg:.1f} ⭐")
    await message.answer("\n".join(lines))


@router.message(Command("diary"))
async def show_diary(message: Message):
    if not admin_only(message):
        return
    entries = storage.get_diary_entries()
    if not entries:
        await message.answer("Записей дневника нет.")
        return
    text = f"📓 Дневник ощущений ({len(entries)} записей):\n\n"
    for e in entries[-10:]:
        text += (
            f"👤 {e['name']}\n"
            f"📍 {e['location']} | {e['sensation']} | {e['intensity']}/10 | {e['emotion']}\n\n"
        )
    await message.answer(text)


@router.message(Command("reviews"))
async def show_reviews(message: Message):
    if not admin_only(message):
        return
    all_reviews = storage.get_all_reviews()
    if not all_reviews:
        await message.answer("Отзывов нет.")
        return
    avg = sum(r["rating"] for r in all_reviews) / len(all_reviews)
    text = f"💬 Отзывы ({len(all_reviews)}) | Среднее: {avg:.1f} ⭐\n\n"
    for r in all_reviews[-10:]:
        text += f"{'⭐' * r['rating']} {r['name']}\n{r['comment']}\n\n"
    await message.answer(text)
