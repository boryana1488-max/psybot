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


# ── Админ-меню ────────────────────────────────────────────────────────────────

def admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Записи", callback_data="adm_bookings")
    kb.button(text="📅 Слоты", callback_data="adm_slots")
    kb.button(text="📓 Дневники", callback_data="adm_diary")
    kb.button(text="😊 Настроение", callback_data="adm_mood")
    kb.button(text="💬 Отзывы", callback_data="adm_reviews")
    kb.button(text="📢 Рассылка", callback_data="adm_broadcast")
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
    await message.answer(
        "👩‍⚕️ Панель психолога\n\nВыберите раздел:",
        reply_markup=admin_menu_kb()
    )


@router.callback_query(F.data == "adm_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "👩‍⚕️ Панель психолога\n\nВыберите раздел:",
        reply_markup=admin_menu_kb()
    )


# ── Записи ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_bookings")
async def adm_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    all_bookings = storage.get_all_bookings()
    if not all_bookings:
        text = "Записей пока нет."
    else:
        text = f"📋 Записи ({len(all_bookings)}):\n\n"
        for i, b in enumerate(all_bookings, 1):
            text += f"#{i} {b['name']} | {b['phone']} | {b['slot']}\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


# ── Слоты ─────────────────────────────────────────────────────────────────────

def slots_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить слот", callback_data="adm_addslot")
    kb.button(text="➖ Удалить слот", callback_data="adm_rmslot_list")
    kb.button(text="◀️ Меню", callback_data="adm_menu")
    kb.adjust(2, 1)
    return kb.as_markup()


@router.callback_query(F.data == "adm_slots")
async def adm_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    all_slots = storage.get_all_slots()
    taken = storage.booked_slots
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
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(SlotState.adding)
    await callback.message.edit_text(
        "Напиши время нового слота:\n\nПример: Пятница 15:00",
        reply_markup=back_admin_kb()
    )


@router.message(SlotState.adding)
async def adm_addslot_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    slot = message.text.strip()
    ok = storage.add_slot(slot)
    await state.clear()
    await message.answer(
        f"✅ Слот добавлен: {slot}" if ok else f"⚠️ Слот уже существует: {slot}",
        reply_markup=admin_menu_kb()
    )


@router.callback_query(F.data == "adm_rmslot_list")
async def adm_rmslot_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    slots = storage.get_all_slots()
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
    if not is_admin(callback.from_user.id):
        return
    slot = callback.data[7:]
    storage.remove_slot(slot)
    await callback.answer(f"Удалён: {slot}")
    # Обновляем список
    slots = storage.get_all_slots()
    if not slots:
        await callback.message.edit_text("Все слоты удалены.", reply_markup=back_admin_kb())
        return
    kb = InlineKeyboardBuilder()
    for s in slots:
        kb.button(text=f"❌ {s}", callback_data=f"adm_rm_{s}")
    kb.button(text="◀️ Назад", callback_data="adm_slots")
    kb.adjust(1)
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


# ── Дневник ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_diary")
async def adm_diary(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    entries = storage.get_diary_entries()
    if not entries:
        await callback.message.edit_text("Записей дневника нет.", reply_markup=back_admin_kb())
        return
    text = f"📓 Дневник ощущений ({len(entries)}):\n\n"
    for e in entries[-15:]:
        text += f"👤 {e['name']}: {e['location']} | {e['sensation']} | {e['intensity']}/10 | {e['emotion']}\n"
    await callback.message.edit_text(text, reply_markup=back_admin_kb())


# ── Настроение ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_mood")
async def adm_mood(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    entries = storage.get_mood_entries()
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


# ── Отзывы ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_reviews")
async def adm_reviews(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    reviews = storage.get_all_reviews()
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
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(BroadcastState.typing)
    await callback.message.edit_text(
        "Напиши текст рассылки — он уйдёт всем клиентам:",
        reply_markup=back_admin_kb()
    )


@router.message(BroadcastState.typing)
async def adm_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    users = storage.get_all_users()
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
    await message.answer(
        f"✅ Рассылка отправлена!\nДоставлено: {sent}\nНе доставлено: {failed}",
        reply_markup=admin_menu_kb()
    )


# ── Текстовые команды (запасной вариант) ──────────────────────────────────────

@router.message(Command("myid"))
async def my_id(message: Message):
    await message.answer(
        f"🆔 Ваш ID: `{message.from_user.id}`\n"
        f"ADMIN_ID в боте: `{ADMIN_ID}`\n"
        f"Совпадает: {'✅' if message.from_user.id == ADMIN_ID else '❌'}",
        parse_mode="Markdown"
    )
