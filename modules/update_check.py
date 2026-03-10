"""Automatic update check for Kiosk POS.

Fetches a JSON manifest from a configurable URL and compares the published
version against the running version.  Runs entirely in a daemon thread so it
never blocks the UI.

Expected JSON manifest format served at the update-check URL:
{
  "version":      "1.005",
  "download_url": "https://example.com/kiosk_pos_v1.005.zip",
  "description":  "Bug fixes and new reports",
  "release_date": "2026-03-07",
  "release_notes": "- Fixed X\n- Added Y"
}

Settings keys (stored in the DB settings table):
  update_check_url       – URL to fetch the manifest from (empty = disabled)
  update_check_auto      – "1" or "0" (default "1") — run check on login
"""
from __future__ import annotations

import json
import threading
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# ── Version helpers ──────────────────────────────────────────────────────────

def _version_parts(v: str) -> list[int]:
    return [int(x) for x in v.split(".") if x.isdigit()]


def version_gt(v1: str, v2: str) -> bool:
    """Return True if v1 is strictly greater than v2."""
    p1, p2 = _version_parts(v1), _version_parts(v2)
    n = max(len(p1), len(p2))
    p1 += [0] * (n - len(p1))
    p2 += [0] * (n - len(p2))
    return p1 > p2


# ── Public API ───────────────────────────────────────────────────────────────

def get_update_check_url() -> str:
    """Return the configured update-check URL, or empty string if not set."""
    try:
        from database.init_db import get_setting
        return (get_setting("update_check_url") or "").strip()
    except Exception:
        return ""


def set_update_check_url(url: str) -> None:
    """Persist the update-check URL to the database settings."""
    try:
        from database.init_db import set_setting
        set_setting("update_check_url", url.strip())
    except Exception as e:
        logger.warning(f"Could not save update_check_url: {e}")


def get_auto_check_enabled() -> bool:
    """Return whether automatic update checking on login is enabled."""
    try:
        from database.init_db import get_setting
        v = get_setting("update_check_auto")
        return (v or "1") != "0"
    except Exception:
        return True


def set_auto_check_enabled(enabled: bool) -> None:
    """Persist the auto-check preference."""
    try:
        from database.init_db import set_setting
        set_setting("update_check_auto", "1" if enabled else "0")
    except Exception as e:
        logger.warning(f"Could not save update_check_auto: {e}")


def check_for_updates(
    current_version: str,
    check_url: str,
    callback: Callable[[Optional[Dict[str, Any]]], None],
    *,
    timeout: int = 10,
) -> None:
    """Fetch the update manifest and call *callback* with the result.

    Runs in a background daemon thread.

    Args:
        current_version: The running app version string (e.g. "1.004").
        check_url:        Full URL to the manifest JSON file.
        callback:         Called on the background thread with either a dict
                          (update available) or None (up-to-date / error).
        timeout:          HTTP request timeout in seconds.
    """
    if not check_url:
        callback(None)
        return

    def _worker() -> None:
        try:
            import urllib.request
            req = urllib.request.Request(
                check_url,
                headers={"User-Agent": f"KioskPOS/{current_version}"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data: Dict[str, Any] = json.loads(raw)

            available = str(data.get("version", "")).strip()
            if available and version_gt(available, current_version):
                logger.info(f"Update available: {available} (current {current_version})")
                callback(data)
            else:
                logger.debug(f"App is up-to-date (latest={available}, current={current_version})")
                callback(None)

        except Exception as exc:
            logger.debug(f"Update check failed ({check_url}): {exc}")
            callback(None)

    threading.Thread(target=_worker, daemon=True, name="update-check").start()


def run_startup_check(
    current_version: str,
    callback: Callable[[Optional[Dict[str, Any]]], None],
) -> None:
    """Convenience wrapper used on login: reads URL + auto flag from DB then checks.

    Only fires if auto-check is enabled and a URL is configured.
    """
    if not get_auto_check_enabled():
        return
    url = get_update_check_url()
    if not url:
        return
    check_for_updates(current_version, url, callback)
