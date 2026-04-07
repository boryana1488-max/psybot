"""
Напоминания:
- За 12 часов — клиенту (напоминание + оплата если не оплачено)
- За 1 час — клиенту и психологу (админу)
"""
import asyncio
import re
from datetime import datetime, timedelta, date
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
import storage
from config import ADMIN_ID

DAYS_MAP = {
    "Понедельник": 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
    "Пятница": 4, "Суббота": 5, "Воскресенье": 6,
    "Понеділок": 0, "Вівторок": 1, "Середа": 2, "Четвер": 3,
    "П'ятниця": 4, "Субота": 5, "Неділя": 6,
}


def parse_slot_datetime(booking: dict) -> datetime | None:
    """Парсит дату и время из слота вида '15.03 Пятница 15:00'"""
    slot = booking.get("slot", "")
    if booking.get("slot_date"):
        match = re.search(r"(\d+):(\d+)", slot)
        if match:
            h, m = int(match.group(1)), int(match.group(2))
            slot_date = booking["slot_date"]
            if isinstance(slot_date, date):
                return datetime(slot_date.year, slot_date.month, slot_date.day, h, m)
    return None


async def send_12h_reminders(bot: Bot):
    """За 12 часов: напоминание клиенту + напоминание об оплате если не оплачено."""
    now = datetime.now()
    for booking in await storage.get_unreminded_bookings():
        dt = parse_slot_datetime(booking)
        if not dt:
            continue
        diff_h = (dt - now).total_seconds() / 3600
        if 11.5 <= diff_h <= 12.5:
            lang = booking.get("lang", "ru")
            name = booking["name"]
            slot = booking["slot"]

            # Напоминание о записи
            text = (
                f"👋 {name}, напоминаем!\n\nЧерез 12 часов у вас консультация:\n📅 {slot}\n\nЕсли не сможете — отмените заранее."
                if lang == "ru" else
                f"👋 {name}, нагадуємо!\n\nЧерез 12 годин у вас консультація:\n📅 {slot}\n\nЯкщо не зможете — скасуйте заздалегідь."
            )
            kb = InlineKeyboardBuilder()
            kb.button(
                text="❌ Отменить запись" if lang == "ru" else "❌ Скасувати запис",
                callback_data="cancel_booking"
            )
            try:
                await bot.send_message(booking["user_id"], text, reply_markup=kb.as_markup())
                await storage.mark_reminded(booking)
            except Exception:
                pass

            # Напоминание об оплате если не оплачено
            if not booking.get("paid"):
                pay_kb = InlineKeyboardBuilder()
                pay_kb.button(
                    text="💳 Оплатить" if lang == "ru" else "💳 Оплатити",
                    callback_data="pay_consultation"
                )
                pay_text = (
                    f"💳 Не забудьте оплатить консультацию!\n\n📅 {slot}\n\nОплатите заранее, чтобы подтвердить участие."
                    if lang == "ru" else
                    f"💳 Не забудьте оплатити консультацію!\n\n📅 {slot}\n\nОплатіть заздалегідь, щоб підтвердити участь."
                )
                try:
                    await bot.send_message(booking["user_id"], pay_text, reply_markup=pay_kb.as_markup())
                    await storage.mark_pay_reminded(booking)
                except Exception:
                    pass


async def send_1h_reminders(bot: Bot):
    """За 1 час: клиенту + психологу (админу)."""
    now = datetime.now()
    for booking in await storage.get_unreminded_1h_bookings():
        dt = parse_slot_datetime(booking)
        if not dt:
            continue
        diff_h = (dt - now).total_seconds() / 3600
        if 0.75 <= diff_h <= 1.25:
            lang = booking.get("lang", "ru")
            name = booking["name"]
            slot = booking["slot"]

            # Клиенту
            client_text = (
                f"⏰ Через час у вас консультация!\n\n📅 {slot}\n\nДо встречи! 💙"
                if lang == "ru" else
                f"⏰ Через годину у вас консультація!\n\n📅 {slot}\n\nДо зустрічі! 💙"
            )
            try:
                await bot.send_message(booking["user_id"], client_text)
            except Exception:
                pass

            # Психологу
            tg_link = f"tg://user?id={booking['user_id']}"
            admin_text = (
                f"⏰ Через 1 час сессия!\n\n"
                f"👤 {name}\n"
                f"📅 {slot}\n"
                f"📞 {booking.get('phone', '—')}\n"
                f"🔗 {tg_link}"
            )
            try:
                await bot.send_message(ADMIN_ID, admin_text)
            except Exception:
                pass

            try:
                await storage.mark_reminded_1h(booking)
            except Exception:
                pass


async def slot_refresh_loop(bot: Bot):
    """Раз в день генерируем новые слоты на 2 недели вперёд."""
    while True:
        await storage.generate_slots_for_week()
        await asyncio.sleep(86400)


async def reminder_loop(bot: Bot):
    while True:
        await send_12h_reminders(bot)
        await send_1h_reminders(bot)
        await asyncio.sleep(1800)  # каждые 30 минут
