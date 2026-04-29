"""Аффирмации и ежедневные послания."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import storage
from images_config import get_image
from affirmations import get_affirmation_by_index

router = Router()


async def safe_edit(callback, text, kb=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# ── Аффирмации ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "affirmations")
async def affirmations_start(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    idx = data.get("affirmation_idx", 0)
    text, next_idx = get_affirmation_by_index(idx, lang)
    await state.update_data(affirmation_idx=next_idx)
    header = "🌸 Аффирмация" if lang == "ru" else "🌸 Афірмація"
    full_text = header + "\n\n" + text

    kb = InlineKeyboardBuilder()
    kb.button(
        text="✨ Следующая" if lang == "ru" else "✨ Наступна",
        callback_data="affirmation_next"
    )
    kb.button(
        text="◀️ Меню" if lang == "ru" else "◀️ Меню",
        callback_data="main_menu"
    )
    kb.adjust(1)

    await safe_edit(callback, full_text, kb.as_markup())


@router.callback_query(F.data == "affirmation_next")
async def affirmation_next(callback: CallbackQuery, state: FSMContext):
    await affirmations_start(callback, state)


# ── Ежедневные послания ───────────────────────────────────────────────────────

@router.callback_query(F.data == "daily_messages")
async def daily_messages_toggle(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    uid = callback.from_user.id
    now_subscribed = await storage.toggle_daily_message(uid)

    if now_subscribed:
        text = (
            "📬 Ежедневные послания включены!\n\n"
            "Каждый день вы будете получать вдохновляющее послание.\n\n"
            "Чтобы отключить — нажмите «Послания» ещё раз."
            if lang == "ru" else
            "📬 Щоденні послання увімкнено!\n\n"
            "Щодня ви будете отримувати надихаюче послання.\n\n"
            "Щоб вимкнути — натисніть «Послання» ще раз."
        )
    else:
        text = (
            "🔕 Ежедневные послания отключены."
            if lang == "ru" else
            "🔕 Щоденні послання вимкнено."
        )

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await safe_edit(callback, text, kb.as_markup())
