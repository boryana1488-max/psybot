import os
BASE = os.path.join(os.path.dirname(__file__), "images")

IMAGES = {
    "welcome":      os.path.join(BASE, "welcome.jpg"),
    "main_menu":    os.path.join(BASE, "main_menu.jpg"),
    "timezone":     os.path.join(BASE, "timezone.jpg"),
    "booking":      os.path.join(BASE, "booking.jpg"),
    "sos":          os.path.join(BASE, "sos.jpg"),
    "breathing":    os.path.join(BASE, "breathing.jpg"),
    "breathing_box": os.path.join(BASE, "breathing_box.jpg"),
    "body":         os.path.join(BASE, "body.jpg"),
    "tension":      os.path.join(BASE, "tension.jpg"),
    "cold":         os.path.join(BASE, "cold.jpg"),
    "cognitive":    os.path.join(BASE, "cognitive.jpg"),
    "sensations":   os.path.join(BASE, "sensations.jpg"),
    "mood":         os.path.join(BASE, "mood.jpg"),
    "payment":      os.path.join(BASE, "payment.jpg"),
    "affirmations": os.path.join(BASE, "affirmations.jpg"),
    "ai_chat":      os.path.join(BASE, "ai_chat.jpg"),
    "courses":      os.path.join(BASE, "courses.jpg"),
    "diary":        os.path.join(BASE, "diary.jpg"),
    # Дипломы — добавляйте сколько нужно
    "diploma_1":    os.path.join(BASE, "diploma_1.jpg"),
    "diploma_2":    os.path.join(BASE, "diploma_2.jpg"),
    "diploma_3":    os.path.join(BASE, "diploma_3.jpg"),
    "diploma_4":    os.path.join(BASE, "diploma_4.jpg"),
    "diploma_5":    os.path.join(BASE, "diploma_5.jpg"),
}

def get_image(key: str):
    from aiogram.types import FSInputFile
    path = IMAGES.get(key)
    if path and os.path.exists(path):
        return FSInputFile(path)
    return None
