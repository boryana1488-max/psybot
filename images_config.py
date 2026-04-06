import os
BASE = os.path.join(os.path.dirname(__file__), "images")

IMAGES = {
    "welcome":   os.path.join(BASE, "welcome.jpg"),
    "breathing": os.path.join(BASE, "breathing.jpg"),
    "sos":       os.path.join(BASE, "sos.jpg"),
    "tension":   os.path.join(BASE, "tension.jpg"),
    "cold":      os.path.join(BASE, "cold.jpg"),
    "diary":     os.path.join(BASE, "diary.jpg"),
    "body":      os.path.join(BASE, "body.jpg"),
    "cognitive": os.path.join(BASE, "cognitive.jpg"),
    "sensations":os.path.join(BASE, "sensations.jpg"),
}

def get_image(key: str):
    from aiogram.types import FSInputFile
    path = IMAGES.get(key)
    if path and os.path.exists(path):
        return FSInputFile(path)
    return None
