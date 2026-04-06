from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
import storage

router = Router()


class DiaryState(StatesGroup):
    location = State()
    sensation = State()
    intensity = State()
    emotion = State()


def kb(options: list[tuple], back_cb="practices"):
    b = InlineKeyboardBuilder()
    for label, cb in options:
        b.button(text=label, callback_data=cb)
    b.button(text="◀️ Назад", callback_data=back_cb)
    b.adjust(2)
    return b.as_markup()


async def safe_edit(callback, text, markup):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=markup)
        else:
            await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "p_diary")
async def diary_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DiaryState.location)
    await safe_edit(callback,
        "📓 Дневник ощущений\n\n🔍 Шаг 1/4: Где в теле больше всего ощущений?",
        kb([
            ("Голова/Шея", "dl_Голова/Шея"), ("Грудь", "dl_Грудь"),
            ("Живот", "dl_Живот"), ("Спина", "dl_Спина"),
            ("Руки/Ноги", "dl_Руки/Ноги"), ("Всё тело", "dl_Всё тело"),
        ])
    )


@router.callback_query(DiaryState.location, F.data.startswith("dl_"))
async def diary_location(callback: CallbackQuery, state: FSMContext):
    await state.update_data(location=callback.data[3:])
    await state.set_state(DiaryState.sensation)
    await safe_edit(callback,
        "💭 Шаг 2/4: Как это ощущается?",
        kb([
            ("Сжатие", "ds_Сжатие"), ("Жар/Холод", "ds_Жар/Холод"),
            ("Пустота", "ds_Пустота"), ("Тяжесть", "ds_Тяжесть"),
            ("Покалывание", "ds_Покалывание"), ("Пульсация", "ds_Пульсация"),
            ("Онемение", "ds_Онемение"), ("Ком в горле", "ds_Ком в горле"),
        ])
    )


@router.callback_query(DiaryState.sensation, F.data.startswith("ds_"))
async def diary_sensation(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sensation=callback.data[3:])
    await state.set_state(DiaryState.intensity)
    b = InlineKeyboardBuilder()
    for i in range(1, 11):
        b.button(text=str(i), callback_data=f"di_{i}")
    b.adjust(5)
    await safe_edit(callback, "📊 Шаг 3/4: Интенсивность от 1 (едва) до 10 (невыносимо):", b.as_markup())


@router.callback_query(DiaryState.intensity, F.data.startswith("di_"))
async def diary_intensity(callback: CallbackQuery, state: FSMContext):
    await state.update_data(intensity=int(callback.data[3:]))
    await state.set_state(DiaryState.emotion)
    await safe_edit(callback,
        "❤️ Шаг 4/4: Что вы чувствуете?",
        kb([
            ("Тревога", "de_Тревога"), ("Гнев", "de_Гнев"),
            ("Радость", "de_Радость"), ("Усталость", "de_Усталость"),
            ("Грусть", "de_Грусть"), ("Спокойствие", "de_Спокойствие"),
        ])
    )


@router.callback_query(DiaryState.emotion, F.data.startswith("de_"))
async def diary_emotion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    name = data.get("name", callback.from_user.first_name or "Клиент")
    emotion = callback.data[3:]

    storage.save_diary(
        user_id=callback.from_user.id, name=name,
        location=data["location"], sensation=data["sensation"],
        intensity=data["intensity"], emotion=emotion,
    )
    await state.set_state(None)

    summary = (
        f"✅ Записано!\n\n"
        f"📍 {data['location']} | {data['sensation']} | {data['intensity']}/10 | {emotion}\n\n"
        f"Спасибо — это помогает лучше понять себя. 💙"
    )
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Главное меню", callback_data="main_menu")
    await safe_edit(callback, summary, b.as_markup())

    # Уведомить психолога
    await callback.bot.send_message(
        ADMIN_ID,
        f"📓 Дневник ощущений\n\n"
        f"👤 {name}\n"
        f"📍 Где: {data['location']}\n"
        f"💭 Как: {data['sensation']}\n"
        f"📊 Интенсивность: {data['intensity']}/10\n"
        f"❤️ Эмоция: {emotion}"
    )
