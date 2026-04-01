from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID
from texts import t
import storage

router = Router()


@router.message(Command("bookings"), F.from_user.id == ADMIN_ID)
async def show_bookings(message: Message):
    all_bookings = storage.get_all_bookings()

    if not all_bookings:
        await message.answer(t("ru", "admin_bookings_empty"))
        return

    text = t("ru", "admin_bookings_header", count=len(all_bookings))
    for i, b in enumerate(all_bookings, 1):
        text += t("ru", "admin_booking_item",
                  n=i,
                  name=b["name"],
                  phone=b["phone"],
                  slot=b["slot"])

    await message.answer(text)


@router.message(Command("slots"), F.from_user.id == ADMIN_ID)
async def show_slots(message: Message):
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


@router.message(Command("addslot"), F.from_user.id == ADMIN_ID)
async def add_slot(message: Message):
    # Формат: /addslot Пятница 15:00
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажи время после команды.\n\n"
            "Пример:\n/addslot Пятница 15:00\n/addslot Понедельник 10:00"
        )
        return

    slot = parts[1].strip()
    ok = storage.add_slot(slot)

    if ok:
        await message.answer(f"✅ Слот добавлен: *{slot}*\n\nКлиенты уже могут его выбрать.", parse_mode="Markdown")
    else:
        await message.answer(f"⚠️ Слот «{slot}» уже существует.")


@router.message(Command("removeslot"), F.from_user.id == ADMIN_ID)
async def remove_slot(message: Message):
    # Формат: /removeslot Пятница 15:00
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажи время после команды.\n\n"
            "Пример:\n/removeslot Пятница 15:00\n\n"
            "Посмотреть все слоты: /slots"
        )
        return

    slot = parts[1].strip()
    ok = storage.remove_slot(slot)

    if ok:
        await message.answer(f"🗑 Слот удалён: *{slot}*", parse_mode="Markdown")
    else:
        await message.answer(
            f"⚠️ Слот «{slot}» не найден.\n\nПосмотреть все слоты: /slots"
        )
