import os
BASE = os.path.join(os.path.dirname(__file__), "images")

IMAGES = {
    "welcome":      os.path.join(BASE, "welcome.jpg"),
    "timezone":     os.path.join(BASE, "timezone.jpg"),
    "booking":      os.path.join(BASE, "booking.jpg"),
    "sos":          os.path.join(BASE, "sos.jpg"),
    "breathing":    os.path.join(BASE, "breathing.jpg"),
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
}

def get_image(key: str):
    from aiogram.types import FSInputFile
    path = IMAGES.get(key)
    if path and os.path.exists(path):
        return FSInputFile(path)
    return None
