from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import t
import storage

router = Router()


def mood_kb(lang: str):
    kb = InlineKeyboardBuilder()
    moods = [
        ("😢 Очень плохо" if lang == "ru" else "😢 Дуже погано", "mood_1"),
        ("😔 Плохо" if lang == "ru" else "😔 Погано", "mood_2"),
        ("😐 Нейтрально" if lang == "ru" else "😐 Нейтрально", "mood_3"),
        ("🙂 Хорошо" if lang == "ru" else "🙂 Добре", "mood_4"),
        ("😊 Отлично" if lang == "ru" else "😊 Чудово", "mood_5"),
    ]
    for label, cb in moods:
        kb.button(text=label, callback_data=cb)
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "mood")
async def ask_mood(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=t(lang, "mood_ask"), reply_markup=mood_kb(lang))
        else:
            await callback.message.edit_text(t(lang, "mood_ask"), reply_markup=mood_kb(lang))
    except Exception:
        await callback.message.answer(t(lang, "mood_ask"), reply_markup=mood_kb(lang))


@router.callback_query(F.data.startswith("mood_"))
async def mood_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    score = int(callback.data.split("_")[1])
    name = data.get("name", callback.from_user.first_name or "Клиент")

    storage.save_mood(user_id=callback.from_user.id, name=name, mood=score)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.button(text="◀️ Меню", callback_data="main_menu")
    kb.adjust(1)

    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=t(lang, "mood_thanks"), reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(t(lang, "mood_thanks"), reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(t(lang, "mood_thanks"), reply_markup=kb.as_markup())
