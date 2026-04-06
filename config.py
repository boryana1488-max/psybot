import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8762200697:AAHdysGbNPumEDmltjPHdPZvYDBYlys3V1E")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://start-production-d65b.up.railway.app")  # https://your-app.railway.app
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

_admin_raw = os.getenv("ADMIN_ID", "388585287")
ADMIN_ID = int(_admin_raw.strip())

# Шаблоны слотов — только время и день недели (без конкретной даты)
SLOT_TEMPLATES = [
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

PAYMENT_CARD = "4441 1110 4879 8072"
PAYMENT_RECIPIENT = "Мозер Александра"
CONSULTATION_PRICE = 999
COURSE_PRICE = 3000
