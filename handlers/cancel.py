from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
import storage

router = Router()


def cancel_confirm_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Да, отменить" if lang == "ru" else "✅ Так, скасувати",
        callback_data="cancel_confirm"
    )
    kb.button(
        text="◀️ Назад" if lang == "ru" else "◀️ Назад",
        callback_data="main_menu"
    )
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_ask(callback: CallbackQuery):
    data = await callback.bot.get_chat(callback.from_user.id)
    from aiogram.fsm.context import FSMContext
    user_id = callback.from_user.id

    booking = storage.get_booking_by_user(user_id)
    if not booking:
        await callback.answer("У вас нет активной записи.", show_alert=True)
        return

    lang = booking.get("lang", "ru")
    slot = booking["slot"]

    text = (
        f"Вы хотите отменить запись?\n\n📅 {slot}"
        if lang == "ru" else
        f"Ви хочете скасувати запис?\n\n📅 {slot}"
    )
    await callback.message.edit_text(text, reply_markup=cancel_confirm_kb(lang))


@router.callback_query(F.data == "cancel_confirm")
async def cancel_confirmed(callback: CallbackQuery):
    user_id = callback.from_user.id
    booking = storage.cancel_booking_by_user(user_id)

    if not booking:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    lang = booking.get("lang", "ru")

    text = (
        "✅ Ваша запись отменена. Если захотите записаться снова — нажмите «Записаться»."
        if lang == "ru" else
        "✅ Ваш запис скасовано. Якщо захочете записатися знову — натисніть «Записатися»."
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.adjust(1)

    await callback.message.edit_text(text, reply_markup=kb.as_markup())

    # Уведомить психолога
    await callback.bot.send_message(
        ADMIN_ID,
        f"❌ Отмена записи!\n\n"
        f"👤 {booking['name']}\n"
        f"📅 {booking['slot']}\n"
        f"🆔 {user_id}"
    )
