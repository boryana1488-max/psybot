"""
Оплата консультации и курсов.
- За 12 часов до сессии клиенту приходит напоминание об оплате
- Клиент жмёт "Оплатил" и отправляет чек (фото/PDF)
- Психолог получает чек с ID транзакции
"""
import uuid
import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot

from config import ADMIN_ID
import storage

router = Router()

CONSULTATION_PRICE = 999
COURSE_PRICE = 3000
MONO_CARD = "4441 1110 4879 8072"
RECIPIENT = "Мозер Александра"

COURSES = {
    "course_vzroslenie": {
        "name_ru": "🌱 «Взросление»",
        "name_uk": "🌱 «Дорослішання»",
        "desc_ru": "Бодинамический Курс Лилии Копейченко\n\nГлубокая работа с телом и психикой через призму бодинамики. Курс помогает осознать паттерны взросления и освободиться от ограничивающих убеждений.",
        "desc_uk": "Бодинамічний Курс Лілії Копейченко\n\nГлибока робота з тілом і психікою через призму бодинаміки. Курс допомагає усвідомити патерни дорослішання та звільнитися від обмежуючих переконань.",
        "price": COURSE_PRICE,
    }
}


class PaymentState(StatesGroup):
    waiting_receipt = State()


# ── Реквизиты ────────────────────────────────────────────────────────────────

def payment_details(lang: str, price: int, tx_id: str, item_name: str) -> str:
    if lang == "ru":
        return (
            f"💳 Реквизиты для оплаты\n\n"
            f"🏦 Банк: Monobank\n"
            f"💳 Номер карты: {MONO_CARD}\n"
            f"👤 Получатель: {RECIPIENT}\n"
            f"💰 Сумма: {price} UAH\n"
            f"📋 За: {item_name}\n"
            f"🔖 ID транзакции: #{tx_id}\n\n"
            f"После оплаты нажмите «Оплатил/Оплатила» и отправьте фото или PDF квитанции."
        )
    else:
        return (
            f"💳 Реквізити для оплати\n\n"
            f"🏦 Банк: Monobank\n"
            f"💳 Номер картки: {MONO_CARD}\n"
            f"👤 Отримувач: {RECIPIENT}\n"
            f"💰 Сума: {price} UAH\n"
            f"📋 За: {item_name}\n"
            f"🔖 ID транзакції: #{tx_id}\n\n"
            f"Після оплати натисніть «Оплатив/Оплатила» і надішліть фото або PDF квитанції."
        )


def paid_kb(lang: str, tx_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Оплатил/Оплатила" if lang == "ru" else "✅ Оплатив/Оплатила",
        callback_data=f"paid_{tx_id}"
    )
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


# ── Оплата консультации ───────────────────────────────────────────────────────

@router.callback_query(F.data == "pay_consultation")
async def pay_consultation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    tx_id = str(uuid.uuid4())[:8].upper()
    await state.update_data(tx_id=tx_id, tx_type="consultation", tx_price=CONSULTATION_PRICE)

    item = "Консультация психолога" if lang == "ru" else "Консультація психолога"
    text = payment_details(lang, CONSULTATION_PRICE, tx_id, item)

    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=paid_kb(lang, tx_id))
        else:
            await callback.message.edit_text(text, reply_markup=paid_kb(lang, tx_id))
    except Exception:
        await callback.message.answer(text, reply_markup=paid_kb(lang, tx_id))


