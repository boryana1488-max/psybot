import os
BASE = os.path.join(os.path.dirname(__file__), "images")

IMAGES = {
    "welcome":      os.path.join(BASE, "welcome.jpg"),
    "breathing":    os.path.join(BASE, "breathing.jpg"),
    "breathing_box":os.path.join(BASE, "breathing_box.jpg"),  # квадратное дыхание
    "sos":          os.path.join(BASE, "sos.jpg"),
    "tension":      os.path.join(BASE, "tension.jpg"),
    "cold":         os.path.join(BASE, "cold.jpg"),
    "diary":        os.path.join(BASE, "diary.jpg"),
    "body":         os.path.join(BASE, "body.jpg"),
    "cognitive":    os.path.join(BASE, "cognitive.jpg"),   # "ну и что?"
    "sensations":   os.path.join(BASE, "sensations.jpg"),
    "timezone":     os.path.join(BASE, "timezone.jpg"),    # выбор часового пояса
    "booking":      os.path.join(BASE, "booking.jpg"),     # выбор даты/слота
    "mood":         os.path.join(BASE, "mood.jpg"),        # моё настроение
    "payment":      os.path.join(BASE, "payment.jpg"),     # оплата
}

def get_image(key: str):
    from aiogram.types import FSInputFile
    path = IMAGES.get(key)
    if path and os.path.exists(path):
        return FSInputFile(path)
    return None
