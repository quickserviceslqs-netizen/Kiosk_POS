"""Database backup and restore functionality."""
from __future__ import annotations

import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from database.init_db import DB_PATH


CONFIG_FILE = Path(__file__).parent.parent / "backup_config.json"


def get_backup_config() -> dict:
    """Load backup configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "auto_backup_enabled": False,
        "backup_interval_hours": 24,
        "last_auto_backup": None,
        "max_backups_to_keep": 10
    }


def save_backup_config(config: dict) -> None:
    """Save backup configuration."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_backup_dir() -> Path:
    """Get or create the backups directory."""
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def create_backup(custom_name: Optional[str] = None) -> Path:
    """
    Create a backup of the database.
    
    Args:
        custom_name: Optional custom name for the backup. If not provided,
                    uses timestamp format: pos_backup_YYYYMMDD_HHMMSS.db
    
    Returns:
        Path to the created backup file
    
    Raises:
        FileNotFoundError: If the database file doesn't exist
        PermissionError: If unable to write to backup directory
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    
    backup_dir = get_backup_dir()
    
    if custom_name:
        backup_name = custom_name if custom_name.endswith('.db') else f"{custom_name}.db"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"pos_backup_{timestamp}.db"
    
    backup_path = backup_dir / backup_name
    
    # Copy database file
    shutil.copy2(DB_PATH, backup_path)
    
    return backup_path


def restore_backup(backup_path: Path | str) -> None:
    """
    Restore database from a backup file.
    
    Args:
        backup_path: Path to the backup file to restore
    
    Raises:
        FileNotFoundError: If the backup file doesn't exist
        PermissionError: If unable to write to database location
    """
    backup_path = Path(backup_path)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    # Create a safety backup of current database before restoring
    if DB_PATH.exists():
        backup_dir = get_backup_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safety_backup = backup_dir / f"SAFETY_pre_restore_{timestamp}.db"
        shutil.copy2(DB_PATH, safety_backup)
    
    # Restore the backup
    shutil.copy2(backup_path, DB_PATH)


def list_backups() -> list[dict]:
    """
    List all available backups.
    
    Returns:
        List of dicts with backup info: name, path, size, created_date
    """
    backup_dir = get_backup_dir()
    backups = []
    
    for backup_file in sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = backup_file.stat()
        backups.append({
            "name": backup_file.name,
            "path": backup_file,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return backups


def delete_backup(backup_path: Path | str) -> None:
    """
    Delete a backup file.
    
    Args:
        backup_path: Path to the backup file to delete
    
    Raises:
        FileNotFoundError: If the backup file doesn't exist
    """
    backup_path = Path(backup_path)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    backup_path.unlink()


def get_backup_size_mb(backup_path: Path | str) -> float:
    """Get size of backup file in MB."""
    return Path(backup_path).stat().st_size / (1024 * 1024)


def check_and_run_auto_backup() -> Optional[Path]:
    """
    Check if auto backup should run and execute if needed.
    
    Returns:
        Path to created backup if one was made, None otherwise
    """
    config = get_backup_config()
    
    if not config["auto_backup_enabled"]:
        return None
    
    last_backup = config.get("last_auto_backup")
    interval_hours = config.get("backup_interval_hours", 24)
    
    # Check if enough time has passed
    should_backup = False
    if last_backup is None:
        should_backup = True
    else:
        last_backup_time = datetime.fromisoformat(last_backup)
        next_backup_time = last_backup_time + timedelta(hours=interval_hours)
        should_backup = datetime.now() >= next_backup_time
    
    if should_backup:
        # Create auto backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = create_backup(f"AUTO_{timestamp}")
        
        # Update last backup time
        config["last_auto_backup"] = datetime.now().isoformat()
        save_backup_config(config)
        
        # Clean up old backups
        _cleanup_old_auto_backups(config.get("max_backups_to_keep", 10))
        
        return backup_path
    
    return None


def _cleanup_old_auto_backups(max_to_keep: int) -> None:
    """Remove old AUTO backups beyond the max limit."""
    backup_dir = get_backup_dir()
    auto_backups = sorted(
        [f for f in backup_dir.glob("AUTO_*.db")],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Delete backups beyond the limit
    for old_backup in auto_backups[max_to_keep:]:
        old_backup.unlink()