# ── Курсы ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "courses")
async def courses_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    kb = InlineKeyboardBuilder()
    for key, course in COURSES.items():
        name = course["name_ru"] if lang == "ru" else course["name_uk"]
        kb.button(text=name, callback_data=f"course_{key}")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    title = "📚 Курсы" if lang == "ru" else "📚 Курси"
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=title, reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(title, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(title, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("course_course_"))
async def course_detail(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    key = callback.data.replace("course_", "", 1)
    course = COURSES.get(key)
    if not course:
        await callback.answer("Курс не найден.", show_alert=True)
        return

    name = course["name_ru"] if lang == "ru" else course["name_uk"]
    desc = course["desc_ru"] if lang == "ru" else course["desc_uk"]
    price = course["price"]
    tx_id = str(uuid.uuid4())[:8].upper()
    await state.update_data(tx_id=tx_id, tx_type=key, tx_price=price)

    text = f"{name}\n\n{desc}\n\n💰 Стоимость: {price} UAH" if lang == "ru" else f"{name}\n\n{desc}\n\n💰 Вартість: {price} UAH"

    kb = InlineKeyboardBuilder()
    kb.button(
        text=f"💳 Оплатить {price} UAH" if lang == "ru" else f"💳 Оплатити {price} UAH",
        callback_data=f"pay_course_{key}"
    )
    kb.button(text="◀️ Назад", callback_data="courses")
    kb.adjust(1)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("pay_course_"))
async def pay_course(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    key = callback.data.replace("pay_course_", "")
    course = COURSES.get(key)
    if not course:
        await callback.answer("Курс не найден.", show_alert=True)
        return

    tx_id = str(uuid.uuid4())[:8].upper()
    await state.update_data(tx_id=tx_id, tx_type=key, tx_price=course["price"])

    name = course["name_ru"] if lang == "ru" else course["name_uk"]
    text = payment_details(lang, course["price"], tx_id, name)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=paid_kb(lang, tx_id))
        else:
            await callback.message.edit_text(text, reply_markup=paid_kb(lang, tx_id))
    except Exception:
        await callback.message.answer(text, reply_markup=paid_kb(lang, tx_id))


# ── Клиент нажал "Оплатил" ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("paid_"))
async def paid_pressed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    tx_id = callback.data.replace("paid_", "")
    await state.update_data(awaiting_receipt=True, tx_id=tx_id)
    await state.set_state(PaymentState.waiting_receipt)

    text = ("📎 Пожалуйста, отправьте фото или PDF квитанции об оплате."
            if lang == "ru" else
            "📎 Будь ласка, надішліть фото або PDF квитанції про оплату.")
    await callback.message.answer(text)


@router.message(PaymentState.waiting_receipt, F.photo | F.document)
async def receipt_received(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    tx_id = data.get("tx_id", "???")
    tx_price = data.get("tx_price", "?")
    tx_type = data.get("tx_type", "?")
    name = data.get("name", message.from_user.first_name or "Клиент")

    await state.set_state(None)

    # Подтверждение клиенту
    text = (f"✅ Спасибо! Квитанция получена.\n\n🔖 ID транзакции: #{tx_id}\n\nПсихолог проверит оплату и подтвердит запись."
            if lang == "ru" else
            f"✅ Дякуємо! Квитанцію отримано.\n\n🔖 ID транзакції: #{tx_id}\n\nПсихолог перевірить оплату і підтвердить запис.")
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await message.answer(text, reply_markup=kb.as_markup())

    # Пересылаем чек психологу
    admin_text = (
        f"💳 Оплата получена!\n\n"
        f"👤 {name} (@{message.from_user.username or '—'})\n"
        f"🆔 TG ID: {message.from_user.id}\n"
        f"🔖 TX ID: #{tx_id}\n"
        f"💰 Сумма: {tx_price} UAH\n"
        f"📋 За: {tx_type}"
    )
    await message.bot.send_message(ADMIN_ID, admin_text)

    # Пересылаем сам файл/фото
    if message.photo:
        await message.bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🧾 Квитанция #{tx_id}")
    elif message.document:
        await message.bot.send_document(ADMIN_ID, message.document.file_id, caption=f"🧾 Квитанция #{tx_id}")


@router.message(PaymentState.waiting_receipt)
async def receipt_wrong_format(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = ("Пожалуйста, отправьте фото или PDF файл квитанции." if lang == "ru"
            else "Будь ласка, надішліть фото або PDF файл квитанції.")
    await message.answer(text)


# ── Напоминание об оплате за 12 часов ────────────────────────────────────────

async def payment_reminder_loop(bot: Bot):
    """Проверяем каждый час — если до сессии осталось 12 часов, напоминаем об оплате."""
    import re
    from datetime import datetime, timedelta

    DAYS_MAP = {
        "Понедельник": 0, "Вторник": 1, "Среда": 2, "Четверг": 3,
        "Пятница": 4, "Суббота": 5, "Воскресенье": 6,
        "Понеділок": 0, "Вівторок": 1, "Середа": 2, "Четвер": 3,
        "П'ятниця": 4, "Субота": 5, "Неділя": 6,
    }

    notified: set = set()  # tx ключи уже уведомлённых

    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        for b in storage.get_all_bookings():
            key = f"{b['user_id']}_{b['slot']}"
            if key in notified:
                continue
            # Парсим слот "День ЧЧ:ММ"
            for day_name, day_num in DAYS_MAP.items():
                if b["slot"].startswith(day_name):
                    time_part = b["slot"].replace(day_name, "").strip()
                    match = re.match(r"(\d+):(\d+)", time_part)
                    if not match:
                        break
                    h, m = int(match.group(1)), int(match.group(2))
                    # Находим ближайшую дату с этим днём недели
                    days_ahead = (day_num - now.weekday()) % 7
                    session_dt = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=days_ahead)
                    diff = (session_dt - now).total_seconds() / 3600
                    if 11.5 <= diff <= 12.5:
                        lang = b.get("lang", "ru")
                        tx_id = str(uuid.uuid4())[:8].upper()
                        item = "Консультация психолога" if lang == "ru" else "Консультація психолога"
                        text = (
                            f"⏰ Напоминание об оплате\n\n"
                            f"Ваша консультация завтра в {time_part}.\n"
                            f"Пожалуйста, оплатите заранее."
                            if lang == "ru" else
                            f"⏰ Нагадування про оплату\n\n"
                            f"Ваша консультація завтра о {time_part}.\n"
                            f"Будь ласка, оплатіть заздалегідь."
                        )
                        kb = InlineKeyboardBuilder()
                        kb.button(
                            text="💳 Оплатить" if lang == "ru" else "💳 Оплатити",
                            callback_data="pay_consultation"
                        )
                        try:
                            await bot.send_message(b["user_id"], text, reply_markup=kb.as_markup())
                            notified.add(key)
                        except Exception:
                            pass
                    break
