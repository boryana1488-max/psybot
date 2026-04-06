from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
import storage

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Записи", callback_data="adm_bookings")
    kb.button(text="📅 Слоты", callback_data="adm_slots")
    kb.button(text="📆 Расписание", callback_data="adm_schedule")
    kb.button(text="📓 Дневники", callback_data="adm_diary")
    kb.button(text="😊 Настроение", callback_data="adm_mood")
    kb.button(text="💬 Отзывы", callback_data="adm_reviews")
    kb.button(text="📢 Рассылка", callback_data="adm_broadcast")
    kb.button(text="📈 Аналитика", callback_data="adm_analytics")
    kb.button(text="📝 Заметки", callback_data="adm_notes")
    kb.button(text="🌙 Чек-ины", callback_data="adm_checkins")
    kb.button(text="📤 Экспорт", callback_data="adm_export")
    kb.adjust(2)
    return kb.as_markup()


def back_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    return kb.as_markup()


@router.message(CommandStart(), F.func(lambda m: is_admin(m.from_user.id)))
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👩‍⚕️ Панель психолога\n\nВыберите раздел:", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.clear()
    await callback.message.edit_text("👩‍⚕️ Панель психолога\n\nВыберите раздел:", reply_markup=admin_menu_kb())


# ── Расписание на неделю ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_schedule")
async def adm_schedule(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    bookings = await storage.get_week_schedule()
    if not bookings:
        await callback.message.edit_text("На ближайшую неделю записей нет.", reply_markup=back_admin_kb())
        return

    # Группируем по дате
    by_date: dict = {}
    for b in bookings:
        d = str(b.get("slot_date", "—"))
        by_date.setdefault(d, []).append(b)

    text = "📆 Расписание на неделю:\n\n"
    for d, items in by_date.items():
        text += f"📅 {d}\n"
        for b in items:
            paid = "✅" if b.get("paid") else "💳"
            text += f"  {paid} {b['name']} — {b['slot']}\n"
        text += "\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


# ── Записи ────────────────────────────────────────────────────────────────────

def bookings_list_kb(bookings: list):
    kb = InlineKeyboardBuilder()
    for i, b in enumerate(bookings, 1):
        paid = "✅" if b.get("paid") else "💳"
        kb.button(text=f"{paid} #{i} {b['name']} — {b['slot']}", callback_data=f"adm_bk_{i}")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    return kb.as_markup()


def booking_actions_kb(n: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить слот", callback_data=f"adm_bk_change_{n}")
    kb.button(text="❌ Отменить", callback_data=f"adm_bk_cancel_{n}")
    kb.button(text="✅ Отметить оплату", callback_data=f"adm_bk_paid_{n}")
    kb.button(text="◀️ Назад", callback_data="adm_bookings")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def slot_choose_kb(n: int, free_slots: list):
    kb = InlineKeyboardBuilder()
    for s in free_slots[:10]:
        slot = s["slot"] if isinstance(s, dict) else s
        kb.button(text=f"🕐 {slot}", callback_data=f"adm_bk_slot_{n}_{slot}")
    kb.button(text="◀️ Назад", callback_data="adm_bookings")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "adm_bookings")
async def adm_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    all_bookings = await storage.get_all_bookings()
    if not all_bookings:
        await callback.message.edit_text("Записей пока нет.", reply_markup=back_admin_kb())
        return
    await callback.message.edit_text("📋 Выберите запись:", reply_markup=bookings_list_kb(all_bookings))


@router.callback_query(F.data.regexp(r'^adm_bk_(\d+)$'))
async def adm_booking_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[2])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    paid = "✅ Оплачено" if b.get("paid") else "💳 Не оплачено"
    text = f"📋 Запись #{n}\n\n👤 {b['name']}\n📞 {b['phone']}\n📅 {b['slot']}\n{paid}"
    await callback.message.edit_text(text, reply_markup=booking_actions_kb(n))


