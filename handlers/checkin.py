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

async def checkin_loop(bot: Bot):
    while True:
        now = datetime.now()
        target = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if now >= target:
            wait = (target.replace(day=target.day + 1) - now).seconds
        else:
            wait = (target - now).seconds
        await asyncio.sleep(wait)

        all_users = await storage.get_all_users()
        for user_id in list(await storage.get_subscribed_users()):
            user_data = all_users.get(user_id, {})
            lang = user_data.get("lang", "ru")
            text = ("🌙 Как прошёл твой день? Напиши пару слов — это помогает осознавать себя."
                    if lang == "ru" else
                    "🌙 Як пройшов твій день? Напиши кілька слів — це допомагає усвідомлювати себе.")
            try:
                await bot.send_message(user_id, text)
            except Exception:
                pass

        await asyncio.sleep(60)
