from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from texts import t
from images_config import get_image
import storage

router = Router()

async def safe_edit(callback, text, kb=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

def mood_kb(lang):
    kb = InlineKeyboardBuilder()
    opts = [("😢", "mood_1"), ("😔", "mood_2"), ("😐", "mood_3"), ("🙂", "mood_4"), ("😊", "mood_5")]
    for emoji, cb in opts:
        kb.button(text=emoji, callback_data=cb)
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    kb.adjust(5, 1)
    return kb.as_markup()

@router.callback_query(F.data == "mood")
async def ask_mood(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    photo = get_image("mood")
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=t(lang, "mood_ask"),
                                                reply_markup=mood_kb(lang))
            await callback.message.delete()
            return
        except Exception:
            pass
    await safe_edit(callback, t(lang, "mood_ask"), mood_kb(lang))

@router.callback_query(F.data.startswith("mood_"))
async def mood_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    score = int(callback.data.split("_")[1])
    name = data.get("name", callback.from_user.first_name or "Клиент")
    await storage.save_mood_with_date(callback.from_user.id, name, score)
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Мой прогресс" if lang == "ru" else "📊 Мій прогрес", callback_data="my_progress")
    kb.button(text="◀️ Меню", callback_data="main_menu")
    kb.adjust(1)
    await safe_edit(callback, t(lang, "mood_thanks"), kb.as_markup())
