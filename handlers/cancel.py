from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from collections import defaultdict

from config import ADMIN_ID
import storage

router = Router()

# Хранилище слотов при выборе даты (в памяти на время FSM)
_slot_cache: dict = {}  # user_id -> {date_key -> [slots]}


class RescheduleState(StatesGroup):
    choosing_date = State()
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
        await callback.answer("Активной записи нет." if lang == "ru" else "Активного запису немає.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, отменить" if lang == "ru" else "✅ Так, скасувати", callback_data="cancel_confirm")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(2)
    text = (f"Отменить запись?\n\n📅 {b['slot']}" if lang == "ru"
            else f"Скасувати запис?\n\n📅 {b['slot']}")
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(F.data == "cancel_confirm")
async def cancel_confirmed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    b = await storage.get_booking_by_user(callback.from_user.id)
    if not b:
        await callback.answer("Запись не найдена." if lang == "ru" else "Запис не знайдено.", show_alert=True)
        return
    slot = b["slot"]
    await storage.cancel_booking(b)

    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться снова" if lang == "ru" else "📅 Записатися знову", callback_data="book")
    kb.adjust(1)
    text = "✅ Запись отменена." if lang == "ru" else "✅ Запис скасовано."
    await safe_edit(callback, text, kb.as_markup())

    try:
        await callback.bot.send_message(
            ADMIN_ID,
            f"❌ Клиент отменил запись\n\n👤 {b['name']}\n📅 {slot}"
        )
    except Exception:
        pass


# ── Перенос клиентом — выбор даты ────────────────────────────────────────────

@router.callback_query(F.data == "reschedule_booking")
async def reschedule_ask(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    b = await storage.get_booking_by_user(callback.from_user.id)
    if not b:
        await callback.answer("Активной записи нет." if lang == "ru" else "Активного запису немає.", show_alert=True)
        return
    free = await storage.get_free_slots()
    if not free:
        await callback.answer(
            "Свободных слотов нет. Свяжитесь с психологом." if lang == "ru"
            else "Вільних слотів немає. Зв'яжіться з психологом.",
            show_alert=True
        )
        return

    # Группируем по дате
    by_date = defaultdict(list)
    for s in free:
        date_key = str(s.get("slot_date", ""))
        by_date[date_key].append(s)

    # Кэшируем слоты
    _slot_cache[callback.from_user.id] = dict(by_date)

    kb = InlineKeyboardBuilder()
    for date_key in sorted(by_date.keys()):
        sample = by_date[date_key][0]
        parts = sample["slot"].split(" ")
        label = " ".join(parts[:2]) if len(parts) >= 2 else sample["slot"]
        kb.button(text=f"📅 {label}", callback_data=f"rsdate_{date_key}")
    kb.button(text="◀️ Назад" if lang == "ru" else "◀️ Назад", callback_data="main_menu")
    kb.adjust(2)
    await state.set_state(RescheduleState.choosing_date)
    text = (f"Текущий слот: {b['slot']}\n\nВыберите новую дату:" if lang == "ru"
            else f"Поточний слот: {b['slot']}\n\nОберіть нову дату:")
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(RescheduleState.choosing_date, F.data.startswith("rsdate_"))
async def reschedule_date_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    date_key = callback.data[7:]

    uid = callback.from_user.id
    by_date = _slot_cache.get(uid, {})
    day_slots = by_date.get(date_key, [])

    if not day_slots:
        await callback.answer("Слоты заняты." if lang == "ru" else "Слоти зайняті.", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for s in day_slots:
        time_part = s["slot"].split(" ")[-1]
        # Используем индекс чтобы не хранить слот в callback_data
        idx = day_slots.index(s)
        kb.button(text=f"🕐 {time_part}", callback_data=f"rsslot_{date_key}_{idx}")
    kb.button(text="◀️ Назад" if lang == "ru" else "◀️ Назад", callback_data="reschedule_booking")
    kb.adjust(2)
    await state.set_state(RescheduleState.choosing_slot)
    text = "Выберите время:" if lang == "ru" else "Оберіть час:"
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(RescheduleState.choosing_slot, F.data.startswith("rsslot_"))
async def reschedule_slot_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    parts = callback.data[7:].rsplit("_", 1)
    date_key = parts[0]
    idx = int(parts[1])

    uid = callback.from_user.id
    day_slots = _slot_cache.get(uid, {}).get(date_key, [])
    if idx >= len(day_slots):
        await callback.answer("Слот недоступен." if lang == "ru" else "Слот недоступний.", show_alert=True)
        return

    new_slot = day_slots[idx]["slot"]
    b = await storage.get_booking_by_user(uid)
    if not b:
        await callback.answer("Запись не найдена." if lang == "ru" else "Запис не знайдено.", show_alert=True)
        return

    pending = await storage.get_pending_reschedules()
    req_idx = len(pending)
    await storage.add_reschedule(
        user_id=uid,
        name=b["name"],
        old_slot=b["slot"],
        new_slot=new_slot,
    )
    await state.set_state(None)
    _slot_cache.pop(uid, None)

    text = ("⏳ Запрос на перенос отправлен психологу.\n\nОжидайте подтверждения." if lang == "ru"
            else "⏳ Запит на перенесення надіслано психологу.\n\nОчікуйте підтвердження.")
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await safe_edit(callback, text, kb.as_markup())

    # Уведомить психолога
    adm_kb = InlineKeyboardBuilder()
    adm_kb.button(text="✅ Подтвердить", callback_data=f"adm_rs_ok_{req_idx}")
    adm_kb.button(text="❌ Отклонить", callback_data=f"adm_rs_no_{req_idx}")
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
