from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from collections import defaultdict

from texts import t
from config import ADMIN_ID
from images_config import get_image
import storage

router = Router()

# Двухуровневый выбор TZ: регион → город
# offset = часы относительно Киева (UTC+2)
TZ_REGIONS = {
    "ru": [
        ("🇺🇦 Украина и СНГ", "reg_ua"),
        ("🇪🇺 Европа",        "reg_eu"),
        ("🌎 Америка",        "reg_am"),
        ("🌏 Азия",           "reg_as"),
    ],
    "uk": [
        ("🇺🇦 Україна та СНД", "reg_ua"),
        ("🇪🇺 Європа",         "reg_eu"),
        ("🌎 Америка",         "reg_am"),
        ("🌏 Азія",            "reg_as"),
    ],
}

TZ_CITIES = {
    "reg_ua": [
        ("Киев (UTC+2)",      "tz_kyiv",    0),
        ("Тбилиси (UTC+4)",   "tz_tbilisi", +2),
        ("Кишинёв (UTC+2)",   "tz_chisinau", 0),
        ("Баку (UTC+4)",      "tz_baku",    +2),
        ("Алматы (UTC+5)",    "tz_almaty",  +3),
        ("Ташкент (UTC+5)",   "tz_tashkent",+3),
    ],
    "reg_eu": [
        ("Лондон (UTC+0)",    "tz_london",  -2),
        ("Берлин (UTC+1)",    "tz_berlin",  -1),
        ("Париж (UTC+1)",     "tz_paris",   -1),
        ("Варшава (UTC+1)",   "tz_warsaw",  -1),
        ("Хельсинки (UTC+2)", "tz_helsinki", 0),
        ("Лиссабон (UTC+0)",  "tz_lisbon",  -2),
    ],
    "reg_am": [
        ("Нью-Йорк (UTC-5)",  "tz_ny",      -7),
        ("Чикаго (UTC-6)",    "tz_chicago", -8),
        ("Денвер (UTC-7)",    "tz_denver",  -9),
        ("Лос-Анджелес (UTC-8)", "tz_la",  -10),
        ("Торонто (UTC-5)",   "tz_toronto", -7),
        ("Монреаль (UTC-5)",  "tz_montreal",-7),
    ],
    "reg_as": [
        ("Дубай (UTC+4)",     "tz_dubai",   +2),
        ("Стамбул (UTC+3)",   "tz_istanbul",+1),
        ("Тель-Авив (UTC+2)", "tz_telaviv", 0),
        ("Бангкок (UTC+7)",   "tz_bangkok", +5),
        ("Гонконг (UTC+8)",   "tz_hk",      +6),
        ("Токио (UTC+9)",     "tz_tokyo",   +7),
    ],
}

# tz_code -> offset от Киева
TZ_OFFSET_MAP = {city[1]: city[2] for cities in TZ_CITIES.values() for city in cities}

# Обратная карта tz -> label
TZ_LABEL_MAP = {city[1]: city[0] for cities in TZ_CITIES.values() for city in cities}

TIMEZONE_OFFSETS = TZ_OFFSET_MAP  # совместимость
TIMEZONE_LABELS = TZ_LABEL_MAP


class BookingState(StatesGroup):
    choosing_lang = State()
    choosing_region = State()
    choosing_tz = State()
    choosing_date = State()
    choosing_slot = State()
    entering_name = State()
    entering_phone = State()


def get_user_lang(data: dict) -> str:
    return data.get("lang", "ru")


def get_tz_offset(data: dict) -> int:
    return TZ_OFFSET_MAP.get(data.get("tz", "tz_kyiv"), 0)


def apply_tz_offset(slot_str: str, offset_hours: int) -> str:
    """Смещает время в строке слота на offset_hours. Формат: '15.04 Пятница 10:00'"""
    if offset_hours == 0:
        return slot_str
    try:
        parts = slot_str.split(" ")
        time_part = parts[-1]  # '10:00'
        h, m = map(int, time_part.split(":"))
        total = h * 60 + m + offset_hours * 60
        # Нормализация
        total = total % (24 * 60)
        if total < 0:
            total += 24 * 60
        nh, nm = divmod(total, 60)
        new_time = f"{nh:02d}:{nm:02d}"
        return " ".join(parts[:-1] + [new_time])
    except Exception:
        return slot_str


