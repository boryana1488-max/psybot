import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import (admin, client, sos, practices, cancel, broadcast,
                      review, mood, diary, checkin, payment,
                      questionnaire, affirmations, ai_chat)
from handlers.reminder import reminder_loop, slot_refresh_loop
from handlers.checkin import checkin_loop
from storage import init_db

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(ai_chat.router)
    dp.include_router(questionnaire.router)
    dp.include_router(affirmations.router)
    dp.include_router(sos.router)
    dp.include_router(diary.router)
    dp.include_router(practices.router)
    dp.include_router(cancel.router)
    dp.include_router(review.router)
    dp.include_router(mood.router)
    dp.include_router(checkin.router)
    dp.include_router(broadcast.router)
    dp.include_router(payment.router)
    dp.include_router(client.router)

    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(reminder_loop(bot))
    asyncio.create_task(slot_refresh_loop(bot))
    asyncio.create_task(checkin_loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
