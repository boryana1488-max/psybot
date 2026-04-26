"""Первичная анкета — запускается перед первой записью."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import storage

router = Router()


class QuestionnaireState(StatesGroup):
    goal = State()
    request = State()
    source = State()


GOALS = {
    "ru": [
        ("😰 Тревога/стресс", "qg_anxiety"),
        ("💔 Отношения", "qg_relations"),
        ("🧠 Самопознание", "qg_self"),
        ("😢 Депрессия", "qg_depression"),
        ("💼 Работа/карьера", "qg_work"),
        ("👨‍👩‍👧 Семья", "qg_family"),
        ("🌱 Личностный рост", "qg_growth"),
        ("🔹 Другое", "qg_other"),
    ],
    "uk": [
        ("😰 Тривога/стрес", "qg_anxiety"),
        ("💔 Стосунки", "qg_relations"),
        ("🧠 Самопізнання", "qg_self"),
        ("😢 Депресія", "qg_depression"),
        ("💼 Робота/кар'єра", "qg_work"),
        ("👨‍👩‍👧 Сім'я", "qg_family"),
        ("🌱 Особистісне зростання", "qg_growth"),
        ("🔹 Інше", "qg_other"),
    ],
}

SOURCES = {
    "ru": [
        ("👥 Рекомендация друга", "qs_friend"),
        ("📱 Instagram", "qs_instagram"),
        ("🔍 Google", "qs_google"),
        ("📢 Реклама", "qs_ads"),
        ("🔹 Другое", "qs_other"),
    ],
    "uk": [
        ("👥 Рекомендація друга", "qs_friend"),
        ("📱 Instagram", "qs_instagram"),
        ("🔍 Google", "qs_google"),
        ("📢 Реклама", "qs_ads"),
        ("🔹 Інше", "qs_other"),
    ],
}

# cb -> label ru/uk
GOAL_MAP = {
    "qg_anxiety": ("Тревога/стресс", "Тривога/стрес"),
    "qg_relations": ("Отношения", "Стосунки"),
    "qg_self": ("Самопознание", "Самопізнання"),
    "qg_depression": ("Депрессия", "Депресія"),
    "qg_work": ("Работа/карьера", "Робота/кар'єра"),
    "qg_family": ("Семья", "Сім'я"),
    "qg_growth": ("Личностный рост", "Особистісне зростання"),
    "qg_other": ("Другое", "Інше"),
}
SOURCE_MAP = {
    "qs_friend": ("Рекомендация друга", "Рекомендація друга"),
    "qs_instagram": ("Instagram", "Instagram"),
    "qs_google": ("Google", "Google"),
    "qs_ads": ("Реклама", "Реклама"),
    "qs_other": ("Другое", "Інше"),
}


async def safe_edit(callback, text, kb=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb)
        else:
            await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "start_questionnaire")
async def q_start(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await state.set_state(QuestionnaireState.goal)
    text = ("📋 Несколько вопросов помогут психологу лучше подготовиться к встрече.\n\n"
            "1️⃣ Что вас привело? Выберите основную тему:"
            if lang == "ru" else
            "📋 Кілька запитань допоможуть психологу краще підготуватися до зустрічі.\n\n"
            "1️⃣ Що вас привело? Оберіть основну тему:")
    kb = InlineKeyboardBuilder()
    for label, cb in GOALS[lang]:
        kb.button(text=label, callback_data=cb)
    kb.adjust(2)
    await safe_edit(callback, text, kb.as_markup())


@router.callback_query(QuestionnaireState.goal, F.data.startswith("qg_"))
async def q_goal_chosen(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    labels = GOAL_MAP.get(callback.data, ("Другое", "Інше"))
    label = labels[0] if lang == "ru" else labels[1]
    await state.update_data(q_goal=label)
    await state.set_state(QuestionnaireState.request)
    text = ("2️⃣ Коротко опишите свой запрос — что хотите изменить или проработать?\n\n"
            "(напишите текстом)"
            if lang == "ru" else
            "2️⃣ Коротко опишіть свій запит — що хочете змінити або опрацювати?\n\n"
            "(напишіть текстом)")
    await safe_edit(callback, text)


@router.message(QuestionnaireState.request)
async def q_request_entered(message: Message, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await state.update_data(q_request=message.text.strip())
    await state.set_state(QuestionnaireState.source)
    text = ("3️⃣ Как вы узнали о нас?" if lang == "ru" else "3️⃣ Як ви дізналися про нас?")
    kb = InlineKeyboardBuilder()
    for label, cb in SOURCES[lang]:
        kb.button(text=label, callback_data=cb)
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(QuestionnaireState.source, F.data.startswith("qs_"))
async def q_source_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    labels = SOURCE_MAP.get(callback.data, ("Другое", "Інше"))
    source = labels[0] if lang == "ru" else labels[1]

    await storage.save_questionnaire(
        user_id=callback.from_user.id,
        goal=data.get("q_goal", ""),
        request=data.get("q_request", ""),
        source=source,
    )
    await state.set_state(None)

    text = ("✅ Спасибо! Теперь выберите удобное время."
            if lang == "ru" else
            "✅ Дякуємо! Тепер оберіть зручний час.")
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Записаться" if lang == "ru" else "📅 Записатися", callback_data="book")
    kb.adjust(1)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=kb.as_markup())