@router.callback_query(F.data.startswith("adm_bk_paid_"))
async def adm_booking_mark_paid(callback: CallbackQuery):
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
            "✅ Ваша оплата подтверждена психологом. До встречи! 💙" if lang == "ru"
            else "✅ Ваша оплата підтверджена психологом. До зустрічі! 💙"
        )
    except Exception:
        pass
    await adm_bookings(callback)


@router.callback_query(F.data.startswith("adm_bk_cancel_"))
async def adm_booking_cancel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[3])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    user_id = b["user_id"]
    lang = b.get("lang", "ru")
    await storage.cancel_booking(b)
    await callback.message.edit_text("✅ Запись отменена.", reply_markup=back_admin_kb())
    try:
        await callback.bot.send_message(
            user_id,
            f"❌ Ваша запись на {b['slot']} отменена психологом.\n\nЕсли хотите записаться снова — /start."
            if lang == "ru" else
            f"❌ Ваш запис на {b['slot']} скасовано психологом.\n\nЯкщо хочете записатися знову — /start."
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_bk_change_"))
async def adm_booking_change(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[3])
    free = await storage.get_free_slots()
    if not free:
        await callback.answer("Нет свободных слотов.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Выберите новый слот для записи #{n}:",
        reply_markup=slot_choose_kb(n, free)
    )


@router.callback_query(F.data.startswith("adm_bk_slot_"))
async def adm_booking_slot_set(callback: CallbackQuery):
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
    await callback.message.edit_text(
        f"✅ Слот изменён:\n{old_slot} → {new_slot}", reply_markup=back_admin_kb()
    )
    try:
        await callback.bot.send_message(
            b["user_id"],
            f"📅 Ваша запись перенесена!\n\n{old_slot} → {new_slot}"
            if lang == "ru" else
            f"📅 Ваш запис перенесено!\n\n{old_slot} → {new_slot}"
        )
    except Exception:
        pass


# ── Слоты ─────────────────────────────────────────────────────────────────────

def slots_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="adm_addslot")
    kb.button(text="➖ Удалить", callback_data="adm_rmslot_list")
    kb.button(text="🔄 Обновить на 2 недели", callback_data="adm_gen_slots")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(2, 1, 1)
    return kb.as_markup()


@router.callback_query(F.data == "adm_slots")
async def adm_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    all_slots = await storage.get_all_slots()
    lines = ["📅 Свободные слоты:\n"]
    for s in all_slots:
        lines.append(f"🟢 {s['slot']}")
    if not all_slots:
        lines.append("Слотов нет.")
    await callback.message.edit_text("\n".join(lines), reply_markup=slots_kb())


@router.callback_query(F.data == "adm_gen_slots")
async def adm_gen_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await storage.generate_slots_for_week()
    await callback.answer("✅ Слоты обновлены на 2 недели!")
    await adm_slots(callback)


class SlotState(StatesGroup):
    adding = State()


@router.callback_query(F.data == "adm_addslot")
async def adm_addslot_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(SlotState.adding)
    await callback.message.edit_text(
        "Напиши время:\nПример: 15.03 Пятница 15:00", reply_markup=back_admin_kb()
    )


@router.message(SlotState.adding)
async def adm_addslot_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    slot = message.text.strip()
    ok = await storage.add_slot(slot)
    await state.clear()
    await message.answer(
        f"✅ Добавлен: {slot}" if ok else f"⚠️ Уже существует: {slot}",
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
        kb.button(text=f"❌ {s['slot']}", callback_data=f"adm_rm_{s['slot']}")
    kb.button(text="◀️ Назад", callback_data="adm_slots")
    kb.adjust(1)
    await callback.message.edit_text("Выбери слот для удаления:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm_rm_"))
async def adm_rmslot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    slot = callback.data[7:]
    await storage.remove_slot(slot)
    await callback.answer(f"Удалён: {slot}")
    slots = await storage.get_all_slots()
    if not slots:
        await callback.message.edit_text("Все слоты удалены.", reply_markup=back_admin_kb())
        return
    kb = InlineKeyboardBuilder()
    for s in slots:
        kb.button(text=f"❌ {s['slot']}", callback_data=f"adm_rm_{s['slot']}")
    kb.button(text="◀️ Назад", callback_data="adm_slots")
    kb.adjust(1)
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


