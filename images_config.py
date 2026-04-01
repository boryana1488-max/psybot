"""
Пути к картинкам. Если файл не найден — бот просто отправит текст без фото.
"""
import os

BASE = os.path.join(os.path.dirname(__file__), "images")

IMAGES = {
    "welcome":    os.path.join(BASE, "welcome.jpg"),
    "breathing":  os.path.join(BASE, "breathing.jpg"),
    "sos":        os.path.join(BASE, "sos.jpg"),
}


def get_image(key: str):
    """Возвращает FSInputFile если файл существует, иначе None."""
    from aiogram.types import FSInputFile
    path = IMAGES.get(key)
    if path and os.path.exists(path):
        return FSInputFile(path)
    return None
