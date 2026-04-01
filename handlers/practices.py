from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import t

router = Router()


def practices_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🌬 4-7-8", callback_data="p_478")
    kb.button(text="📦 Коробочное" if lang == "ru" else "📦 Коробкове", callback_data="p_box")
    kb.button(text="🌱 5-4-3-2-1", callback_data="p_ground")
    kb.button(text="🧠 Когнитивное" if lang == "ru" else "🧠 Когнітивне", callback_data="p_cog")
    kb.button(text="📓 Дневник" if lang == "ru" else "📓 Щоденник", callback_data="p_diary")
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def back_to_practices_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "back"), callback_data="practices")
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.adjust(2)
    return kb.as_markup()


@router.callback_query(F.data == "practices")
async def practices_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_text(t(lang, "practices_menu"), reply_markup=practices_kb(lang))


@router.callback_query(F.data == "p_478")
async def practice_478(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = f"*{t(lang, 'breathing_478_title')}*\n\n{t(lang, 'breathing_478_text')}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_practices_kb(lang))


@router.callback_query(F.data == "p_box")
async def practice_box(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = f"*{t(lang, 'breathing_box_title')}*\n\n{t(lang, 'breathing_box_text')}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_practices_kb(lang))


@router.callback_query(F.data == "p_ground")
async def practice_ground(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = f"*{t(lang, 'grounding_title')}*\n\n{t(lang, 'grounding_text')}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_practices_kb(lang))


@router.callback_query(F.data == "p_cog")
async def practice_cog(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = f"*{t(lang, 'cognitive_title')}*\n\n{t(lang, 'cognitive_text')}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_practices_kb(lang))


@router.callback_query(F.data == "p_diary")
async def practice_diary(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = f"*{t(lang, 'diary_title')}*\n\n{t(lang, 'diary_text')}"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_practices_kb(lang))