def main_menu_kb(lang: str, has_booking: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.button(text="🌬 Практики", callback_data="practices")
    kb.button(text="🆘 SOS", callback_data="sos")
    kb.button(text=t(lang, "mood_btn"), callback_data="mood")
    kb.button(text="💬 Отзывы" if lang == "ru" else "💬 Відгуки", callback_data="client_reviews")
    kb.button(text="📊 Мой прогресс" if lang == "ru" else "📊 Мій прогрес", callback_data="my_progress")
    kb.button(text="🌙 Чек-ин" if lang == "ru" else "🌙 Чек-ін", callback_data="checkin_toggle")
    kb.button(text="🌸 " + ("Аффирмации" if lang == "ru" else "Афірмації"), callback_data="affirmations")
    kb.button(text="📬 " + ("Послания" if lang == "ru" else "Послання"), callback_data="daily_messages")
    kb.button(text="📚 Курсы" if lang == "ru" else "📚 Курси", callback_data="courses")
    kb.button(text="🎓 " + ("Дипломы" if lang == "ru" else "Дипломи"), callback_data="diplomas")
    kb.button(text="💬 Написать психологу" if lang == "ru" else "💬 Написати психологу", callback_data="contact_psychologist")
    if has_booking:
        kb.button(text="📋 Мои записи" if lang == "ru" else "📋 Мої записи", callback_data="my_bookings")
        kb.button(text="❌ Отменить" if lang == "ru" else "❌ Скасувати", callback_data="cancel_booking")
        kb.button(text="🔄 Перенести" if lang == "ru" else "🔄 Перенести", callback_data="reschedule_booking")
        kb.button(text="💳 Оплатить" if lang == "ru" else "💳 Оплатити", callback_data="pay_consultation")
        kb.button(text="⭐ Отзыв" if lang == "ru" else "⭐ Відгук", callback_data="leave_review")
    kb.adjust(2)
    return kb.as_markup()


def lang_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇺🇦 Українська", callback_data="lang_uk")
    kb.adjust(2)
    return kb.as_markup()


def tz_region_kb(lang: str):
    kb = InlineKeyboardBuilder()
    for label, cb in TZ_REGIONS[lang]:
        kb.button(text=label, callback_data=cb)
    kb.adjust(2)
    return kb.as_markup()

def tz_city_kb(region: str):
    kb = InlineKeyboardBuilder()
    for label, cb, _ in TZ_CITIES.get(region, []):
        kb.button(text=label, callback_data=cb)
    kb.button(text="◀️ Назад", callback_data="tz_back")
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
    await state.set_state(BookingState.choosing_region)
    text = ("🌍 Откуда вы? Выберите регион:"
            if lang == "ru" else
            "🌍 Звідки ви? Оберіть регіон:")
    photo = get_image("timezone")
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=text, reply_markup=tz_region_kb(lang))
            await callback.message.delete()
            return
        except Exception:
            pass
    await safe_edit(callback, text, tz_region_kb(lang))


