from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
import storage

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ── Меню ──────────────────────────────────────────────────────────────────────

def admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Записи", callback_data="adm_bookings")
    kb.button(text="📅 Слоты", callback_data="adm_slots")
    kb.button(text="📓 Дневники", callback_data="adm_diary")
    kb.button(text="😊 Настроение", callback_data="adm_mood")
    kb.button(text="💬 Отзывы", callback_data="adm_reviews")
    kb.button(text="📢 Рассылка", callback_data="adm_broadcast")
    kb.button(text="📈 Аналитика", callback_data="adm_analytics")
    kb.button(text="📝 Заметки", callback_data="adm_notes")
    kb.button(text="🌙 Чек-ины", callback_data="adm_checkins")
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


# ── Записи ────────────────────────────────────────────────────────────────────

def bookings_list_kb(bookings: list):
    kb = InlineKeyboardBuilder()
    for i, b in enumerate(bookings, 1):
        kb.button(text=f"#{i} {b['name']} — {b['slot']}", callback_data=f"adm_bk_{i}")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    return kb.as_markup()

def booking_actions_kb(n: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить слот", callback_data=f"adm_bk_change_{n}")
    kb.button(text="❌ Отменить запись", callback_data=f"adm_bk_cancel_{n}")
    kb.button(text="◀️ Назад", callback_data="adm_bookings")
    kb.adjust(2, 1)
    return kb.as_markup()

def slot_choose_kb(n: int, free_slots: list):
    kb = InlineKeyboardBuilder()
    for s in free_slots:
        kb.button(text=f"🕐 {s}", callback_data=f"adm_bk_slot_{n}_{s}")
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


@router.callback_query(F.data.startswith("adm_bk_") & ~F.data.startswith("adm_bk_change_") & ~F.data.startswith("adm_bk_cancel_") & ~F.data.startswith("adm_bk_slot_"))
async def adm_booking_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    n = int(callback.data.split("_")[2])
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    text = f"📋 Запись #{n}\n\n👤 {b['name']}\n📞 {b['phone']}\n📅 {b['slot']}"
    await callback.message.edit_text(text, reply_markup=booking_actions_kb(n))


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
    # Уведомить клиента
    cancel_text = (
        f"❌ Ваша запись на {b['slot']} была отменена психологом.\n\nЕсли хотите записаться снова — нажмите /start."
        if lang == "ru" else
        f"❌ Ваш запис на {b['slot']} було скасовано психологом.\n\nЯкщо хочете записатися знову — натисніть /start."
    )
    try:
        await callback.bot.send_message(user_id, cancel_text)
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
    await callback.message.edit_text(f"Выберите новый слот для записи #{n}:", reply_markup=slot_choose_kb(n, free))


@router.callback_query(F.data.startswith("adm_bk_slot_"))
async def adm_booking_slot_set(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    parts = callback.data.split("_", 4)  # adm_bk_slot_N_SLOT
    n = int(parts[3])
    new_slot = parts[4]
    b = await storage.get_booking_by_index(n)
    if not b:
        await callback.answer("Запись не найдена.", show_alert=True)
        return
    old_slot = b["slot"]
    user_id = b["user_id"]
    lang = b.get("lang", "ru")
    await storage.change_booking_slot(b, new_slot)
    await callback.message.edit_text(
        f"✅ Слот изменён:\n{old_slot} → {new_slot}",
        reply_markup=back_admin_kb()
    )
    notify = (
        f"📅 Ваша запись перенесена!\n\nСтарое время: {old_slot}\nНовое время: {new_slot}\n\nЕсли неудобно — напишите /start."
        if lang == "ru" else
        f"📅 Ваш запис перенесено!\n\nСтарий час: {old_slot}\nНовий час: {new_slot}\n\nЯкщо незручно — напишіть /start."
    )
    try:
        await callback.bot.send_message(user_id, notify)
    except Exception:
        pass


# ── Слоты ─────────────────────────────────────────────────────────────────────

def slots_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="adm_addslot")
    kb.button(text="➖ Удалить", callback_data="adm_rmslot_list")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(2, 1)
    return kb.as_markup()


@router.callback_query(F.data == "adm_slots")
async def adm_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    all_slots = await storage.get_all_slots()
    taken = await storage.get_booked_slots()
    lines = ["📅 Слоты:\n"]
    for s in all_slots:
        lines.append(f"{'🔴' if s in taken else '🟢'} {s}")
    if not all_slots:
        lines.append("Слотов нет.")
    await callback.message.edit_text("\n".join(lines), reply_markup=slots_kb())


class SlotState(StatesGroup):
    adding = State()

@router.callback_query(F.data == "adm_addslot")
async def adm_addslot_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(SlotState.adding)
    await callback.message.edit_text("Напиши время:\nПример: Пятница 15:00", reply_markup=back_admin_kb())

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
        kb.button(text=f"❌ {s}", callback_data=f"adm_rm_{s}")
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
        kb.button(text=f"❌ {s}", callback_data=f"adm_rm_{s}")
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
    await callback.message.edit_text(
        f"✅ Перенос подтверждён:\n{req['old_slot']} → {req['new_slot']}"
    )
    lang = b.get("lang", "ru") if b else "ru"
    notify = (
        f"✅ Ваш запрос на перенос подтверждён!\n\nНовое время: {req['new_slot']}"
        if lang == "ru" else
        f"✅ Ваш запит на перенесення підтверджено!\n\nНовий час: {req['new_slot']}"
    )
    try:
        await callback.bot.send_message(req["user_id"], notify)
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
    await callback.message.edit_text(f"❌ Перенос отклонён.")
    b = await storage.get_booking_by_user(req["user_id"])
    lang = b.get("lang", "ru") if b else "ru"
    kb = InlineKeyboardBuilder()
    if lang == "ru":
        kb.button(text="💬 Связаться с психологом", url=f"tg://user?id={ADMIN_ID}")
        notify = f"❌ Ваш запрос на перенос отклонён.\n\nВы можете связаться с психологом напрямую:"
    else:
        kb.button(text="💬 Зв'язатися з психологом", url=f"tg://user?id={ADMIN_ID}")
        notify = f"❌ Ваш запит на перенесення відхилено.\n\nВи можете зв'язатися з психологом напряму:"
    try:
        await callback.bot.send_message(req["user_id"], notify, reply_markup=kb.as_markup())
    except Exception:
        pass


# ── Дневник / Настроение / Отзывы ────────────────────────────────────────────

@router.callback_query(F.data == "adm_diary")
async def adm_diary(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_diary_entries()
    if not entries:
        await callback.message.edit_text("Записей дневника нет.", reply_markup=back_admin_kb())
        return
    text = f"📓 Дневник ощущений ({len(entries)}):\n\n"
    for e in entries[-15:]:
        text += f"👤 {e['name']}: {e['location']} | {e['sensation']} | {e['intensity']}/10 | {e['emotion']}\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


@router.callback_query(F.data == "adm_mood")
async def adm_mood(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_mood_entries()
    if not entries:
        await callback.message.edit_text("Записей настроения нет.", reply_markup=back_admin_kb())
        return
    by_user: dict = {}
    for e in entries:
        by_user[e["user_id"]] = e
    emojis = {1: "😢", 2: "😔", 3: "😐", 4: "🙂", 5: "😊"}
    lines = [f"📊 Настроение ({len(by_user)} чел.):\n"]
    for e in sorted(by_user.values(), key=lambda x: x["mood"]):
        lines.append(f"{emojis.get(e['mood'], '❓')} {e['name']} — {e['mood']}/5")
    avg = sum(e["mood"] for e in by_user.values()) / len(by_user)
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
    for user_id in users:
        if user_id == ADMIN_ID:
            continue
        try:
            await message.bot.send_message(user_id, f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ Отправлено: {sent} | Не доставлено: {failed}", reply_markup=admin_menu_kb())


# ── Диагностика ───────────────────────────────────────────────────────────────

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(
        f"🆔 Ваш ID: `{message.from_user.id}`\n"
        f"ADMIN_ID: `{ADMIN_ID}`\n"
        f"Совпадает: {'✅' if message.from_user.id == ADMIN_ID else '❌'}",
        parse_mode="Markdown"
    )


# ── Аналитика ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_analytics")
async def adm_analytics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return

    bookings = await storage.get_all_bookings()
    users = await storage.get_all_users()
    reviews = await storage.get_all_reviews()
    mood = await storage.get_mood_entries()
    diary = await storage.get_diary_entries()
    checkins = await storage.get_checkin_entries()

    avg_rating = (sum(r["rating"] for r in reviews) / len(reviews)) if reviews else 0
    avg_mood = (sum(e["mood"] for e in mood) / len(mood)) if mood else 0
    slots_total = len(await storage.get_all_slots())
    slots_taken = len(storage.booked_slots)

    text = (
        f"📈 Аналитика\n\n"
        f"👥 Всего клиентов: {len(users)}\n"
        f"📅 Записей активных: {len(bookings)}\n"
        f"🗓 Слоты: {slots_taken}/{slots_total} занято\n"
        f"⭐ Средний рейтинг: {avg_rating:.1f}\n"
        f"😊 Среднее настроение: {avg_mood:.1f}/5\n"
        f"📓 Записей дневника: {len(diary)}\n"
        f"🌙 Чек-инов: {len(checkins)}\n"
    )
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


# ── Заметки о клиентах ────────────────────────────────────────────────────────

class NoteState(StatesGroup):
    choosing_client = State()
    typing_note = State()


@router.callback_query(F.data == "adm_notes")
async def adm_notes_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    users = await storage.get_all_users()
    if not users:
        await callback.message.edit_text("Клиентов пока нет.", reply_markup=back_admin_kb())
        return
    kb = InlineKeyboardBuilder()
    for uid, info in users.items():
        note_icon = "📝" if await storage.get_note(uid) else "👤"
        kb.button(text=f"{note_icon} {info.get('name', uid)}", callback_data=f"adm_note_view_{uid}")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(1)
    await callback.message.edit_text("📝 Выбери клиента:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm_note_view_"))
async def adm_note_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[3])
    info = await storage.get_all_users().get(uid, {})
    note = await storage.get_note(uid)
    name = info.get("name", str(uid))

    text = f"👤 {name}\n\n"
    text += f"📝 Заметка:\n{note}" if note else "📝 Заметок нет."

    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Добавить/изменить заметку", callback_data=f"adm_note_edit_{uid}")
    kb.button(text="◀️ Назад", callback_data="adm_notes")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm_note_edit_"))
async def adm_note_edit(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    uid = int(callback.data.split("_")[3])
    await state.update_data(note_target_uid=uid)
    await state.set_state(NoteState.typing_note)
    await callback.message.edit_text("Напиши заметку о клиенте:", reply_markup=back_admin_kb())


@router.message(NoteState.typing_note)
async def adm_note_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    uid = data.get("note_target_uid")
    await storage.set_note(uid, message.text.strip())
    await state.clear()
    await message.answer("✅ Заметка сохранена.", reply_markup=admin_menu_kb())


# ── Чек-ины (просмотр админом) ────────────────────────────────────────────────

@router.callback_query(F.data == "adm_checkins")
async def adm_checkins(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    entries = await storage.get_checkin_entries()
    if not entries:
        await callback.message.edit_text("Чек-инов пока нет.", reply_markup=back_admin_kb())
        return
    text = f"🌙 Вечерние чек-ины ({len(entries)}):\n\n"
    for e in entries[-15:]:
        text += f"👤 {e['name']} ({e['date']}):\n{e['text']}\n\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())
