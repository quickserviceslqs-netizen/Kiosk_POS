import os
import json
import uuid
from pathlib import Path

CONFIG_FILENAME = "config.json"
DB_DIRNAME = "database"


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
