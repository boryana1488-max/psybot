from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import t
from config import ADMIN_ID
from images_config import get_image
import storage

router = Router()


class BookingState(StatesGroup):
    choosing_lang = State()
    choosing_slot = State()
    entering_name = State()
    entering_phone = State()


def get_user_lang(data: dict) -> str:
    return data.get("lang", "ru")


def main_menu_kb(lang: str, has_booking: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.button(text="🌬 Практики" if lang == "ru" else "🌬 Практики", callback_data="practices")
    kb.button(text="🆘 SOS", callback_data="sos")
    kb.button(text=t(lang, "mood_btn"), callback_data="mood")
    kb.button(text="💬 Отзывы" if lang == "ru" else "💬 Відгуки", callback_data="client_reviews")
    kb.button(text="📊 Мой прогресс" if lang == "ru" else "📊 Мій прогрес", callback_data="my_progress")
    kb.button(text="🌙 Чек-ин" if lang == "ru" else "🌙 Чек-ін", callback_data="checkin_toggle")
    kb.button(text="📚 Курсы" if lang == "ru" else "📚 Курси", callback_data="courses")
    if has_booking:
        kb.button(text="📋 Мои записи" if lang == "ru" else "📋 Мої записи", callback_data="my_bookings")
        kb.button(text="❌ Отменить" if lang == "ru" else "❌ Скасувати", callback_data="cancel_booking")
        kb.button(text="🔄 Перенести" if lang == "ru" else "🔄 Перенести", callback_data="reschedule_booking")
        kb.button(text="💳 Оплатить" if lang == "ru" else "💳 Оплатити", callback_data="pay_consultation")
        kb.button(text="⭐ Отзыв" if lang == "ru" else "⭐ Відгук", callback_data="leave_review")
    kb.adjust(1)
    return kb.as_markup()


def lang_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇺🇦 Українська", callback_data="lang_uk")
    kb.adjust(2)
    return kb.as_markup()


async def safe_edit(callback, text, kb):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.message(CommandStart(), F.func(lambda m: not (m.from_user.id == __import__("config").ADMIN_ID)))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BookingState.choosing_lang)
    photo = get_image("welcome")
    text = "👋 Добро пожаловать! / Ласкаво просимо!\n\nВыберите язык / Оберіть мову:"
    if photo:
        try:
            await message.answer_photo(photo=photo, caption=text, reply_markup=lang_kb())
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=lang_kb())


@router.callback_query(F.data.in_(["lang_ru", "lang_uk"]))
async def choose_lang(callback: CallbackQuery, state: FSMContext):
    lang = "ru" if callback.data == "lang_ru" else "uk"
    await state.update_data(lang=lang)
    await state.set_state(None)
    await storage.register_user(callback.from_user.id, lang)
    has_booking = await storage.get_booking_by_user(callback.from_user.id) is not None
    await safe_edit(callback, t(lang, "main_menu"), main_menu_kb(lang, has_booking))


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    has_booking = await storage.get_booking_by_user(callback.from_user.id) is not None
    await safe_edit(callback, t(lang, "main_menu"), main_menu_kb(lang, has_booking))


# ── Мои записи ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    bookings = await storage.get_user_bookings(callback.from_user.id)

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")

    if not bookings:
        text = "У вас нет записей." if lang == "ru" else "У вас немає записів."
        await safe_edit(callback, text, kb.as_markup())
        return

    text = "📋 Ваши записи:\n\n" if lang == "ru" else "📋 Ваші записи:\n\n"
    for b in bookings:
        status = "✅" if b.get("paid") else "⏳"
        cancelled = " ❌ отменена" if b.get("cancelled") else ""
        paid_str = " оплачено" if b.get("paid") else " не оплачено"
        text += f"{status} {b['slot']}{cancelled} — {paid_str}\n"

    await safe_edit(callback, text, kb.as_markup())


# ── Отзывы (публичные) ────────────────────────────────────────────────────────

@router.callback_query(F.data == "client_reviews")
async def client_reviews(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    reviews = await storage.get_all_reviews()
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data="main_menu")
    if not reviews:
        text = "💬 Отзывов пока нет. Будьте первым!" if lang == "ru" else "💬 Відгуків поки немає. Будьте першим!"
        await safe_edit(callback, text, kb.as_markup())
        return
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    text = (f"💬 Отзывы клиентов\n{'⭐' * round(avg)} {avg:.1f}/5\n\n" if lang == "ru"
            else f"💬 Відгуки клієнтів\n{'⭐' * round(avg)} {avg:.1f}/5\n\n")
    for r in reviews[-8:]:
        text += f"{'⭐' * r['rating']} {r['name']}\n{r['comment']}\n\n"
    await safe_edit(callback, text, kb.as_markup())


# ── Запись ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)

    # Генерируем слоты если мало
    slots = await storage.get_free_slots()
    if len(slots) < 3:
        await storage.generate_slots_for_week()
        slots = await storage.get_free_slots()

    if not slots:
        await callback.answer(t(lang, "no_slots"), show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for s in slots[:10]:  # максимум 10 слотов
        kb.button(text=f"🕐 {s['slot']}", callback_data=f"slot_{s['slot']}")
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    kb.adjust(1)
    await state.set_state(BookingState.choosing_slot)
    await safe_edit(callback, t(lang, "choose_slot"), kb.as_markup())


@router.callback_query(BookingState.choosing_slot, F.data.startswith("slot_"))
async def slot_chosen(callback: CallbackQuery, state: FSMContext):
    slot = callback.data.replace("slot_", "", 1)
    await state.update_data(slot=slot)
    lang = get_user_lang(await state.get_data())
    await state.set_state(BookingState.entering_name)
    await safe_edit(callback, t(lang, "ask_name"), None)


@router.message(BookingState.entering_name)
async def name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    lang = get_user_lang(await state.get_data())
    await state.set_state(BookingState.entering_phone)
    await message.answer(t(lang, "ask_phone"))


@router.message(BookingState.entering_phone)
async def phone_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    phone = message.text.strip()
    name = data.get("name", "—")
    slot = data.get("slot", "—")

    await storage.add_booking(
        user_id=message.from_user.id, name=name,
        phone=phone, slot=slot, lang=lang
    )
    await state.update_data(name=name)
    await state.set_state(None)

    # Кнопки: оплатить сейчас или позже
    kb = InlineKeyboardBuilder()
    kb.button(
        text="💳 Оплатить сейчас" if lang == "ru" else "💳 Оплатити зараз",
        callback_data="pay_consultation"
    )
    kb.button(
        text="⏰ Оплатить за 12 часов до сессии" if lang == "ru" else "⏰ Оплатити за 12 годин до сесії",
        callback_data="main_menu"
    )
    kb.adjust(1)

    await message.answer(
        t(lang, "booking_confirmed", slot=slot, name=name),
        reply_markup=kb.as_markup()
    )
    await message.bot.send_message(
        ADMIN_ID,
        t("ru", "admin_new_booking", name=name, phone=phone,
          slot=slot, user_id=message.from_user.id)
    )
