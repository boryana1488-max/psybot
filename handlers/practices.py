from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import t
from images_config import get_image

router = Router()


def practices_kb(lang: str):
    kb = InlineKeyboardBuilder()
    # Дыхание
    kb.button(text="🌬 4-7-8", callback_data="p_478")
    kb.button(text="📦 Квадратное" if lang == "ru" else "📦 Квадратне", callback_data="p_box")
    # Заземление и тело
    kb.button(text="🌱 5-4-3-2-1", callback_data="p_ground")
    kb.button(text="💪 Напряжение" if lang == "ru" else "💪 Напруга", callback_data="p_tension")
    kb.button(text="🧊 Холод/тепло" if lang == "ru" else "🧊 Холод/тепло", callback_data="p_cold")
    # Когниции
    kb.button(text="🧠 Ну и что?" if lang == "ru" else "🧠 Ну і що?", callback_data="p_cog")
    # Дневники
    kb.button(text="📓 Дневник ощущений" if lang == "ru" else "📓 Щоденник відчуттів", callback_data="p_diary")
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    kb.adjust(2, 2, 1, 1, 1, 1)
    return kb.as_markup()


def back_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back"), callback_data="practices")
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.adjust(2)
    return kb.as_markup()


async def safe_edit(callback: CallbackQuery, text: str, kb, parse_mode="Markdown"):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=kb)
        else:
            await callback.message.edit_text(text, parse_mode=parse_mode, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode=parse_mode, reply_markup=kb)


async def send_practice(callback, lang, title_key, text_key, with_photo=False):
    text = f"*{t(lang, title_key)}*\n\n{t(lang, text_key)}"
    kb = back_kb(lang)
    if with_photo:
        photo = get_image("breathing")
        if photo:
            try:
                await callback.message.answer_photo(photo=photo, caption=text, parse_mode="Markdown", reply_markup=kb)
                await callback.message.delete()
                return
            except Exception:
                pass
    await safe_edit(callback, text, kb)


@router.callback_query(F.data == "practices")
async def practices_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await safe_edit(callback, t(lang, "practices_menu"), practices_kb(lang), parse_mode=None)


@router.callback_query(F.data == "p_478")
async def p_478(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "breathing_478_title", "breathing_478_text", with_photo=True)

@router.callback_query(F.data == "p_box")
async def p_box(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "breathing_box_title", "breathing_box_text", with_photo=True)

@router.callback_query(F.data == "p_ground")
async def p_ground(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "grounding_title", "grounding_text")

@router.callback_query(F.data == "p_tension")
async def p_tension(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "tension_title", "tension_text")

@router.callback_query(F.data == "p_cold")
async def p_cold(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "cold_title", "cold_text")

@router.callback_query(F.data == "p_cog")
async def p_cog(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "cognitive_title", "cognitive_text")

@router.callback_query(F.data == "p_diary")
async def p_diary(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await send_practice(callback, lang, "diary_title", "diary_text")
