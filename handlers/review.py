from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
import storage

router = Router()


class ReviewState(StatesGroup):
    waiting_comment = State()


def stars_kb(lang: str):
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data=f"review_{i}")
    kb.button(text="◀️ Пропустить" if lang == "ru" else "◀️ Пропустити", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "leave_review")
async def ask_rating(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    text = (
        "Пожалуйста, оцените консультацию:"
        if lang == "ru" else
        "Будь ласка, оцініть консультацію:"
    )
    await callback.message.edit_text(text, reply_markup=stars_kb(lang))


@router.callback_query(F.data.startswith("review_"))
async def rating_chosen(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(review_rating=rating)
    data = await state.get_data()
    lang = data.get("lang", "ru")

    await state.set_state(ReviewState.waiting_comment)
    text = (
        f"{'⭐' * rating}\n\nХотите добавить комментарий? (или напишите «нет»)"
        if lang == "ru" else
        f"{'⭐' * rating}\n\nХочете додати коментар? (або напишіть «ні»)"
    )
    await callback.message.edit_text(text)


@router.message(ReviewState.waiting_comment)
async def comment_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    rating = data.get("review_rating", 5)
    comment = message.text.strip()
    name = data.get("name", message.from_user.first_name or "—")

    storage.add_review(
        user_id=message.from_user.id,
        name=name,
        rating=rating,
        comment=comment,
    )
    await state.set_state(None)

    text = (
        "💙 Спасибо за отзыв! Это очень важно для нас."
        if lang == "ru" else
        "💙 Дякуємо за відгук! Це дуже важливо для нас."
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню" if lang == "ru" else "🏠 Головне меню", callback_data="main_menu")
    await message.answer(text, reply_markup=kb.as_markup())

    # Уведомить психолога
    stars = "⭐" * rating
    await message.bot.send_message(
        ADMIN_ID,
        f"💬 Новый отзыв!\n\n"
        f"👤 {name}\n"
        f"{stars}\n"
        f"📝 {comment}"
    )
