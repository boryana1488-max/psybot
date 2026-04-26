from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID
import storage

router = Router()


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


def admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Записи",      callback_data="adm_bookings")
    kb.button(text="📅 Слоты",       callback_data="adm_slots")
    kb.button(text="📆 Расписание",  callback_data="adm_schedule")
    kb.button(text="💰 Платежи",     callback_data="adm_payments")
    kb.button(text="👥 Клиенты",     callback_data="adm_clients")
    kb.button(text="📓 Дневники",    callback_data="adm_diary")
    kb.button(text="😊 Настроение",  callback_data="adm_mood")
    kb.button(text="💬 Отзывы",      callback_data="adm_reviews")
    kb.button(text="📢 Рассылка",    callback_data="adm_broadcast")
    kb.button(text="📈 Аналитика",   callback_data="adm_analytics")
    kb.button(text="👥 Клиенты",     callback_data="adm_client_status")
    kb.button(text="🌙 Чек-ины",     callback_data="adm_checkins")
    kb.button(text="💰 Платежи",     callback_data="adm_payments")
    kb.button(text="📤 Экспорт",     callback_data="adm_export")
    kb.adjust(2)
    return kb.as_markup()


def back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    return kb.as_markup()


async def safe_edit(callback, text, kb=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.message(CommandStart(), F.func(lambda m: is_admin(m.from_user.id)))
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👩\u200d⚕️ Панель психолога\n\nВыберите раздел:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm_menu")
async def adm_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await safe_edit(callback, "👩\u200d⚕️ Панель психолога\n\nВыберите раздел:", admin_menu_kb())


# ── Расписание ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_schedule")
async def adm_schedule(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    bookings = await storage.get_week_schedule()
    if not bookings:
        await safe_edit(callback, "На ближайшую неделю записей нет.", back_kb())
        return
    by_date: dict = {}
    for b in bookings:
        d = str(b.get("slot_date", "—"))
        by_date.setdefault(d, []).append(b)
    lines = ["📆 Расписание на неделю:\n"]
    for d, items in by_date.items():
        lines.append("📅 " + d)
        for b in items:
            paid = "✅" if b.get("paid") else "💳"
            lines.append("  " + paid + " " + b["name"] + " — " + b["slot"])
        lines.append("")
    await safe_edit(callback, "\n".join(lines), back_kb())


# ── Записи ────────────────────────────────────────────────────────────────────

def bookings_list_kb(bookings: list):
    kb = InlineKeyboardBuilder()
    for i, b in enumerate(bookings, 1):
        paid = "✅" if b.get("paid") else "💳"
        kb.button(
            text=paid + " #" + str(i) + " " + b["name"] + " — " + b["slot"],
            callback_data="adm_bk_" + str(i)
        )
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    return kb.as_markup()


def booking_actions_kb(n: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить слот",    callback_data="adm_bk_change_" + str(n))
    kb.button(text="❌ Отменить",          callback_data="adm_bk_cancel_" + str(n))
    kb.button(text="✅ Отметить оплату",   callback_data="adm_bk_paid_" + str(n))
    kb.button(text="🏁 Завершить сессию", callback_data="adm_bk_complete_" + str(n))
    kb.button(text="◀️ Назад",            callback_data="adm_bookings")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


@router.callback_query(F.data == "adm_bookings")
async def adm_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    all_bookings = await storage.get_all_bookings()
    if not all_bookings:
        await safe_edit(callback, "Записей пока нет.", back_kb())
        return
    await safe_edit(callback, "📋 Выберите запись:", bookings_list_kb(all_bookings))


@router.callback_query(F.data.regexp(r"^adm_bk_(\d+)$"))
async def adm_bk_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[2])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    paid = "✅ Оплачено" if b.get("paid") else "💳 Не оплачено"
    text = ("📋 Запись #" + str(n) + "\n\n"
            "👤 " + b["name"] + "\n"
            "📞 " + b["phone"] + "\n"
            "📅 " + b["slot"] + "\n"
            + paid)
    await safe_edit(callback, text, booking_actions_kb(n))


@router.callback_query(F.data.startswith("adm_bk_paid_"))
async def adm_bk_paid(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[3])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await storage.mark_paid(b)
    await callback.answer("✅ Оплата отмечена!")
    lang = b.get("lang", "ru")
    try:
        await callback.bot.send_message(
            b["user_id"],
            "✅ Ваша оплата подтверждена психологом. До встречи! 💙"
            if lang == "ru" else
            "✅ Ваша оплата підтверджена психологом. До зустрічі! 💙"
        )
    except Exception:
        pass
    await adm_bookings(callback)


@router.callback_query(F.data.startswith("adm_bk_cancel_"))
async def adm_bk_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[3])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    lang = b.get("lang", "ru")
    await storage.cancel_booking(b)
    await safe_edit(callback, "✅ Запись отменена.", back_kb())
    try:
        await callback.bot.send_message(
            b["user_id"],
            "❌ Ваша запись на " + b["slot"] + " отменена психологом.\n\nЗапишитесь снова: /start"
            if lang == "ru" else
            "❌ Ваш запис на " + b["slot"] + " скасовано психологом.\n\nЗапишіться знову: /start"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_bk_change_"))
async def adm_bk_change(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[3])
    free = await storage.get_free_slots()
    if not free:
        await callback.answer("Нет свободных слотов.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for s in free[:10]:
        slot = s["slot"] if isinstance(s, dict) else s
        kb.button(text="🕐 " + slot, callback_data="adm_bk_slot_" + str(n) + "_" + slot)
    kb.button(text="◀️ Назад", callback_data="adm_bookings")
    kb.adjust(1)
    await safe_edit(callback, "Выберите новый слот для записи #" + str(n) + ":", kb.as_markup())


@router.callback_query(F.data.startswith("adm_bk_slot_"))
async def adm_bk_slot_set(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_", 4)
    n = int(parts[3])
    new_slot = parts[4]
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    old_slot = b["slot"]
    lang = b.get("lang", "ru")
    await storage.change_booking_slot(b, new_slot)
    await safe_edit(callback, "✅ Слот изменён:\n" + old_slot + " → " + new_slot, back_kb())
    try:
        await callback.bot.send_message(
            b["user_id"],
            "📅 Ваша запись перенесена!\n\n" + old_slot + " → " + new_slot
            if lang == "ru" else
            "📅 Ваш запис перенесено!\n\n" + old_slot + " → " + new_slot
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_bk_complete_"))
async def adm_bk_complete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[3])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    await storage.complete_session(b["id"])
    lang = b.get("lang", "ru")
    await safe_edit(callback, "✅ Сессия завершена!", back_kb())
    review_kb = InlineKeyboardBuilder()
    review_kb.button(
        text="⭐ Оставить отзыв" if lang == "ru" else "⭐ Залишити відгук",
        callback_data="leave_review"
    )
    review_kb.button(
        text="📅 Записаться снова" if lang == "ru" else "📅 Записатися знову",
        callback_data="book"
    )
    review_kb.adjust(1)
    complete_text = (
        "💙 Сессия завершена! Спасибо за доверие.\n\n"
        "Если хотите — оставьте отзыв или запишитесь снова."
        if lang == "ru" else
        "💙 Сесія завершена! Дякуємо за довіру.\n\n"
        "Якщо хочете — залиште відгук або запишіться знову."
    )
    try:
        await callback.bot.send_message(b["user_id"], complete_text,
                                        reply_markup=review_kb.as_markup())
    except Exception:
        pass


# ── Слоты ─────────────────────────────────────────────────────────────────────

class SlotState(StatesGroup):
    adding = State()


def slots_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить",           callback_data="adm_addslot")
    kb.button(text="➖ Удалить",            callback_data="adm_rmslot_list")
    kb.button(text="🔄 Сгенерировать на 2 нед.", callback_data="adm_gen_slots")
    kb.button(text="◀️ Меню",              callback_data="adm_menu")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


@router.callback_query(F.data == "adm_slots")
async def adm_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    all_slots = await storage.get_all_slots()
    lines = ["📅 Свободные слоты:\n"]
    for s in all_slots:
        lines.append("🟢 " + s["slot"])
    if not all_slots:
        lines.append("Слотов нет.")
    await safe_edit(callback, "\n".join(lines), slots_kb())


@router.callback_query(F.data == "adm_gen_slots")
async def adm_gen_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await storage.generate_slots_for_week()
    await callback.answer("✅ Слоты обновлены на 2 недели!")
    await adm_slots(callback)


@router.callback_query(F.data == "adm_addslot")
async def adm_addslot_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(SlotState.adding)
    await safe_edit(callback, "Напиши время:\nПример: 15.05 Пятница 15:00", back_kb())


@router.message(SlotState.adding)
async def adm_addslot_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    slot = message.text.strip()
    ok = await storage.add_slot(slot)
    await state.clear()
    await message.answer(
        "✅ Добавлен: " + slot if ok else "⚠️ Уже существует: " + slot,
        reply_markup=admin_menu_kb()
    )


@router.callback_query(F.data == "adm_rmslot_list")
async def adm_rmslot_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    slots = await storage.get_all_slots()
    if not slots:
        await callback.answer("Слотов нет.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for s in slots:
        kb.button(text="❌ " + s["slot"], callback_data="adm_rm_" + s["slot"])
    kb.button(text="◀️ Назад", callback_data="adm_slots")
    kb.adjust(1)
    await safe_edit(callback, "Выбери слот для удаления:", kb.as_markup())


@router.callback_query(F.data.startswith("adm_rm_"))
async def adm_rmslot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    slot = callback.data[7:]
    await storage.remove_slot(slot)
    await callback.answer("Удалён: " + slot)
    await adm_rmslot_list(callback)


# ── Запросы на перенос ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_rs_ok_"))
async def rs_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    idx = int(callback.data.split("_")[3])
    pending = await storage.get_pending_reschedules()
    if idx >= len(pending):
        await callback.answer("Уже обработан.", show_alert=True)
        return
    req = pending[idx]
    b = await storage.get_booking_by_user(req["user_id"])
    if b:
        await storage.change_booking_slot(b, req["new_slot"])
    await storage.resolve_reschedule(req)
    await callback.message.edit_text(
        "✅ Перенос подтверждён:\n" + req["old_slot"] + " → " + req["new_slot"]
    )
    lang = b.get("lang", "ru") if b else "ru"
    try:
        await callback.bot.send_message(
            req["user_id"],
            "✅ Перенос подтверждён!\n\nНовое время: " + req["new_slot"]
            if lang == "ru" else
            "✅ Перенесення підтверджено!\n\nНовий час: " + req["new_slot"]
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_rs_no_"))
async def rs_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    idx = int(callback.data.split("_")[3])
    pending = await storage.get_pending_reschedules()
    if idx >= len(pending):
        await callback.answer("Уже обработан.", show_alert=True)
        return
    req = pending[idx]
    await storage.resolve_reschedule(req)
    await callback.message.edit_text("❌ Перенос отклонён.")
    b = await storage.get_booking_by_user(req["user_id"])
    lang = b.get("lang", "ru") if b else "ru"
    kb = InlineKeyboardBuilder()
    kb.button(
        text="💬 Написать психологу" if lang == "ru" else "💬 Написати психологу",
        url="tg://user?id=" + str(ADMIN_ID)
    )
    try:
        await callback.bot.send_message(
            req["user_id"],
            "❌ Запрос на перенос отклонён." if lang == "ru" else "❌ Запит на перенесення відхилено.",
            reply_markup=kb.as_markup()
        )
    except Exception:
        pass


# ── Клиенты (CRM) ─────────────────────────────────────────────────────────────

TAGS = {
    "new": "🆕 Новый",
    "regular": "⭐ Постоянный",
    "vip": "👑 VIP",
    "pause": "⏸ Пауза",
}
STATUSES = {
    "active": "✅ Активный",
    "pause": "⏸ На паузе",
    "done": "🏁 Завершил работу",
}


@router.callback_query(F.data == "adm_clients")
async def adm_clients(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await storage.get_all_users()
    if not users:
        await safe_edit(callback, "Клиентов нет.", back_kb())
        return
    kb = InlineKeyboardBuilder()
    for uid, info in users.items():
        tag_info = await storage.get_client_tag(uid)
        tag_icon = {"new": "🆕", "regular": "⭐", "vip": "👑", "pause": "⏸"}.get(
            tag_info.get("tag", "new"), "👤"
        )
        kb.button(
            text=tag_icon + " " + str(info.get("name", uid)),
            callback_data="adm_client_" + str(uid)
        )
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    await safe_edit(callback, "👥 Клиенты:", kb.as_markup())


@router.callback_query(F.data.startswith("adm_client_") & ~F.data.startswith("adm_client_card_"))
async def adm_client_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    info = (await storage.get_all_users()).get(uid, {})
    note = await storage.get_note(uid)
    tag_info = await storage.get_client_tag(uid)
    tag_label = TAGS.get(tag_info.get("tag", "new"), "🆕 Новый")
    status_label = STATUSES.get(tag_info.get("status", "active"), "✅ Активный")

    lines = [
        "👤 " + str(info.get("name", uid)),
        "🏷 Тег: " + tag_label,
        "📊 Статус: " + status_label,
        "📝 " + (note if note else "Заметок нет."),
    ]
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Карточка",         callback_data="adm_client_card_" + str(uid))
    kb.button(text="📝 Заметка",          callback_data="adm_note_edit_" + str(uid))
    kb.button(text="🏷 Тег",              callback_data="adm_tag_" + str(uid))
    kb.button(text="📊 Статус",           callback_data="adm_status_" + str(uid))
    kb.button(text="💬 Написать",         callback_data="adm_reply_" + str(uid))
    kb.button(text="📜 История сообщ.",   callback_data="adm_history_" + str(uid))
    kb.button(text="◀️ Назад",           callback_data="adm_clients")
    kb.adjust(2, 2, 2, 1)
    await safe_edit(callback, "\n".join(lines), kb.as_markup())


@router.callback_query(F.data.startswith("adm_client_card_"))
async def adm_client_card(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[3])
    info = (await storage.get_all_users()).get(uid, {})
    note = await storage.get_note(uid)
    stats = await storage.get_client_stats(uid)
    q = await storage.get_questionnaire(uid)
    tag_info = await storage.get_client_tag(uid)

    from handlers.client import TZ_LABEL_MAP
    tz_label = TZ_LABEL_MAP.get(info.get("tz", "tz_kyiv"), info.get("tz", "—"))
    emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
    last_mood = stats.get("last_mood")
    mood_str = emojis.get(last_mood, "—") + " " + str(last_mood) + "/5" if last_mood else "—"

    lines = [
        "📊 Карточка клиента",
        "",
        "👤 " + str(info.get("name", uid)),
        "🆔 " + str(uid),
        "🌍 " + tz_label,
        "🗣 Язык: " + str(info.get("lang", "—")),
        "🏷 Тег: " + TAGS.get(tag_info.get("tag", "new"), "—"),
        "📊 Статус: " + STATUSES.get(tag_info.get("status", "active"), "—"),
        "",
        "📅 Всего записей: " + str(stats["total"]),
        "✅ Оплачено: " + str(stats["paid"]),
        "🏁 Завершено сессий: " + str(stats["completed"]),
        "😊 Настроение: " + mood_str,
        "",
    ]
    if q:
        lines += [
            "📋 Анкета:",
            "• Тема: " + str(q.get("goal", "—")),
            "• Запрос: " + str(q.get("request", "—")),
            "• Источник: " + str(q.get("source", "—")),
            "",
        ]
    lines.append(("📝 Заметка:\n" + note) if note else "📝 Заметок нет.")

    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Заметка",  callback_data="adm_note_edit_" + str(uid))
    kb.button(text="💬 Написать", callback_data="adm_reply_" + str(uid))
    kb.button(text="◀️ Назад",   callback_data="adm_client_" + str(uid))
    kb.adjust(2, 1)
    await safe_edit(callback, "\n".join(lines), kb.as_markup())


# ── Теги ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_tag_"))
async def adm_tag(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    kb = InlineKeyboardBuilder()
    for tag_key, tag_label in TAGS.items():
        kb.button(text=tag_label, callback_data="adm_settag_" + str(uid) + "_" + tag_key)
    kb.button(text="◀️ Назад", callback_data="adm_client_" + str(uid))
    kb.adjust(2)
    await safe_edit(callback, "Выберите тег:", kb.as_markup())


@router.callback_query(F.data.startswith("adm_settag_"))
async def adm_settag(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_")
    uid = int(parts[2])
    tag = parts[3]
    await storage.set_client_tag(uid, tag)
    await callback.answer("✅ Тег обновлён: " + TAGS.get(tag, tag))
    # Возвращаем в карточку
    class FakeData:
        data = "adm_client_" + str(uid)
        from_user = callback.from_user
        message = callback.message
        bot = callback.bot
        async def answer(self, *a, **kw): pass
    await adm_client_view(callback)


# ── Статусы ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_status_"))
async def adm_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    kb = InlineKeyboardBuilder()
    for st_key, st_label in STATUSES.items():
        kb.button(text=st_label, callback_data="adm_setstatus_" + str(uid) + "_" + st_key)
    kb.button(text="◀️ Назад", callback_data="adm_client_" + str(uid))
    kb.adjust(1)
    await safe_edit(callback, "Выберите статус:", kb.as_markup())


@router.callback_query(F.data.startswith("adm_setstatus_"))
async def adm_setstatus(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_")
    uid = int(parts[2])
    status = parts[3]
    await storage.set_client_status(uid, status)
    await callback.answer("✅ Статус обновлён: " + STATUSES.get(status, status))
    await adm_client_view(callback)


# ── Заметки ───────────────────────────────────────────────────────────────────

class NoteState(StatesGroup):
    typing = State()


@router.callback_query(F.data.startswith("adm_note_edit_"))
async def adm_note_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[3])
    await state.update_data(note_uid=uid)
    await state.set_state(NoteState.typing)
    await safe_edit(callback, "Напиши заметку:", back_kb())


@router.message(NoteState.typing)
async def adm_note_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    await storage.set_note(data.get("note_uid"), message.text.strip())
    await state.clear()
    await message.answer("✅ Заметка сохранена.", reply_markup=admin_menu_kb())


# ── История сообщений ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_history_"))
async def adm_history(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    log = await storage.get_reply_log(uid)
    if not log:
        await safe_edit(callback, "История сообщений пуста.", back_kb())
        return
    lines = ["📜 История (последние 20):\n"]
    for entry in reversed(log):
        arrow = "→" if entry["direction"] == "admin→client" else "←"
        date_str = str(entry.get("created_at", ""))[:16]
        lines.append(arrow + " [" + date_str + "] " + str(entry["text"])[:100])
    await safe_edit(callback, "\n".join(lines), back_kb())


# ── Написать клиенту ──────────────────────────────────────────────────────────

class ReplyState(StatesGroup):
    typing = State()


@router.callback_query(F.data.startswith("adm_reply_"))
async def adm_reply_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[2])
    await state.update_data(reply_uid=uid)
    await state.set_state(ReplyState.typing)
    info = (await storage.get_all_users()).get(uid, {})
    name = info.get("name", str(uid))
    await safe_edit(callback, "Напишите сообщение для " + name + ":", back_kb())


@router.message(ReplyState.typing)
async def adm_reply_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    uid = data.get("reply_uid")
    text = message.text
    await state.clear()
    try:
        await message.bot.send_message(
            uid, "💬 Сообщение от психолога:\n\n" + text
        )
        await storage.log_reply(True, uid, text)
        await message.answer("✅ Отправлено.", reply_markup=admin_menu_kb())
    except Exception:
        await message.answer("❌ Не удалось отправить.", reply_markup=admin_menu_kb())


# ── Рассылка ──────────────────────────────────────────────────────────────────

class BroadcastState(StatesGroup):
    choosing_target = State()
    typing = State()


@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Всем клиентам",    callback_data="adm_bc_all")
    kb.button(text="👑 VIP клиентам",     callback_data="adm_bc_vip")
    kb.button(text="⭐ Постоянным",       callback_data="adm_bc_regular")
    kb.button(text="🆕 Новым",            callback_data="adm_bc_new")
    kb.button(text="◀️ Меню",            callback_data="adm_menu")
    kb.adjust(2, 2, 1)
    await safe_edit(callback, "Кому отправить рассылку?", kb.as_markup())


@router.callback_query(F.data.startswith("adm_bc_"))
async def adm_bc_target(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    target = callback.data.replace("adm_bc_", "")
    await state.update_data(bc_target=target)
    await state.set_state(BroadcastState.typing)
    await safe_edit(callback, "Напиши текст рассылки:", back_kb())


@router.message(BroadcastState.typing)
async def adm_bc_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    target = data.get("bc_target", "all")
    text = message.text.strip()
    await state.clear()

    if target == "all":
        users_dict = await storage.get_all_users()
        uids = list(users_dict.keys())
    else:
        uids = await storage.get_clients_by_tag(target)

    sent, failed = 0, 0
    for uid in uids:
        if uid == ADMIN_ID:
            continue
        try:
            await message.bot.send_message(uid, "📢 " + text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        "✅ Отправлено: " + str(sent) + " | Не доставлено: " + str(failed),
        reply_markup=admin_menu_kb()
    )


# ── Платежи ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_payments")
async def adm_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    log = await storage.get_payment_log()
    if not log:
        await safe_edit(callback, "Платежей нет.", back_kb())
        return
    lines = ["💰 Последние платежи:\n"]
    for r in log[:20]:
        confirmed = "✅" if r.get("confirmed") else "⏳"
        lines.append(
            confirmed + " " + str(r["name"]) + " | " +
            str(r["amount"]) + " UAH | " + str(r["purpose"]) + "\n" +
            "🔖 #" + str(r["tx_id"]) + " | " + str(r.get("created_at", ""))[:10]
        )
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Экспорт платежей", callback_data="adm_export_payments")
    kb.button(text="◀️ Меню",            callback_data="adm_menu")
    kb.adjust(1)
    await safe_edit(callback, "\n\n".join(lines), kb.as_markup())


@router.callback_query(F.data == "adm_export_payments")
async def adm_export_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    csv_data = await storage.export_payments_csv()
    f = BufferedInputFile(csv_data.encode("utf-8-sig"), filename="payments.csv")
    await callback.message.answer_document(f, caption="💰 Реестр платежей")
    await callback.answer()


# ── Дневник / Настроение / Отзывы / Чек-ины / Аналитика ─────────────────────

@router.callback_query(F.data == "adm_diary")
async def adm_diary(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_diary_entries()
    if not entries:
        await safe_edit(callback, "Записей дневника нет.", back_kb())
        return
    lines = ["📓 Дневник ощущений (" + str(len(entries)) + "):\n"]
    for e in entries[:15]:
        lines.append(
            "👤 " + str(e["name"]) + ": " +
            str(e["location"]) + " | " + str(e["sensation"]) +
            " | " + str(e["intensity"]) + "/10 | " + str(e["emotion"])
        )
    await safe_edit(callback, "\n".join(lines), back_kb())


@router.callback_query(F.data == "adm_mood")
async def adm_mood(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_mood_entries()
    if not entries:
        await safe_edit(callback, "Настроения нет.", back_kb())
        return
    emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
    lines = ["📊 Настроение (" + str(len(entries)) + " чел.):\n"]
    for e in sorted(entries, key=lambda x: x["mood"]):
        lines.append(emojis.get(e["mood"], "❓") + " " + str(e["name"]) + " — " + str(e["mood"]) + "/5")
    avg = sum(e["mood"] for e in entries) / len(entries)
    lines.append("\nСреднее: " + str(round(avg, 1)) + " ⭐")
    await safe_edit(callback, "\n".join(lines), back_kb())


@router.callback_query(F.data == "adm_reviews")
async def adm_reviews(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    reviews = await storage.get_all_reviews()
    if not reviews:
        await safe_edit(callback, "Отзывов нет.", back_kb())
        return
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    lines = ["💬 Отзывы (" + str(len(reviews)) + ") | Среднее: " + str(round(avg, 1)) + " ⭐\n"]
    for r in reviews[-10:]:
        lines.append("⭐" * r["rating"] + " " + str(r["name"]) + "\n" + str(r["comment"]))
    await safe_edit(callback, "\n\n".join(lines), back_kb())


@router.callback_query(F.data == "adm_checkins")
async def adm_checkins(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_checkin_entries()
    if not entries:
        await safe_edit(callback, "Чек-инов нет.", back_kb())
        return
    lines = ["🌙 Чек-ины (" + str(len(entries)) + "):\n"]
    for e in entries[:15]:
        lines.append("👤 " + str(e["name"]) + " (" + str(e.get("created_at", ""))[:10] + "):\n" + str(e["text"]))
    await safe_edit(callback, "\n\n".join(lines), back_kb())


@router.callback_query(F.data == "adm_analytics")
async def adm_analytics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    a = await storage.get_analytics()
    lines = [
        "📈 Аналитика\n",
        "👥 Клиентов: " + str(a["users"]),
        "📅 Активных записей: " + str(a["bookings"]),
        "✅ Оплачено: " + str(a["paid"]),
        "🗓 Свободных слотов: " + str(a["slots_free"]),
        "⭐ Средний рейтинг: " + str(round(a["avg_rating"], 1)),
        "😊 Среднее настроение: " + str(round(a["avg_mood"], 1)) + "/5",
        "📓 Записей дневника: " + str(a["diary"]),
        "🌙 Чек-инов: " + str(a["checkins"]),
    ]
    await safe_edit(callback, "\n".join(lines), back_kb())


@router.callback_query(F.data == "adm_export")
async def adm_export(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    csv_data = await storage.export_bookings_csv()
    f = BufferedInputFile(csv_data.encode("utf-8-sig"), filename="bookings.csv")
    await callback.message.answer_document(f, caption="📤 Все записи")
    await callback.answer()


# ── Статус клиента ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_client_status")
async def adm_show_clients(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await storage.get_all_users()
    if not users:
        await safe_edit(callback, "Клиентов нет.", back_kb())
        return
    lines = ["👥 Клиенты:\n"]
    for uid, info in list(users.items())[:20]:
        stats = await storage.get_client_stats(uid)
        emojis = {1:"😢",2:"😔",3:"😐",4:"🙂",5:"😊"}
        mood = emojis.get(stats.get("last_mood"), "—")
        lines.append(
            "👤 " + str(info.get("name","?")) + "\n"
            "📅 " + str(stats["total"]) + " зап | ✅ " + str(stats["paid"]) + " опл | " + mood
        )
    await safe_edit(callback, "\n\n".join(lines), back_kb())


# ── Реестр платежей ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_payments")
async def adm_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    log = await storage.get_payment_log()
    if not log:
        await safe_edit(callback, "Платежей нет.", back_kb())
        return
    lines = ["💰 Реестр платежей (" + str(len(log)) + "):\n"]
    for r in log[:15]:
        status = "✅" if r.get("confirmed") else "⏳"
        lines.append(
            status + " " + str(r["name"]) + " | " + str(r["amount"]) + " UAH\n"
            "🔖 #" + str(r["tx_id"]) + " | " + str(r.get("created_at",""))[:10]
        )
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Экспорт CSV", callback_data="adm_export_payments")
    kb.button(text="◀️ Меню",       callback_data="adm_menu")
    kb.adjust(1)
    await safe_edit(callback, "\n\n".join(lines), kb.as_markup())


@router.callback_query(F.data == "adm_export_payments")
async def adm_export_payments(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    from aiogram.types import BufferedInputFile
    csv = await storage.export_payments_csv()
    f = BufferedInputFile(csv.encode("utf-8-sig"), filename="payments.csv")
    await callback.message.answer_document(f, caption="💰 Реестр платежей")
    await callback.answer()


# ── Диагностика ───────────────────────────────────────────────────────────────

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(
        "🆔 Ваш ID: `" + str(message.from_user.id) + "`\n"
        "ADMIN_ID: `" + str(ADMIN_ID) + "`\n"
        "Совпадает: " + ("✅" if message.from_user.id == ADMIN_ID else "❌"),
        parse_mode="Markdown"
    )
