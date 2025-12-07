"""Image handling helpers using Pillow."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

THUMB_SIZE = (96, 96)


def load_thumbnail(path: str | Path, size: tuple[int, int] = THUMB_SIZE) -> Optional[ImageTk.PhotoImage]:
    """Load and resize an image to a PhotoImage thumbnail; returns None on failure."""
    try:
        img = Image.open(Path(path)).convert("RGBA")
        img.thumbnail(size)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def validate_image_path(path: str | Path) -> bool:
    try:
        p = Path(path)
        return p.exists() and p.is_file()
    except Exception:
        return False
