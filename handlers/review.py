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

async def safe_edit(callback, text, kb=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

def stars_kb(lang):
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.button(text="⭐" * i, callback_data="review_" + str(i))
    kb.button(text="◀️ " + ("Пропустить" if lang == "ru" else "Пропустити"), callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

@router.callback_query(F.data == "leave_review")
async def ask_rating(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    text = "Оцените консультацию:" if lang == "ru" else "Оцініть консультацію:"
    await safe_edit(callback, text, stars_kb(lang))

@router.callback_query(F.data.startswith("review_"))
async def rating_chosen(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    rating = int(callback.data.split("_")[1])
    await state.update_data(review_rating=rating)
    await state.set_state(ReviewState.waiting_comment)
    text = ("⭐" * rating + "\n\nДобавьте комментарий (или напишите «нет»):"
            if lang == "ru" else
            "⭐" * rating + "\n\nДодайте коментар (або напишіть «ні»):")
    await safe_edit(callback, text)

@router.message(ReviewState.waiting_comment)
async def comment_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    rating = data.get("review_rating", 5)
    name = data.get("name", message.from_user.first_name or "Клиент")
    await storage.add_review(message.from_user.id, name, rating, message.text.strip())
    await state.set_state(None)
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await message.answer(
        "💙 Спасибо за отзыв!" if lang == "ru" else "💙 Дякуємо за відгук!",
        reply_markup=kb.as_markup()
    )
    try:
        await message.bot.send_message(
            ADMIN_ID,
            "💬 Новый отзыв!\n\n👤 " + name + "\n" + "⭐" * rating + "\n" + message.text
        )
    except Exception:
        pass
