import os
import json
import uuid
from pathlib import Path
import sys

CONFIG_FILENAME = "config.json"
DB_DIRNAME = "database"


def verify_dependencies() -> None:
    """
    Verify that all required dependencies are installed.
    Raises RuntimeError if any critical dependencies are missing.
    """
    missing_deps = []
    optional_missing = []
    
    # Required dependencies
    try:
        import PIL
        import PIL.Image
    except ImportError:
        missing_deps.append("Pillow (PIL)")
    
    try:
        import tkcalendar
    except ImportError:
        missing_deps.append("tkcalendar")
    
    try:
        import pycountry
    except ImportError:
        missing_deps.append("pycountry")
    
    # Check for tkinter (should be built-in but verify)
    try:
        import tkinter
    except ImportError:
        missing_deps.append("tkinter")
    
    # Optional but recommended
    try:
        import sqlite3
    except ImportError:
        optional_missing.append("sqlite3")
    
    if missing_deps:
        error_msg = "Missing required dependencies:\n" + "\n".join(f"  - {dep}" for dep in missing_deps)
        error_msg += "\n\nPlease install with: pip install -r requirements.txt"
        if optional_missing:
            error_msg += "\n\nOptional dependencies missing:\n" + "\n".join(f"  - {dep}" for dep in optional_missing)
        raise RuntimeError(error_msg)
    
    if optional_missing:
        print("Warning: Optional dependencies missing:", ", ".join(optional_missing))


def get_or_create_config(app_dir: Path) -> dict:
    config_path = app_dir / CONFIG_FILENAME
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Create new config with unique DB name
    db_dir = app_dir / DB_DIRNAME
    db_dir.mkdir(parents=True, exist_ok=True)
    db_name = f"pos_{uuid.uuid4().hex[:8]}.db"
    config = {"db_path": str(db_dir / db_name)}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    return config