@router.callback_query(BookingState.choosing_region, F.data.startswith("reg_"))
async def choose_region(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    region = callback.data  # reg_ua / reg_eu / reg_am / reg_as
    await state.update_data(tz_region=region)
    await state.set_state(BookingState.choosing_tz)
    text = ("Выберите ваш город:" if lang == "ru" else "Оберіть ваше місто:")
    await safe_edit(callback, text, tz_city_kb(region))


@router.callback_query(F.data == "tz_back")
async def tz_back(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await state.set_state(BookingState.choosing_region)
    text = ("🌍 Выберите регион:" if lang == "ru" else "🌍 Оберіть регіон:")
    await safe_edit(callback, text, tz_region_kb(lang))


@router.callback_query(BookingState.choosing_tz, F.data.startswith("tz_"))
async def choose_tz(callback: CallbackQuery, state: FSMContext):
    tz = callback.data  # tz_kyiv / tz_berlin etc.
    await state.update_data(tz=tz)
    await state.set_state(None)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await storage.register_user(callback.from_user.id, lang, tz=tz)
    has_booking = await storage.get_booking_by_user(callback.from_user.id) is not None
    # Если анкеты ещё нет — предлагаем заполнить перед первой записью
    has_q = await storage.has_questionnaire(callback.from_user.id)
    if not has_q:
        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Заполнить анкету (1 мин)" if lang == "ru" else "📋 Заповнити анкету (1 хв)",
                  callback_data="start_questionnaire")
        kb.button(text="Пропустить" if lang == "ru" else "Пропустити", callback_data="main_menu")
        kb.adjust(1)
        text = ("Прежде чем записаться, ответьте на 3 вопроса — это поможет психологу лучше подготовиться."
                if lang == "ru" else
                "Перш ніж записатися, дайте відповідь на 3 запитання — це допоможе психологу краще підготуватися.")
        await safe_edit(callback, text, kb.as_markup())
        return
    await safe_edit(callback, t(lang, "main_menu"), main_menu_kb(lang, has_booking))


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    has_booking = await storage.get_booking_by_user(callback.from_user.id) is not None
    text = t(lang, "main_menu")
    kb = main_menu_kb(lang, has_booking)
    photo = get_image("main_menu")
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
            await callback.message.delete()
            return
        except Exception:
            pass
    await safe_edit(callback, text, kb)


@router.callback_query(F.data == "diplomas")
async def show_diplomas(callback: CallbackQuery, state: FSMContext):
    from aiogram.types import InputMediaPhoto
    lang = (await state.get_data()).get("lang", "ru")
    diploma_keys = ["diploma_1", "diploma_2", "diploma_3", "diploma_4", "diploma_5"]

    media = []
    for key in diploma_keys:
        photo = get_image(key)
        if photo:
            media.append(InputMediaPhoto(media=photo))

    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")

    if not media:
        text = ("🎓 Дипломы пока не загружены." if lang == "ru" else "🎓 Дипломи ще не завантажені.")
        await callback.message.answer(text, reply_markup=kb.as_markup())
    else:
        # Медиагруппа — все фото одним блоком
        try:
            await callback.message.answer_media_group(media=media)
        except Exception:
            # Fallback — по одному
            for m in media:
                try:
                    await callback.message.answer_photo(photo=m.media)
                except Exception:
                    pass
        text = ("🎓 Дипломы и сертификаты психолога" if lang == "ru" else "🎓 Дипломи та сертифікати психолога")
        await callback.message.answer(text, reply_markup=kb.as_markup())

    try:
        await callback.answer()
    except Exception:
        pass


# ── Мои записи ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    tz_offset = get_tz_offset(data)
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
        cancelled = (" ❌ отменена" if lang == "ru" else " ❌ скасовано") if b.get("cancelled") else ""
        paid_str = ("✅ оплачено" if lang == "ru" else "✅ оплачено") if b.get("paid") else ("⏳ не оплачено" if lang == "ru" else "⏳ не оплачено")
        slot_display = apply_tz_offset(b["slot"], tz_offset)
        text += f"{status} {slot_display}{cancelled} — {paid_str}\n"

    await safe_edit(callback, text, kb.as_markup())


# ── Отзывы (публичные) ────────────────────────────────────────────────────────

@router.callback_query(F.data == "client_reviews")
async def client_reviews(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    reviews = await storage.get_all_reviews()
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад" if lang == "ru" else "◀️ Назад", callback_data="main_menu")
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


# ── Запись — выбор даты (уровень 1) ──────────────────────────────────────────

@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    tz_offset = get_tz_offset(data)

    slots = await storage.get_free_slots()
    if len(slots) < 3:
        await storage.generate_slots_for_week()
        slots = await storage.get_free_slots()

    if not slots:
        await callback.answer(t(lang, "no_slots"), show_alert=True)
        return

    # Группируем слоты по дате
    by_date = defaultdict(list)
    for s in slots:
        date_key = str(s.get("slot_date", ""))
        by_date[date_key].append(s)

    sorted_dates = sorted(by_date.keys())
    # 2 колонки: левая сверху вниз, потом правая сверху вниз
    n = len(sorted_dates)
    half = (n + 1) // 2
    left_col = sorted_dates[:half]
    right_col = sorted_dates[half:]
    # Чередуем: left[0], right[0], left[1], right[1]...
    ordered = []
    for i in range(half):
        if i < len(left_col):
            ordered.append(left_col[i])
        if i < len(right_col):
            ordered.append(right_col[i])

    kb = InlineKeyboardBuilder()
    for date_key in ordered:
        sample = by_date[date_key][0]
        slot_str = sample["slot"]
        parts = slot_str.split(" ")
        label = " ".join(parts[:2]) if len(parts) >= 2 else slot_str
        kb.button(text=f"📅 {label}", callback_data=f"bookdate_{date_key}")
    kb.button(text=t(lang, "back"), callback_data="main_menu")
    # Строки по 2, последняя (Назад) одна
    kb.adjust(*([2] * half + [1]))
    await state.set_state(BookingState.choosing_date)
    text = "Выберите дату:" if lang == "ru" else "Оберіть дату:"
    photo = get_image("booking")
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=text, reply_markup=kb.as_markup())
            await callback.message.delete()
            return
        except Exception:
            pass
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(BookingState.choosing_date, F.data.startswith("bookdate_"))
async def booking_date_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = get_user_lang(data)
    tz_offset = get_tz_offset(data)
    date_key = callback.data[9:]  # убираем "bookdate_"

    slots = await storage.get_free_slots()
    day_slots = [s for s in slots if str(s.get("slot_date", "")) == date_key]

    if not day_slots:
        await callback.answer("Слоты заняты, выберите другой день." if lang == "ru"
                              else "Слоти зайняті, оберіть інший день.", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for s in day_slots:
        display = apply_tz_offset(s["slot"], tz_offset)
        # Показываем только время
        time_part = display.split(" ")[-1]
        kb.button(text=f"🕐 {time_part}", callback_data=f"slot_{s['slot']}")
    kb.button(text="◀️ Назад" if lang == "ru" else "◀️ Назад", callback_data="book")
    kb.adjust(2)
    await state.set_state(BookingState.choosing_slot)
    text = ("Выберите время:" if lang == "ru" else "Оберіть час:")
    await safe_edit(callback, text, kb.as_markup())


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
    tz_offset = get_tz_offset(data)

    await storage.add_booking(
        user_id=message.from_user.id, name=name,
        phone=phone, slot=slot, lang=lang
    )
    await state.update_data(name=name)
    await state.set_state(None)

    slot_display = apply_tz_offset(slot, tz_offset)

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
        t(lang, "booking_confirmed", slot=slot_display, name=name),
        reply_markup=kb.as_markup()
    )

    # Уведомление психологу — всегда на русском, время по Киеву
    username = message.from_user.username
    tg_link = f"tg://user?id={message.from_user.id}"
    username_line = f"@{username}" if username else "—"
    tz_label = TIMEZONE_LABELS.get(data.get("tz", "ua"), "Украина")
    await message.bot.send_message(
        ADMIN_ID,
        f"📬 Новая запись!\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"📅 Время (Киев): {slot}\n"
        f"🌍 Часовой пояс клиента: {tz_label}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"✈️ Username: {username_line}\n"
        f"🔗 Написать: {tg_link}"
    )


@router.callback_query(F.data == "contact_psychologist")
async def contact_psychologist(callback: CallbackQuery, state: FSMContext):
    from config import ADMIN_ID
    lang = (await state.get_data()).get("lang", "ru")
    kb = InlineKeyboardBuilder()
    kb.button(
        text="💬 Написать" if lang == "ru" else "💬 Написати",
        url=f"tg://user?id={ADMIN_ID}"
    )
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    text = ("💬 Вы можете написать психологу напрямую:"
            if lang == "ru" else
            "💬 Ви можете написати психологу напряму:")
    await safe_edit(callback, text, kb.as_markup())
