"""Оплата консультации и курсов."""
import uuid
import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot
from config import ADMIN_ID, PAYMENT_CARD, PAYMENT_RECIPIENT, CONSULTATION_PRICE, COURSE_PRICE
from images_config import get_image
import storage

router = Router()

COURSES = {
    "course_vzroslenie": {
        "name_ru": "🌱 Курс «Взросление»",
        "name_uk": "🌱 Курс «Дорослішання»",
        "desc_ru": (
            "*Бодинамический Курс Лилии Копейченко*\n\n"
            "С внутриутробного развития до 12 лет происходит фундаментальное "
            "формирование характера и структуры личности человека.\n"
            "И как известно — этот период у всех не идеален, что влияет на качество "
            "отношений, жизни и здоровья.\n\n"
            "✨ *У вас есть уникальная возможность исправить это!*\n\n"
            "Человеческое тело и психика обладают уникальными способностями к "
            "оздоровлению и восстановлению!\n\n"
            "Программа *«Взросление»* основана на самых современных психологических "
            "и физиологических исследованиях человека. Программа позволяет "
            "«перепрошить», «перепрограммировать» психологические и физические "
            "процессы на здоровый лад, раскрыть потенциал вашей личности.\n\n"
            "📚 *Что вас ждёт:*\n"
            "• 80 уроков по 50 минут\n"
            "• Телесные практики, похожие на йогу\n"
            "• Опора на психомоторное развитие человека\n"
            "• Просты, доступны и легки в освоении\n"
            "• Нет противопоказаний (кроме острых форм заболеваний, "
            "послеоперационного периода и беременности)\n\n"
            "🧠 *Результат за 9 месяцев* (2 раза в неделю):\n"
            "Вы закрепите здоровые паттерны на нейронном уровне головного мозга, "
            "что позволит оздоровить ваши гены и передать более здоровое генетическое "
            "наследие своим детям.\n\n"
            "💡 Это короткий, надёжный, научно подтверждённый и очень экономичный "
            "способ личной психотерапии и трансформации."
        ),
        "desc_uk": (
            "*Бодинамічний Курс Лілії Копейченко*\n\n"
            "З внутрішньоутробного розвитку до 12 років відбувається фундаментальне "
            "формування характеру та структури особистості людини.\n"
            "І як відомо — цей період у всіх не ідеальний, що впливає на якість "
            "стосунків, життя та здоров'я.\n\n"
            "✨ *У вас є унікальна можливість виправити це!*\n\n"
            "Людське тіло і психіка мають унікальні здібності до оздоровлення "
            "та відновлення!\n\n"
            "Програма *«Дорослішання»* заснована на найсучасніших психологічних "
            "та фізіологічних дослідженнях людини. Програма дозволяє «перепрошити», "
            "«перепрограмувати» психологічні та фізичні процеси на здоровий лад, "
            "розкрити потенціал вашої особистості.\n\n"
            "📚 *Що на вас чекає:*\n"
            "• 80 уроків по 50 хвилин\n"
            "• Тілесні практики, схожі на йогу\n"
            "• Опора на психомоторний розвиток людини\n"
            "• Прості, доступні й легкі у засвоєнні\n"
            "• Немає протипоказань (крім гострих форм захворювань, "
            "післяопераційного періоду та вагітності)\n\n"
            "🧠 *Результат за 9 місяців* (2 рази на тиждень):\n"
            "Ви закріпите здорові патерни на нейронному рівні головного мозку, "
            "що дозволить оздоровити ваші гени та передати більш здорове генетичне "
            "спадщину своїм дітям.\n\n"
            "💡 Це короткий, надійний, науково підтверджений та дуже економічний "
            "спосіб особистої психотерапії та трансформації."
        ),
        "price": COURSE_PRICE,
    }
}


class PaymentState(StatesGroup):
    waiting_receipt = State()


COURSE_CARD = "4149 6293 5967 9438"
COURSE_RECIPIENT = "Лілія Копейченко"

