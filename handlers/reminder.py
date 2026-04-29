"""
Напоминания:
- За день до сессии
- За 1 час до сессии
- За 12 часов — об оплате
- Перезапись после завершённой сессии (через ~24ч)
- Ежедневные послания в 10:00
- Авто-генерация слотов раз в сутки
"""
import asyncio
import re
from datetime import datetime, timedelta, date
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
import storage
from affirmations import get_random_daily_message as _get_msg


def parse_slot_dt(booking: dict) -> datetime | None:
    slot_date = booking.get("slot_date")
    if not slot_date:
        return None
    match = re.search(r"(\d+):(\d+)", booking.get("slot", ""))
    if not match:
        return None
    h, m = int(match.group(1)), int(match.group(2))
    if isinstance(slot_date, date):
        return datetime(slot_date.year, slot_date.month, slot_date.day, h, m)
    return None


async def send_day_reminders(bot: Bot):
    now = datetime.now()
    for b in await storage.get_unreminded_bookings():
        dt = parse_slot_dt(b)
        if not dt:
            continue
        diff = (dt - now).total_seconds() / 3600
        if 23 <= diff <= 25:
            lang = b.get("lang", "ru")
            kb = InlineKeyboardBuilder()
            kb.button(
                text="❌ Отменить запись" if lang == "ru" else "❌ Скасувати запис",
                callback_data="cancel_booking"
            )
            text = (
                "👋 " + b["name"] + ", напоминаем!\n\n"
                "Завтра у вас консультация:\n📅 " + b["slot"] + "\n\n"
                "Если не сможете — отмените заранее."
                if lang == "ru" else
                "👋 " + b["name"] + ", нагадуємо!\n\n"
                "Завтра у вас консультація:\n📅 " + b["slot"] + "\n\n"
                "Якщо не зможете — скасуйте заздалегідь."
            )
            try:
                await bot.send_message(b["user_id"], text, reply_markup=kb.as_markup())
                await storage.mark_reminded(b)
            except Exception:
                pass


async def send_1h_reminders(bot: Bot):
    now = datetime.now()
    for b in await storage.get_unreminded_1h_bookings():
        dt = parse_slot_dt(b)
        if not dt:
            continue
        diff = (dt - now).total_seconds() / 3600
        if 0.75 <= diff <= 1.25:
            lang = b.get("lang", "ru")
            text = (
                "⏰ Через час у вас консультация!\n\n📅 " + b["slot"] + "\n\nДо встречи! 💙"
                if lang == "ru" else
                "⏰ Через годину у вас консультація!\n\n📅 " + b["slot"] + "\n\nДо зустрічі! 💙"
            )
            try:
                await bot.send_message(b["user_id"], text)
                await storage.mark_reminded_1h(b)
            except Exception:
                pass


async def send_pay_reminders(bot: Bot):
    now = datetime.now()
    for b in await storage.get_unpay_reminded_bookings():
        if b.get("paid"):
            await storage.mark_pay_reminded(b)
            continue
        dt = parse_slot_dt(b)
        if not dt:
            continue
        diff = (dt - now).total_seconds() / 3600
        if 11.5 <= diff <= 12.5:
            lang = b.get("lang", "ru")
            kb = InlineKeyboardBuilder()
            kb.button(
                text="💳 Оплатить" if lang == "ru" else "💳 Оплатити",
                callback_data="pay_consultation"
            )
            text = (
                "💳 Пора оплатить консультацию!\n\n📅 " + b["slot"]
                if lang == "ru" else
                "💳 Час оплатити консультацію!\n\n📅 " + b["slot"]
            )
            try:
                await bot.send_message(b["user_id"], text, reply_markup=kb.as_markup())
                await storage.mark_pay_reminded(b)
            except Exception:
                pass


async def send_rebooking_suggestions(bot: Bot):
    """Через ~24ч после завершения сессии предлагаем перезаписаться."""
    try:
        async with storage._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT b.user_id, b.name, b.lang
                FROM completed_sessions cs
                JOIN bookings b ON b.id = cs.booking_id
                WHERE cs.completed_at >= NOW() - INTERVAL '25 hours'
                AND cs.completed_at <= NOW() - INTERVAL '23 hours'
                AND NOT EXISTS (
                    SELECT 1 FROM bookings b2
                    WHERE b2.user_id = b.user_id
                    AND b2.cancelled = FALSE
                    AND b2.id > b.id
                )
            """)
        for r in rows:
            lang = r["lang"]
            kb = InlineKeyboardBuilder()
            kb.button(
                text="📅 Записаться снова" if lang == "ru" else "📅 Записатися знову",
                callback_data="book"
            )
            kb.adjust(1)
            text = (
                "👋 " + r["name"] + ", как вы себя чувствуете после сессии?\n\n"
                "Если хотите продолжить работу — запишитесь на следующую встречу. 💙"
                if lang == "ru" else
                "👋 " + r["name"] + ", як ви почуваєтеся після сесії?\n\n"
                "Якщо хочете продовжити роботу — запишіться на наступну зустріч. 💙"
            )
            try:
                await bot.send_message(r["user_id"], text, reply_markup=kb.as_markup())
            except Exception:
                pass
    except Exception:
        pass


async def send_daily_messages(bot: Bot):
    """Ежедневные послания в 10:00."""
    subscribers = await storage.get_daily_message_subscribers()
    if not subscribers:
        return
    users = await storage.get_all_users()
    for uid in subscribers:
        try:
            lang = users.get(uid, {}).get("lang", "ru")
            message = _get_msg(lang)
            await bot.send_message(uid, message)
        except Exception:
            pass


async def slot_refresh_loop(bot: Bot):
    """Раз в сутки генерируем слоты на 2 недели вперёд."""
    while True:
        await storage.generate_slots_for_week()
        await asyncio.sleep(86400)


async def reminder_loop(bot: Bot):
    """Главный цикл — каждые 30 минут."""
    daily_sent_date = None
    while True:
        now = datetime.now()
        await send_day_reminders(bot)
        await send_1h_reminders(bot)
        await send_pay_reminders(bot)
        await send_rebooking_suggestions(bot)

        # Ежедневные послания — один раз в день в 10:00
        if now.hour == 10 and now.minute < 30 and daily_sent_date != now.date():
            await send_daily_messages(bot)
            daily_sent_date = now.date()

        await asyncio.sleep(1800)
