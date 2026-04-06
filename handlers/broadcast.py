"""
Рассылка всем клиентам от психолога.
Использование: /broadcast Текст сообщения
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import ADMIN_ID
import storage

router = Router()


@router.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def broadcast(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "📢 Напиши текст рассылки после команды.\n\n"
            "Пример:\n/broadcast Друзья, на следующей неделе у меня появились новые слоты!"
        )
        return

    text = parts[1].strip()
    users = storage.get_all_users()

    if not users:
        await message.answer("Пока нет ни одного пользователя бота.")
        return

    sent = 0
    failed = 0
    for user_id in users:
        try:
            await message.bot.send_message(user_id, f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed} (заблокировали бота)"
    )


@router.message(Command("reviews"), F.from_user.id == ADMIN_ID)
async def show_reviews(message: Message):
    all_reviews = storage.get_all_reviews()

    if not all_reviews:
        await message.answer("Отзывов пока нет.")
        return

    avg = sum(r["rating"] for r in all_reviews) / len(all_reviews)
    text = f"💬 Отзывы ({len(all_reviews)}) | Средняя оценка: {avg:.1f} ⭐\n\n"

    for r in all_reviews[-10:]:  # последние 10
        stars = "⭐" * r["rating"]
        text += f"{stars} {r['name']}\n{r['comment']}\n\n"

    await message.answer(text)