# ── Запросы на перенос ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_reschedule_approve_"))
async def reschedule_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    idx = int(callback.data.split("_")[3])
    pending = await storage.get_pending_reschedules()
    if idx >= len(pending):
        await callback.answer("Запрос уже обработан.", show_alert=True)
        return
    req = pending[idx]
    b = await storage.get_booking_by_user(req["user_id"])
    if b:
        await storage.change_booking_slot(b, req["new_slot"])
    await storage.resolve_reschedule(req)
    await callback.message.edit_text(f"✅ Перенос подтверждён:\n{req['old_slot']} → {req['new_slot']}")
    lang = b.get("lang", "ru") if b else "ru"
    try:
        await callback.bot.send_message(
            req["user_id"],
            f"✅ Перенос подтверждён!\n\nНовое время: {req['new_slot']}" if lang == "ru"
            else f"✅ Перенесення підтверджено!\n\nНовий час: {req['new_slot']}"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_reschedule_reject_"))
async def reschedule_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    idx = int(callback.data.split("_")[3])
    pending = await storage.get_pending_reschedules()
    if idx >= len(pending):
        await callback.answer("Запрос уже обработан.", show_alert=True)
        return
    req = pending[idx]
    await storage.resolve_reschedule(req)
    await callback.message.edit_text("❌ Перенос отклонён.")
    b = await storage.get_booking_by_user(req["user_id"])
    lang = b.get("lang", "ru") if b else "ru"
    kb = InlineKeyboardBuilder()
    kb.button(
        text="💬 Связаться с психологом" if lang == "ru" else "💬 Зв'язатися з психологом",
        url=f"tg://user?id={ADMIN_ID}"
    )
    try:
        await callback.bot.send_message(
            req["user_id"],
            "❌ Запрос на перенос отклонён." if lang == "ru" else "❌ Запит на перенесення відхилено.",
            reply_markup=kb.as_markup()
        )
    except Exception:
        pass


# ── Экспорт ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_export")
async def adm_export(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    csv_data = await storage.export_bookings_csv()
    file = BufferedInputFile(csv_data.encode("utf-8-sig"), filename="bookings.csv")
    await callback.message.answer_document(file, caption="📤 Все записи")
    await callback.answer()


# ── Аналитика ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_analytics")
async def adm_analytics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    a = await storage.get_analytics()
    text = (
        f"📈 Аналитика\n\n"
        f"👥 Клиентов: {a['users']}\n"
        f"📅 Активных записей: {a['bookings']}\n"
        f"✅ Оплачено: {a['paid']}\n"
        f"🗓 Свободных слотов: {a['slots_free']}\n"
        f"⭐ Средний рейтинг: {a['avg_rating']:.1f}\n"
        f"😊 Среднее настроение: {a['avg_mood']:.1f}/5\n"
        f"📓 Записей дневника: {a['diary']}\n"
        f"🌙 Чек-инов: {a['checkins']}\n"
    )
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


# ── Дневник / Настроение / Отзывы / Чек-ины ──────────────────────────────────

@router.callback_query(F.data == "adm_diary")
async def adm_diary(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_diary_entries()
    if not entries:
        await callback.message.edit_text("Записей дневника нет.", reply_markup=back_admin_kb())
        return
    text = f"📓 Дневник ({len(entries)}):\n\n"
    for e in entries[:15]:
        text += f"👤 {e['name']}: {e['location']} | {e['sensation']} | {e['intensity']}/10 | {e['emotion']}\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


@router.callback_query(F.data == "adm_mood")
async def adm_mood(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_mood_entries()
    if not entries:
        await callback.message.edit_text("Настроения нет.", reply_markup=back_admin_kb())
        return
    emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
    lines = [f"📊 Настроение ({len(entries)} чел.):\n"]
    for e in sorted(entries, key=lambda x: x["mood"]):
        lines.append(f"{emojis.get(e['mood'], '❓')} {e['name']} — {e['mood']}/5")
    avg = sum(e["mood"] for e in entries) / len(entries)
    lines.append(f"\nСреднее: {avg:.1f} ⭐")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_admin_kb())


@router.callback_query(F.data == "adm_reviews")
async def adm_reviews(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    reviews = await storage.get_all_reviews()
    if not reviews:
        await callback.message.edit_text("Отзывов нет.", reply_markup=back_admin_kb())
        return
    avg = sum(r["rating"] for r in reviews) / len(reviews)
    text = f"💬 Отзывы ({len(reviews)}) | Среднее: {avg:.1f} ⭐\n\n"
    for r in reviews[-10:]:
        text += f"{'⭐' * r['rating']} {r['name']}\n{r['comment']}\n\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


@router.callback_query(F.data == "adm_checkins")
async def adm_checkins(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_checkin_entries()
    if not entries:
        await callback.message.edit_text("Чек-инов нет.", reply_markup=back_admin_kb())
        return
    text = f"🌙 Чек-ины ({len(entries)}):\n\n"
    for e in entries[:15]:
        text += f"👤 {e['name']} ({e['created_at']}):\n{e['text']}\n\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


# ── Заметки ───────────────────────────────────────────────────────────────────

class NoteState(StatesGroup):
    typing_note = State()


@router.callback_query(F.data == "adm_notes")
async def adm_notes_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await storage.get_all_users()
    if not users:
        await callback.message.edit_text("Клиентов нет.", reply_markup=back_admin_kb())
        return
    kb = InlineKeyboardBuilder()
    for uid, info in users.items():
        note = await storage.get_note(uid)
        icon = "📝" if note else "👤"
        kb.button(text=f"{icon} {info.get('name', uid)}", callback_data=f"adm_note_view_{uid}")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    await callback.message.edit_text("📝 Клиенты:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm_note_view_"))
async def adm_note_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[3])
    info = (await storage.get_all_users()).get(uid, {})
    note = await storage.get_note(uid)
    text = f"👤 {info.get('name', uid)}\n\n"
    text += f"📝 {note}" if note else "📝 Заметок нет."
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить заметку", callback_data=f"adm_note_edit_{uid}")
    kb.button(text="◀️ Назад", callback_data="adm_notes")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm_note_edit_"))
async def adm_note_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[3])
    await state.update_data(note_target_uid=uid)
    await state.set_state(NoteState.typing_note)
    await callback.message.edit_text("Напиши заметку:", reply_markup=back_admin_kb())


@router.message(NoteState.typing_note)
async def adm_note_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    await storage.set_note(data.get("note_target_uid"), message.text.strip())
    await state.clear()
    await message.answer("✅ Заметка сохранена.", reply_markup=admin_menu_kb())


# ── Рассылка ──────────────────────────────────────────────────────────────────

class BroadcastState(StatesGroup):
    typing = State()


@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(BroadcastState.typing)
    await callback.message.edit_text("Напиши текст рассылки:", reply_markup=back_admin_kb())


@router.message(BroadcastState.typing)
async def adm_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    text = message.text.strip()
    users = await storage.get_all_users()
    await state.clear()
    sent, failed = 0, 0
    for uid in users:
        if uid == ADMIN_ID: continue
        try:
            await message.bot.send_message(uid, f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
    await message.answer(
        f"✅ Отправлено: {sent} | Не доставлено: {failed}",
        reply_markup=admin_menu_kb()
    )


# ── Диагностика ───────────────────────────────────────────────────────────────

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(
        f"🆔 Ваш ID: `{message.from_user.id}`\n"
        f"ADMIN_ID: `{ADMIN_ID}`\n"
        f"Совпадает: {'✅' if message.from_user.id == ADMIN_ID else '❌'}",
        parse_mode="Markdown"
    )
