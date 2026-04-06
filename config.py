import os

# Токен бота от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "8762200697:AAHdysGbNPumEDmltjPHdPZvYDBYlys3V1E")

# Telegram ID жены (админа) — узнать можно через @userinfobot
# ВАЖНО: читаем как int, иначе фильтр не сработает
_admin_raw = os.getenv("ADMIN_ID", "8507430605")
ADMIN_ID = int(_admin_raw.strip())

# Доступные слоты для записи (можно редактировать)
SLOTS = [
    "Понедельник 10:00",
    "Понедельник 14:00",
    "Вторник 11:00",
    "Вторник 16:00",
    "Среда 10:00",
    "Среда 15:00",
    "Четверг 12:00",
    "Пятница 10:00",
    "Пятница 13:00",
]
