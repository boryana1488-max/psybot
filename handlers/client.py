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
    kb.button(text="💬 Отзывы клиентов" if lang == "ru" else "💬 Відгуки клієнтів", callback_data="client_reviews")
    kb.button(text="📊 Мой прогресс" if lang == "ru" else "📊 Мій прогрес", callback_data="my_progress")
    kb.button(text="🌙 Вечерний чек-ин" if lang == "ru" else "🌙 Вечірній чек-ін", callback_data="checkin_toggle")
    if has_booking:
        kb.button(text="❌ Отменить запись" if lang == "ru" else "❌ Скасувати запис", callback_data="cancel_booking")
        kb.button(text="🔄 Перенести запись" if lang == "ru" else "🔄 Перенести запис", callback_data="reschedule_booking")
        kb.button(text="⭐ Оставить отзыв" if lang == "ru" else "⭐ Залишити відгук", callback_data="leave_review")
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
    storage.register_user(callback.from_user.id, lang)
    has_booking = storage.get_booking_by_user(callback.from_user.id) is not None
    await safe_edit(callback, t(lang, "main_menu"), main_menu_kb(lang, has_booking))


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    has_booking = storage.get_booking_by_user(callback.from_user.id) is not None
    await safe_edit(callback, t(lang, "main_menu"), main_menu_kb(lang, has_booking))


# ── Отзывы клиентов (публичный раздел) ───────────────────────────────────────

@router.callback_query(F.data == "client_reviews")
async def client_reviews(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    reviews = storage.get_all_reviews()
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад" if lang == "ru" else "◀️ Назад", callback_data="main_menu")

    if not reviews:
        text = ("💬 Отзывов пока нет.\n\nБудьте первым!" if lang == "ru"
                else "💬 Відгуків поки немає.\n\nБудьте першим!")
        await safe_edit(callback, text, kb.as_markup())
        return

    avg = sum(r["rating"] for r in reviews) / len(reviews)
    stars = "⭐" * round(avg)
    text = f"💬 Отзывы клиентов\n{stars} {avg:.1f} из 5\n\n" if lang == "ru" else f"💬 Відгуки клієнтів\n{stars} {avg:.1f} з 5\n\n"
    for r in reviews[-8:]:
        text += f"{'⭐' * r['rating']} {r['name']}\n{r['comment']}\n\n"
    await safe_edit(callback, text, kb.as_markup())


# ── Запись ────────────────────────────────────────────────────────────────────

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
    await safe_edit(callback, t(lang, "choose_slot"), kb.as_markup())


@router.callback_query(BookingState.choosing_slot, F.data.startswith("slot_"))
async def slot_chosen(callback: CallbackQuery, state: FSMContext):
    slot = callback.data.replace("slot_", "")
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
    storage.add_booking(user_id=message.from_user.id, name=name, phone=phone, slot=slot, lang=lang)
    await state.update_data(name=name)
    await state.set_state(None)
    await message.answer(
        t(lang, "booking_confirmed", slot=slot, name=name),
        reply_markup=main_menu_kb(lang, has_booking=True)
    )
    await message.bot.send_message(
        ADMIN_ID,
        t("ru", "admin_new_booking", name=name, phone=phone, slot=slot, user_id=message.from_user.id)
    )
