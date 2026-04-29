from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from texts import t
from images_config import get_image

router = Router()


def next_kb(lang: str, next_cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "next"), callback_data=next_cb)
    kb.adjust(1)
    return kb.as_markup()


def sos_final_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🤖 AI-ассистент" if lang == "ru" else "🤖 AI-асистент",
              callback_data="ai_sos")
    kb.button(text=t(lang, "sos_book_now"), callback_data="book")
    kb.button(text=t(lang, "sos_later"), callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


async def safe_edit(callback, text, kb):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "sos")
async def sos_start(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = t(lang, "sos_start")
    kb = next_kb(lang, "sos_step1")
    photo = get_image("sos")
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
            await callback.message.delete()
            return
        except Exception:
            pass
    await safe_edit(callback, text, kb)


@router.callback_query(F.data == "sos_step1")
async def sos_step1(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await safe_edit(callback, t(lang, "sos_step1"), next_kb(lang, "sos_step2"))


@router.callback_query(F.data == "sos_step2")
async def sos_step2(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await safe_edit(callback, t(lang, "sos_step2"), next_kb(lang, "sos_step3"))


@router.callback_query(F.data == "sos_step3")
async def sos_step3(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await safe_edit(callback, t(lang, "sos_step3"), sos_final_kb(lang))
