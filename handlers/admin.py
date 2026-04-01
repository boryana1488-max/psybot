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
    from config import SLOTS
    free = storage.get_free_slots(SLOTS)
    taken = storage.booked_slots

    lines = ["📅 Слоты:\n"]
    for s in SLOTS:
        icon = "🔴" if s in taken else "🟢"
        lines.append(f"{icon} {s}")

    await message.answer("\n".join(lines))