def payment_text(lang: str, price: int, tx_id: str, item: str, is_course: bool = False) -> str:
    card = COURSE_CARD if is_course else PAYMENT_CARD
    recipient = COURSE_RECIPIENT if is_course else PAYMENT_RECIPIENT
    if lang == "ru":
        return (
            "💳 Реквизиты для оплаты\n\n"
            "💳 Карта: " + card + "\n"
            "👤 Получатель: " + recipient + "\n"
            "💰 Сумма: " + str(price) + " UAH\n"
            "📋 За: " + item + "\n"
            "🔖 TX ID: #" + tx_id + "\n\n"
            "После оплаты нажмите «Оплатил» и отправьте фото или PDF квитанции."
        )
    else:
        return (
            "💳 Реквізити для оплати\n\n"
            "💳 Картка: " + card + "\n"
            "👤 Отримувач: " + recipient + "\n"
            "💰 Сума: " + str(price) + " UAH\n"
            "📋 За: " + item + "\n"
            "🔖 TX ID: #" + tx_id + "\n\n"
            "Після оплати натисніть «Оплатив» і надішліть фото або PDF квитанції."
        )


def paid_kb(lang: str, tx_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Оплатил/Оплатила" if lang == "ru" else "✅ Оплатив/Оплатила",
        callback_data="paid_" + tx_id
    )
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


async def safe_edit(callback, text, kb=None, parse_mode=None):
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=kb)
        else:
            await callback.message.edit_text(text, parse_mode=parse_mode, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode=parse_mode, reply_markup=kb)


@router.callback_query(F.data == "pay_consultation")
async def pay_consultation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    tx_id = str(uuid.uuid4())[:8].upper()
    await state.update_data(tx_id=tx_id, tx_type="consultation", tx_price=CONSULTATION_PRICE)
    item = "Консультация психолога" if lang == "ru" else "Консультація психолога"
    await safe_edit(callback, payment_text(lang, CONSULTATION_PRICE, tx_id, item),
                    paid_kb(lang, tx_id))


