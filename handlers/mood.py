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
        ("😐 Нейтрально", "mood_3"),
        ("🙂 Хорошо" if lang == "ru" else "🙂 Добре", "mood_4"),
        ("😊 Отлично" if lang == "ru" else "😊 Чудово", "mood_5"),
    ]
    for label, cb in moods:
        kb.button(text=label, callback_data=cb)
    kb.button(text=t(lang, "back"), callback_data="main_menu")
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


@router.callback_query(F.data == "mood")
async def ask_mood(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await safe_edit(callback, t(lang, "mood_ask"), mood_kb(lang))


@router.callback_query(F.data.startswith("mood_"))
async def mood_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    score = int(callback.data.split("_")[1])
    name = data.get("name", callback.from_user.first_name or "Клиент")

    await storage.save_mood_with_date(user_id=callback.from_user.id, name=name, mood=score)

    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Мой прогресс" if lang == "ru" else "📊 Мій прогрес", callback_data="my_progress")
    kb.button(text="◀️ Меню", callback_data="main_menu")
    kb.adjust(1)
    await safe_edit(callback, t(lang, "mood_thanks"), kb.as_markup())
