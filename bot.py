import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import client, admin, sos, practices
from handlers import cancel, review, broadcast, mood
from handlers.reminder import reminder_loop

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(sos.router)
    dp.include_router(practices.router)
    dp.include_router(cancel.router)
    dp.include_router(review.router)
    dp.include_router(broadcast.router)
    dp.include_router(mood.router)
    dp.include_router(admin.router)
    dp.include_router(client.router)

    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем напоминания в фоне
    asyncio.create_task(reminder_loop(bot))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