@router.callback_query(F.data == "courses")
async def courses_menu(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    kb = InlineKeyboardBuilder()
    for key, c in COURSES.items():
        name = c["name_ru"] if lang == "ru" else c["name_uk"]
        kb.button(text=name, callback_data="course_" + key)
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    title = "📚 Курсы" if lang == "ru" else "📚 Курси"
    await safe_edit(callback, title, kb.as_markup())


@router.callback_query(F.data.startswith("course_course_"))
async def course_detail(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    key = callback.data.replace("course_", "", 1)
    course = COURSES.get(key)
    if not course:
        await callback.answer("Курс не найден.", show_alert=True)
        return
    name = course["name_ru"] if lang == "ru" else course["name_uk"]
    desc = course["desc_ru"] if lang == "ru" else course["desc_uk"]
    price = course["price"]
    kb = InlineKeyboardBuilder()
    kb.button(
        text=("💳 Оплатить " if lang == "ru" else "💳 Оплатити ") + str(price) + " UAH",
        callback_data="pay_course_" + key
    )
    kb.button(text="◀️ Назад", callback_data="courses")
    kb.adjust(1)
    text = name + "\n\n" + desc + "\n\n" + ("💰 Стоимость: " if lang == "ru" else "💰 Вартість: ") + str(price) + " UAH"
    photo = get_image("courses")
    if photo:
        try:
            await callback.message.answer_photo(
                photo=photo, caption=text[:1024],
                parse_mode="Markdown", reply_markup=kb.as_markup()
            )
            await callback.message.delete()
            return
        except Exception:
            pass
    # Если текст длинный — отправляем без Markdown
    try:
        await safe_edit(callback, text, kb.as_markup(), parse_mode="Markdown")
    except Exception:
        import re
        plain = re.sub(r'[*_`]', '', text)
        await safe_edit(callback, plain, kb.as_markup(), parse_mode=None)


@router.callback_query(F.data.startswith("pay_course_"))
async def pay_course(callback: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    key = callback.data.replace("pay_course_", "")
    course = COURSES.get(key)
    if not course:
        await callback.answer("Курс не найден.", show_alert=True)
        return
    tx_id = str(uuid.uuid4())[:8].upper()
    name = course["name_ru"] if lang == "ru" else course["name_uk"]
    await state.update_data(tx_id=tx_id, tx_type=key, tx_price=course["price"])
    await safe_edit(callback, payment_text(lang, course["price"], tx_id, name, is_course=True),
                    paid_kb(lang, tx_id))


@router.callback_query(F.data.startswith("paid_"))
async def paid_pressed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    tx_id = callback.data.replace("paid_", "")
    await state.update_data(tx_id=tx_id)
    await state.set_state(PaymentState.waiting_receipt)
    text = (
        "📎 Отправьте фото или PDF квитанции об оплате."
        if lang == "ru" else
        "📎 Надішліть фото або PDF квитанції про оплату."
    )
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

    # Логируем платёж
    await storage.log_payment(
        user_id=message.from_user.id,
        name=name,
        tx_id=tx_id,
        amount=int(tx_price) if str(tx_price).isdigit() else 0,
        purpose=tx_type
    )

    text = (
        "✅ Спасибо! Квитанция получена.\n\n"
        "🔖 TX ID: #" + tx_id + "\n\n"
        "Психолог проверит оплату и подтвердит запись."
        if lang == "ru" else
        "✅ Дякуємо! Квитанцію отримано.\n\n"
        "🔖 TX ID: #" + tx_id + "\n\n"
        "Психолог перевірить оплату і підтвердить запис."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Меню", callback_data="main_menu")
    await message.answer(text, reply_markup=kb.as_markup())

    admin_text = (
        "💳 Новая оплата!\n\n"
        "👤 " + name + "\n"
        "🆔 " + str(message.from_user.id) + "\n"
        "🔖 TX ID: #" + tx_id + "\n"
        "💰 " + str(tx_price) + " UAH\n"
        "📋 " + tx_type
    )
    confirm_kb = InlineKeyboardBuilder()
    confirm_kb.button(text="✅ Подтвердить оплату", callback_data="confirm_pay_" + tx_id)
    confirm_kb.adjust(1)
    await message.bot.send_message(ADMIN_ID, admin_text, reply_markup=confirm_kb.as_markup())
    if message.photo:
        await message.bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                                     caption="🧾 Квитанция #" + tx_id)
    elif message.document:
        await message.bot.send_document(ADMIN_ID, message.document.file_id,
                                        caption="🧾 Квитанция #" + tx_id)


@router.message(PaymentState.waiting_receipt)
async def receipt_wrong(message: Message, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await message.answer(
        "Пожалуйста, отправьте фото или PDF файл."
        if lang == "ru" else
        "Будь ласка, надішліть фото або PDF файл."
    )


@router.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_payment(callback: CallbackQuery):
    from config import ADMIN_ID as _ADMIN
    if callback.from_user.id != _ADMIN:
        return
    tx_id = callback.data.replace("confirm_pay_", "")
    await storage.confirm_payment_by_tx(tx_id)
    await callback.answer("✅ Оплата подтверждена!")
    await callback.message.edit_reply_markup(reply_markup=None)
    # Уведомляем клиента
    log = await storage.get_payment_log()
    for p in log:
        if p["tx_id"] == tx_id:
            try:
                await callback.bot.send_message(
                    p["user_id"],
                    "✅ Ваша оплата #" + tx_id + " подтверждена психологом. До встречи! 💙"
                )
            except Exception:
                pass
            break


async def payment_reminder_loop(bot: Bot):
    """За 12 часов до сессии напоминает об оплате."""
    import re
    from datetime import datetime, timedelta, date
    notified: set = set()
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        for b in await storage.get_unpay_reminded_bookings():
            if b.get("paid"):
                await storage.mark_pay_reminded(b)
                continue
            slot_date = b.get("slot_date")
            if not slot_date:
                continue
            match = re.search(r"(\d+):(\d+)", b.get("slot", ""))
            if not match:
                continue
            h, m = int(match.group(1)), int(match.group(2))
            if isinstance(slot_date, date):
                dt = datetime(slot_date.year, slot_date.month, slot_date.day, h, m)
                diff = (dt - now).total_seconds() / 3600
                if 11.5 <= diff <= 12.5:
                    lang = b.get("lang", "ru")
                    kb = InlineKeyboardBuilder()
                    kb.button(
                        text="💳 Оплатить" if lang == "ru" else "💳 Оплатити",
                        callback_data="pay_consultation"
                    )
                    text = (
                        "💳 Напоминание об оплате\n\nВаша консультация завтра: " + b["slot"]
                        if lang == "ru" else
                        "💳 Нагадування про оплату\n\nВаша консультація завтра: " + b["slot"]
                    )
                    try:
                        await bot.send_message(b["user_id"], text, reply_markup=kb.as_markup())
                        await storage.mark_pay_reminded(b)
                    except Exception:
                        pass
