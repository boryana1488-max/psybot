import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH, WEBHOOK_URL
from handlers import admin, client, sos, practices
from handlers import cancel, review, broadcast, mood, diary, checkin, payment
from handlers.reminder import reminder_loop, slot_refresh_loop
from handlers.checkin import checkin_loop
from handlers.payment import payment_reminder_loop
from storage import init_db

logging.basicConfig(level=logging.INFO)


async def on_startup(bot: Bot):
    await init_db()
    if WEBHOOK_HOST:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set: {WEBHOOK_URL}")
    else:
        logging.info("No WEBHOOK_HOST — running in polling mode")


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(sos.router)
    dp.include_router(payment.router)
    dp.include_router(diary.router)
    dp.include_router(checkin.router)
    dp.include_router(practices.router)
    dp.include_router(cancel.router)
    dp.include_router(review.router)
    dp.include_router(broadcast.router)
    dp.include_router(mood.router)
    dp.include_router(client.router)

    await on_startup(bot)

    # Фоновые задачи
    loop = asyncio.get_event_loop()
    loop.create_task(reminder_loop(bot))
    loop.create_task(slot_refresh_loop(bot))
    loop.create_task(checkin_loop(bot))
    loop.create_task(payment_reminder_loop(bot))

    if WEBHOOK_HOST:
        # Webhook режим
        app = web.Application()
        handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        logging.info("Webhook server started on :8080")
        await asyncio.Event().wait()  # держим процесс
    else:
        # Polling режим (для локальной разработки)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
