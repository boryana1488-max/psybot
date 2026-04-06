from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
import storage

router = Router()


class RescheduleState(StatesGroup):
    choosing_slot = State()


def main_menu_kb(lang: str, has_booking: bool = False):
    from handlers.client import main_menu_kb as _kb
    return _kb(lang, has_booking)


async def safe_edit(callback, text, kb):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# ── Отмена клиентом ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_booking")
async def cancel_ask(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    b = await storage.get_booking_by_user(callback.from_user.id)
    if not b:
        await callback.answer("Активной записи нет.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, отменить" if lang == "ru" else "✅ Так, скасувати", callback_data="cancel_confirm")
    kb.button(text="◀️ Назад" , callback_data="main_menu")
    kb.adjust(1)
    text = (f"Отменить запись?\n\n📅 {b['slot']}" if lang == "ru"
            else f"Скасувати запис?\n\n📅 {b['slot']}")
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(F.data == "cancel_confirm")
async def cancel_confirmed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    b = await storage.get_booking_by_user(callback.from_user.id)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    slot = b["slot"]
    await storage.cancel_booking(b)

    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться снова" if lang == "ru" else "📅 Записатися знову", callback_data="book")
    kb.adjust(1)
    text = ("✅ Запись отменена." if lang == "ru" else "✅ Запис скасовано.")
    await safe_edit(callback, text, kb.as_markup())

    # Уведомить психолога
    try:
        await callback.bot.send_message(
            ADMIN_ID,
            f"❌ Клиент отменил запись\n\n👤 {b['name']}\n📅 {slot}"
        )
    except Exception:
        pass


# ── Запрос на перенос клиентом ────────────────────────────────────────────────

@router.callback_query(F.data == "reschedule_booking")
async def reschedule_ask(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    b = await storage.get_booking_by_user(callback.from_user.id)
    if not b:
        await callback.answer("Активной записи нет.", show_alert=True)
        return
    free = await storage.get_free_slots()
    if not free:
        await callback.answer(
            "Свободных слотов нет. Свяжитесь с психологом." if lang == "ru"
            else "Вільних слотів немає. Зв'яжіться з психологом.",
            show_alert=True
        )
        return
    kb = InlineKeyboardBuilder()
    for s in free:
        kb.button(text=f"🕐 {s}", callback_data=f"reschedule_slot_{s}")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    await state.set_state(RescheduleState.choosing_slot)
    text = (f"Текущий слот: {b['slot']}\n\nВыберите новое время:" if lang == "ru"
            else f"Поточний слот: {b['slot']}\n\nОберіть новий час:")
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(RescheduleState.choosing_slot, F.data.startswith("reschedule_slot_"))
async def reschedule_slot_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    new_slot = callback.data.replace("reschedule_slot_", "")
    b = await storage.get_booking_by_user(callback.from_user.id)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    pending = await storage.get_pending_reschedules()
    idx = len(pending)  # индекс нового запроса
    await storage.add_reschedule(
        user_id=callback.from_user.id,
        name=b["name"],
        old_slot=b["slot"],
        new_slot=new_slot,
    )
    await state.set_state(None)

    text = ("⏳ Запрос на перенос отправлен психологу.\n\nОжидайте подтверждения." if lang == "ru"
            else "⏳ Запит на перенесення надіслано психологу.\n\nОчікуйте підтвердження.")
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await safe_edit(callback, text, kb.as_markup())

    # Уведомить психолога с кнопками
    adm_kb = InlineKeyboardBuilder()
    adm_kb.button(text="✅ Подтвердить", callback_data=f"adm_reschedule_approve_{idx}")
    adm_kb.button(text="❌ Отклонить", callback_data=f"adm_reschedule_reject_{idx}")
    adm_kb.adjust(2)
    try:
        await callback.bot.send_message(
            ADMIN_ID,
            f"🔄 Запрос на перенос\n\n"
            f"👤 {b['name']}\n"
            f"📅 {b['slot']} → {new_slot}",
            reply_markup=adm_kb.as_markup()
        )
    except Exception:
        pass
