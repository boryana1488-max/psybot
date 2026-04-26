"""AI-чат через Anthropic API. Бесплатно. Лимит 10/10 в месяц, сбрасывается 1-го числа."""
import os
import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import storage
from images_config import get_image

router = Router()
API_URL = "https://api.anthropic.com/v1/messages"

SOS_SYSTEM = {
    "ru": ("Ты — тёплый эмпатичный AI-ассистент психолога. Человек в кризисе. "
           "Выслушай, не осуждай, помоги успокоиться через дыхание и заземление. "
           "2-4 предложения. После 8 сообщений предложи записаться к психологу. "
           "Никогда не ставь диагнозы."),
    "uk": ("Ти — теплий емпатичний AI-асистент психолога. Людина в кризі. "
           "Вислухай, не засуджуй, допоможи заспокоїтися через дихання та заземлення. "
           "2-4 речення. Після 8 повідомлень запропонуй записатися до психолога. "
           "Ніколи не став діагнози."),
}
PRACTICE_SYSTEM = {
    "ru": ("Ты — AI-ассистент психолога. Помогаешь подобрать практику. "
           "Спроси что беспокоит, предложи конкретную технику с пошаговым объяснением. "
           "Просто, без жаргона. 3-5 предложений. Никогда не ставь диагнозы."),
    "uk": ("Ти — AI-асистент психолога. Допомагаєш підібрати практику. "
           "Запитай що турбує, запропонуй конкретну техніку з покроковим поясненням. "
           "Просто, без жаргону. 3-5 речень. Ніколи не став діагнози."),
}


class AIChatState(StatesGroup):
    sos_chat      = State()
    practice_chat = State()


def stop_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛑 " + ("Завершить" if lang == "ru" else "Завершити"), callback_data="ai_stop")
    kb.button(text="📅 " + ("Записаться" if lang == "ru" else "Записатися"), callback_data="book")
    kb.adjust(2)
    return kb.as_markup()


async def safe_edit(callback, text, kb=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


async def call_claude(system: str, history: list, user_msg: str) -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return "AI временно недоступен."
    messages = history[-18:] + [{"role": "user", "content": user_msg}]
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(API_URL, json={
                "model": "claude-haiku-4-5",
                "max_tokens": 300,
                "system": system,
                "messages": messages,
            }, headers={
                "Content-Type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    data = await r.json()
                    return data["content"][0]["text"]
                return "Ошибка соединения с AI."
    except Exception:
        return "AI временно недоступен."


async def start_ai(callback: CallbackQuery, state: FSMContext, mode: str):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    uid = callback.from_user.id
    access = await storage.get_ai_access(uid)
    field = "sos_left" if mode == "sos" else "practice_left"
    left = access.get(field, 0) if access else 0

    if left <= 0:
        from datetime import date
        now = date.today()
        text = (
            "🤖 AI-ассистент\n\n"
            "Лимит на этот месяц исчерпан (10 сообщений).\n"
            "Лимит обновится 1 " + str(now.replace(day=1).strftime("%B")) + "."
            if lang == "ru" else
            "🤖 AI-асистент\n\n"
            "Ліміт на цей місяць вичерпано (10 повідомлень).\n"
            "Ліміт оновиться 1-го числа наступного місяця."
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="📅 " + ("Записаться" if lang == "ru" else "Записатися"), callback_data="book")
        kb.button(text="◀️ Меню", callback_data="main_menu")
        kb.adjust(1)
        await safe_edit(callback, text, kb.as_markup())
        return

    await state.update_data(ai_history=[], ai_mode=mode)
    if mode == "sos":
        await state.set_state(AIChatState.sos_chat)
    else:
        await state.set_state(AIChatState.practice_chat)

    text = (
        "🤖 AI-ассистент\n\nОсталось: " + str(left) + "/10\n\n" + (
            "Расскажите что происходит. Я здесь и слушаю."
            if mode == "sos" else
            "Расскажите что вас беспокоит — подберу технику."
        ) if lang == "ru" else
        "🤖 AI-асистент\n\nЗалишилось: " + str(left) + "/10\n\n" + (
            "Розкажіть що відбувається. Я тут і слухаю."
            if mode == "sos" else
            "Розкажіть що вас турбує — підберу техніку."
        )
    )
    photo = get_image("ai_chat")
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=text,
                                                reply_markup=stop_kb(lang))
            await callback.message.delete()
            return
        except Exception:
            pass
    await safe_edit(callback, text, stop_kb(lang))


@router.callback_query(F.data == "ai_sos")
async def ai_sos_start(callback: CallbackQuery, state: FSMContext):
    await start_ai(callback, state, "sos")


@router.callback_query(F.data == "ai_practice")
async def ai_practice_start(callback: CallbackQuery, state: FSMContext):
    await start_ai(callback, state, "practice")


async def handle_msg(message: Message, state: FSMContext, mode: str):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    history = data.get("ai_history", [])
    uid = message.from_user.id

    if mode == "sos":
        left = await storage.decrement_ai_sos(uid)
    else:
        left = await storage.decrement_ai_practice(uid)

    system = (SOS_SYSTEM if mode == "sos" else PRACTICE_SYSTEM)[lang]
    wait = await message.answer("🤔")
    reply = await call_claude(system, history, message.text)
    history = history[-18:] + [
        {"role": "user", "content": message.text},
        {"role": "assistant", "content": reply},
    ]
    await state.update_data(ai_history=history)
    await wait.delete()

    if left <= 2:
        reply += "\n\n⚠️ " + ("Осталось: " + str(left) if lang == "ru" else "Залишилось: " + str(left))

    if left <= 0:
        await state.set_state(None)
        kb = InlineKeyboardBuilder()
        kb.button(text="📅 " + ("Записаться" if lang == "ru" else "Записатися"), callback_data="book")
        kb.button(text="◀️ Меню", callback_data="main_menu")
        kb.adjust(1)
        await message.answer(
            reply + "\n\n💙 " + ("Лимит исчерпан. Рекомендую записаться к психологу."
            if lang == "ru" else "Ліміт вичерпано. Рекомендую записатися до психолога."),
            reply_markup=kb.as_markup()
        )
        return

    await message.answer(reply, reply_markup=stop_kb(lang))


@router.message(AIChatState.sos_chat)
async def sos_msg(message: Message, state: FSMContext):
    await handle_msg(message, state, "sos")


@router.message(AIChatState.practice_chat)
async def practice_msg(message: Message, state: FSMContext):
    await handle_msg(message, state, "practice")


@router.callback_query(F.data == "ai_stop")
async def ai_stop(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await state.update_data(ai_history=[])
    await state.set_state(None)
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 " + ("Записаться" if lang == "ru" else "Записатися"), callback_data="book")
    kb.button(text="◀️ Меню", callback_data="main_menu")
    kb.adjust(1)
    await safe_edit(callback,
        "Диалог завершён. 💙" if lang == "ru" else "Діалог завершено. 💙",
        kb.as_markup()
    )
