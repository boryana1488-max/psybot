from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import t
from config import SLOTS, ADMIN_ID
import storage

router = Router()


class BookingState(StatesGroup):
    choosing_lang = State()
    choosing_slot = State()
    entering_name = State()
    entering_phone = State()


def get_user_lang(data: dict) -> str:
    return data.get("lang", "ru")


def main_menu_kb(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.button(text="🌬 Практики" if lang == "ru" else "🌬 Практики", callback_data="practices")
    kb.button(text="🆘 SOS", callback_data="sos")
    kb.adjust(1)
    return kb.as_markup()


def lang_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇺🇦 Українська", callback_data="lang_uk")
    kb.adjust(2)
    return kb.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BookingState.choosing_lang)
    await message.answer(
        "👋 Добро пожаловать! / Ласкаво просимо!\n\nВыберите язык / Оберіть мову:",
        reply_markup=lang_kb()
    )


@router.callback_query(F.data.in_(["lang_ru", "lang_uk"]))
async def choose_lang(callback: CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data == "lang_ru" else "uk"
    await state.update_data(lang=lang)
    await state.set_state(None)
    await callback.message.edit_text(
        t(lang, "main_menu"),
        reply_markup=main_menu_kb(lang)
    )


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    await callback.message.edit_text(
        t(lang, "main_menu"),
        reply_markup=main_menu_kb(lang)
    )


# ─── Booking flow ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)

    free = storage.get_free_slots()
    if not free:
        await callback.answer(t(lang, "no_slots"), show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for slot in free:
        kb.button(text=f"🕐 {slot}", callback_data=f"slot_{slot}")
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    kb.adjust(1)

    await state.set_state(BookingState.choosing_slot)
    await callback.message.edit_text(t(lang, "choose_slot"), reply_markup=kb.as_markup())


@router.callback_query(BookingState.choosing_slot, F.data.startswith("slot_"))
async def slot_chosen(callback: CallbackQuery, state: FSMContext):
    slot = callback.data.replace("slot_", "")
    await state.update_data(slot=slot)
    data = await state.get_data()
    lang = get_user_lang(data)

    await state.set_state(BookingState.entering_name)
    await callback.message.edit_text(t(lang, "ask_name"))


@router.message(BookingState.entering_name)
async def name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    data = await state.get_data()
    lang = get_user_lang(data)

    await state.set_state(BookingState.entering_phone)
    await message.answer(t(lang, "ask_phone"))


@router.message(BookingState.entering_phone)
async def phone_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    phone = message.text.strip()
    name = data.get("name", "—")
    slot = data.get("slot", "—")

    storage.add_booking(
        user_id=message.from_user.id,
        name=name,
        phone=phone,
        slot=slot,
        lang=lang,
    )

    await state.set_state(None)

    # Подтверждение клиенту
    await message.answer(
        t(lang, "booking_confirmed", slot=slot, name=name),
        reply_markup=main_menu_kb(lang)
    )

    # Уведомление админу
    await message.bot.send_message(
        ADMIN_ID,
        t("ru", "admin_new_booking", name=name, phone=phone, slot=slot, user_id=message.from_user.id)
    )

