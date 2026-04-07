"""
Напоминания:
- За день до сессии
- За 1 час до сессии  
- За 12 часов — об оплате
"""
import asyncio
import re
from datetime import datetime, timedelta, date
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
import storage

DAYS_MAP = {
    "Понедельник": 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
    "Пятница": 4, "Суббота": 5, "Воскресенье": 6,
    "Понеділок": 0, "Вівторок": 1, "Середа": 2, "Четвер": 3,
    "П'ятниця": 4, "Субота": 5, "Неділя": 6,
}


def parse_slot_datetime(booking: dict) -> datetime | None:
    """Парсит дату и время из слота вида '15.03 Пятница 15:00'"""
    slot = booking.get("slot", "")
    # Пробуем slot_date из БД
    if booking.get("slot_date"):
        match = re.search(r"(\d+):(\d+)", slot)
        if match:
            h, m = int(match.group(1)), int(match.group(2))
            slot_date = booking["slot_date"]
            if isinstance(slot_date, date):
                return datetime(slot_date.year, slot_date.month, slot_date.day, h, m)
    return None


async def send_reminders(bot: Bot):
    now = datetime.now()
    for booking in await storage.get_unreminded_bookings():
        dt = parse_slot_datetime(booking)
        if not dt:
            continue
        diff_h = (dt - now).total_seconds() / 3600
        if 23 <= diff_h <= 25:  # за ~24 часа
            lang = booking.get("lang", "ru")
            name = booking["name"]
            slot = booking["slot"]
            kb = InlineKeyboardBuilder()
            kb.button(
                text="❌ Отменить запись" if lang == "ru" else "❌ Скасувати запис",
                callback_data="cancel_booking"
            )
            text = (
                f"👋 {name}, напоминаем!\n\nЗавтра у вас консультация:\n📅 {slot}\n\nЕсли не сможете — отмените заранее."
                if lang == "ru" else
                f"👋 {name}, нагадуємо!\n\nЗавтра у вас консультація:\n📅 {slot}\n\nЯкщо не зможете — скасуйте заздалегідь."
            )
            try:
                await bot.send_message(booking["user_id"], text, reply_markup=kb.as_markup())
                await storage.mark_reminded(booking)
            except Exception:
                pass


async def send_1h_reminders(bot: Bot):
    now = datetime.now()
    for booking in await storage.get_unreminded_1h_bookings():
        dt = parse_slot_datetime(booking)
        if not dt:
            continue
        diff_h = (dt - now).total_seconds() / 3600
        if 0.75 <= diff_h <= 1.25:  # за ~1 час
            lang = booking.get("lang", "ru")
            text = (
                f"⏰ Через час у вас консультация!\n\n📅 {booking['slot']}\n\nДо встречи! 💙"
                if lang == "ru" else
                f"⏰ Через годину у вас консультація!\n\n📅 {booking['slot']}\n\nДо зустрічі! 💙"
            )
            try:
                await bot.send_message(booking["user_id"], text)
                await storage.mark_reminded_1h(booking)
            except Exception:
                pass


async def send_pay_reminders(bot: Bot):
    now = datetime.now()
    for booking in await storage.get_unpay_reminded_bookings():
        if booking.get("paid"):
            await storage.mark_pay_reminded(booking)
            continue
        dt = parse_slot_datetime(booking)
        if not dt:
            continue
        diff_h = (dt - now).total_seconds() / 3600
        if 11.5 <= diff_h <= 12.5:  # за ~12 часов
            lang = booking.get("lang", "ru")
            kb = InlineKeyboardBuilder()
            kb.button(
                text="💳 Оплатить" if lang == "ru" else "💳 Оплатити",
                callback_data="pay_consultation"
            )
            text = (
                f"💳 Пора оплатить консультацию!\n\n📅 {booking['slot']}\n\nОплатите заранее, чтобы подтвердить участие."
                if lang == "ru" else
                f"💳 Час оплатити консультацію!\n\n📅 {booking['slot']}\n\nОплатіть заздалегідь, щоб підтвердити участь."
            )
            try:
                await bot.send_message(booking["user_id"], text, reply_markup=kb.as_markup())
                await storage.mark_pay_reminded(booking)
            except Exception:
                pass


async def slot_refresh_loop(bot: Bot):
    """Раз в день генерируем новые слоты на 2 недели вперёд."""
    while True:
        await storage.generate_slots_for_week()
        await asyncio.sleep(86400)


async def reminder_loop(bot: Bot):
    while True:
        await send_reminders(bot)
        await send_1h_reminders(bot)
        await send_pay_reminders(bot)
        await asyncio.sleep(1800)  # каждые 30 минут
