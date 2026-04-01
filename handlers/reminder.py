"""
Напоминания клиентам за день до консультации.

Запускается автоматически каждый час и проверяет слоты.
Формат слота: "Пятница 15:00" — сопоставляется с текущим днём недели.
"""

import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from config import ADMIN_ID
import storage

DAYS_RU = {
    "Понедельник": 0, "Вторник": 1, "Среда": 2,
    "Четверг": 3, "Пятница": 4, "Суббота": 5, "Воскресенье": 6,
}
DAYS_UK = {
    "Понеділок": 0, "Вівторок": 1, "Середа": 2,
    "Четвер": 3, "П'ятниця": 4, "Субота": 5, "Неділя": 6,
}


def slot_is_tomorrow(slot: str) -> bool:
    """Проверяет, что слот — завтра (по дню недели)."""
    tomorrow = (datetime.now() + timedelta(days=1)).weekday()
    for day_name, day_num in {**DAYS_RU, **DAYS_UK}.items():
        if slot.startswith(day_name) and day_num == tomorrow:
            return True
    return False


async def send_reminders(bot: Bot):
    for booking in storage.get_unreminded_bookings():
        if slot_is_tomorrow(booking["slot"]):
            lang = booking.get("lang", "ru")
            slot = booking["slot"]
            name = booking["name"]

            if lang == "uk":
                text = (
                    f"👋 {name}, нагадуємо!\n\n"
                    f"Завтра у вас консультація: 📅 {slot}\n\n"
                    f"Якщо не зможете прийти — будь ласка, скасуйте запис заздалегідь."
                )
            else:
                text = (
                    f"👋 {name}, напоминаем!\n\n"
                    f"Завтра у вас консультация: 📅 {slot}\n\n"
                    f"Если не сможете прийти — пожалуйста, отмените запись заранее."
                )

            from aiogram.utils.keyboard import InlineKeyboardBuilder
            kb = InlineKeyboardBuilder()
            kb.button(
                text="❌ Отменить запись" if lang == "ru" else "❌ Скасувати запис",
                callback_data="cancel_booking"
            )

            try:
                await bot.send_message(
                    booking["user_id"],
                    text,
                    reply_markup=kb.as_markup()
                )
                storage.mark_reminded(booking)
            except Exception:
                pass  # Пользователь мог заблокировать бота


async def reminder_loop(bot: Bot):
    """Запускается в фоне, проверяет каждый час."""
    while True:
        await send_reminders(bot)
        await asyncio.sleep(3600)  # раз в час
