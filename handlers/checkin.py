"""Вечерний чек-ин в 21:00 и личный прогресс настроения."""
import asyncio
from datetime import datetime, date
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot

import storage

router = Router()


class CheckinState(StatesGroup):
    waiting_text = State()


# ── Подписка / отписка ────────────────────────────────────────────────────────

@router.callback_query(F.data == "checkin_toggle")
async def checkin_toggle(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    uid = callback.from_user.id

    if await storage.is_checkin_subscribed(uid):
        await storage.unsubscribe_checkin(uid)
        text = ("🔕 Вечерний чек-ин отключён." if lang == "ru"
                else "🔕 Вечірній чек-ін вимкнено.")
    else:
        await storage.subscribe_checkin(uid)
        text = ("🔔 Отлично! Каждый вечер в 21:00 я буду спрашивать как прошёл день."
                if lang == "ru" else
                "🔔 Чудово! Щовечора о 21:00 я питатиму як пройшов день.")

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню" if lang == "ru" else "◀️ Меню", callback_data="main_menu")
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup())


# ── Личный прогресс ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_progress")
async def my_progress(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    history = await storage.get_user_mood_history(callback.from_user.id)

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")

    if not history:
        text = ("📊 Прогресс\n\nПока нет данных. Отмечай настроение каждый день через кнопку 😊"
                if lang == "ru" else
                "📊 Прогрес\n\nДаних поки немає. Відзначай настрій щодня через кнопку 😊")
    else:
        emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
        avg = sum(e["mood"] for e in history) / len(history)
        lines = ["📊 Твоё настроение за неделю:\n" if lang == "ru" else "📊 Твій настрій за тиждень:\n"]
        for e in history:
            lines.append(f"{e['created_at']} — {emojis.get(e['mood'], '❓')} {e['mood']}/5")
        if lang == "ru":
            trend = "📈 Растёт!" if history[-1]["mood"] >= history[0]["mood"] else "📉 Снижается"
            lines.append(f"\nСреднее: {avg:.1f} | {trend}")
        else:
            trend = "📈 Зростає!" if history[-1]["mood"] >= history[0]["mood"] else "📉 Знижується"
            lines.append(f"\nСереднє: {avg:.1f} | {trend}")
        text = "\n".join(lines)

    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup())


# ── Ответ на чек-ин ───────────────────────────────────────────────────────────

@router.message(CheckinState.waiting_text)
async def checkin_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    name = data.get("name", message.from_user.first_name or "Клиент")
    await storage.save_checkin(user_id=message.from_user.id, name=name, text=message.text.strip())
    await state.set_state(None)
    text = ("💙 Спасибо, что поделился. Хорошего вечера!" if lang == "ru"
            else "💙 Дякую, що поділився. Гарного вечора!")
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await message.answer(text, reply_markup=kb.as_markup())


# ── Фоновая рассылка в 21:00 ─────────────────────────────────────────────────

# Offset: Kyiv base = UTC+2 (winter) / UTC+3 (summer); we use fixed UTC+2
CHECKIN_HOUR_KYIV = 21  # 21:00 по Киеву

TZ_OFFSETS = {"ua": 0, "eu": -1, "am": -7, "as": 4}

async def checkin_loop(bot: Bot):
    """Раз в минуту проверяем: для каждого пользователя наступило ли 21:00 его timezone."""
    sent_today: set = set()  # user_id которым уже отправили сегодня

    while True:
        await asyncio.sleep(60)
        now_utc = datetime.utcnow()
        today_utc = now_utc.date()

        # Сбрасываем sent_today в полночь UTC
        if not sent_today or now_utc.hour == 0 and now_utc.minute < 2:
            if now_utc.hour == 0:
                sent_today = set()

        all_users = await storage.get_all_users()
        subscribed = await storage.get_subscribed_users()

        for user_id in subscribed:
            if user_id in sent_today:
                continue
            user_data = all_users.get(user_id, {})
            tz = user_data.get("tz", "ua")
            offset = TZ_OFFSETS.get(tz, 0)
            # Время пользователя = UTC+2 (Киев) + offset
            user_hour = (now_utc.hour + 2 + offset) % 24
            if user_hour == CHECKIN_HOUR_KYIV:
                lang = user_data.get("lang", "ru")
                text = ("🌙 Как прошёл твой день? Напиши пару слов — это помогает осознавать себя."
                        if lang == "ru" else
                        "🌙 Як пройшов твій день? Напиши кілька слів — це допомагає усвідомлювати себе.")
                try:
                    await bot.send_message(user_id, text)
                    sent_today.add(user_id)
                except Exception:
                    pass
