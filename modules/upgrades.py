"""Upgrade package utilities.

This module implements a minimal manifest validator and preview helper for
upgrade packages (zip files containing an `upgrade.json` manifest and
optional step files). The goal is to validate manifest correctness and
file presence inside the package. Later we'll add the full apply runner
(with backups, transactional behavior, and rollback).
"""
from __future__ import annotations

import json
import zipfile
from typing import Any, Dict, List


class UpgradeValidationError(Exception):
    pass


ALLOWED_STEP_TYPES = {"sql", "python", "copy", "command"}


def _load_manifest(z: zipfile.ZipFile) -> Dict[str, Any]:
    try:
        with z.open("upgrade.json") as fh:
            return json.load(fh)
    except KeyError:
        raise UpgradeValidationError("Package missing required 'upgrade.json' manifest")
    except json.JSONDecodeError as e:
        raise UpgradeValidationError(f"Invalid JSON in manifest: {e}")


def validate_package(path: str, *, current_app_version: str | None = None) -> Dict[str, Any]:
    """Validate an upgrade ZIP package.

    - Ensures `upgrade.json` exists and is valid JSON.
    - Ensures required top-level fields exist (version, steps).
    - Ensures each step has a valid `type` and references existing files in the ZIP.
    - Optionally checks `min_app_version` against provided current_app_version.

    Returns the parsed manifest on success.
    Raises UpgradeValidationError on validation failure.
    """
    with zipfile.ZipFile(path, "r") as z:
        manifest = _load_manifest(z)

        # Basic structure
        if "version" not in manifest:
            raise UpgradeValidationError("Manifest missing required 'version' field")
        if "steps" not in manifest or not isinstance(manifest["steps"], list):
            raise UpgradeValidationError("Manifest must contain a 'steps' list")

        # Optional min_app_version check
        if current_app_version and "min_app_version" in manifest:
            # Very small semver-ish comparator (major.minor.patch assumed)
            def _ver_to_tuple(v: str):
                return tuple(int(x) for x in v.split("."))
            try:
                if _ver_to_tuple(current_app_version) < _ver_to_tuple(str(manifest["min_app_version"])):
                    raise UpgradeValidationError(
                        f"Package requires app version {manifest['min_app_version']}+, current is {current_app_version}"
                    )
            except ValueError:
                # ignore unusual version formats
                pass

        namelist = set(z.namelist())
        for i, step in enumerate(manifest["steps"]):
            if not isinstance(step, dict):
                raise UpgradeValidationError(f"Step #{i+1} must be an object")
            stype = step.get("type")
            if stype not in ALLOWED_STEP_TYPES:
                raise UpgradeValidationError(f"Step #{i+1} has invalid type '{stype}'")

            # Steps that reference files should point to existing files in the archive
            if stype in {"sql", "python", "copy"}:
                # SQL/python use 'file'; copy may use 'src'
                key = "file" if "file" in step else ("src" if "src" in step else None)
                if not key:
                    raise UpgradeValidationError(f"Step #{i+1} of type '{stype}' must specify a file (key 'file' or 'src')")
                if step[key] not in namelist:
                    raise UpgradeValidationError(f"Step #{i+1} references missing file '{step[key]}'")

        return manifest


def preview_package(path: str) -> List[Dict[str, Any]]:
    """Return the ordered list of steps from the package manifest (validated)."""
    manifest = validate_package(path)
    return manifest.get("steps", [])


# ---- Apply runner (MVP) ----
import shutil
import tempfile
import os
import subprocess
import sys
from pathlib import Path
from database.init_db import get_default_db_path, get_connection


class UpgradeApplyError(Exception):
    pass


def _copy_over(src: Path, dest: Path, backups: List[Path]) -> None:
    """Copy src to dest (dest may be file or directory). Record overwritten files in backups."""
    dest_parent = dest.parent
    dest_parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        # backup existing file
        bk = Path(tempfile.mkdtemp()) / (dest.name + ".bak")
        shutil.copy2(dest, bk)
        backups.append(bk)
    shutil.copy2(src, dest)


def apply_package(path: str, *, dry_run: bool = False, backup_db: bool = True, install_dir: str | None = None, db_path: str | None = None) -> Dict[str, Any]:
    """Apply an upgrade package.

    Steps:
    - validate package
    - extract to temp
    - optionally backup DB
    - run steps in order (sql -> python -> copy -> command)
    - on error, attempt DB restore and report error + logs

    Returns dict with summary and logs.
    """
    summary: Dict[str, Any] = {"success": False, "logs": [], "restored": False}
    tmpdir = Path(tempfile.mkdtemp(prefix="upgrade_"))
    backups: List[Path] = []
    install_dir = Path(install_dir) if install_dir else Path.cwd()

    try:
        manifest = validate_package(path)
        summary["manifest"] = {"version": manifest.get("version"), "description": manifest.get("description")}
        if dry_run:
            summary["logs"].append("DRY RUN: validation passed")
            summary["success"] = True
            return summary

        # Extract package
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(tmpdir)

        # Determine DB path and backup
        db_path = Path(db_path) if db_path else get_default_db_path()
        summary["logs"].append(f"Using DB path: {db_path}")
        if backup_db:
            bk = Path(tempfile.mkdtemp()) / (db_path.name + ".bak")
            shutil.copy2(db_path, bk)
            summary["logs"].append(f"Database backed up to {bk}")
            db_backup = bk
        else:
            db_backup = None

        # Execute steps
        conn = get_connection(db_path)
        try:
            conn.row_factory = __import__("sqlite3").Row
            for i, step in enumerate(manifest.get("steps", [])):
                stype = step.get("type")
                summary["logs"].append(f"Starting step #{i+1}: type={stype}")
                if stype == "sql":
                    sf = tmpdir / step.get("file")
                    sql_text = sf.read_text(encoding="utf-8")
                    try:
                        conn.executescript(sql_text)
                        summary["logs"].append(f"Applied SQL: {step.get('file')}")
                        # Basic verification: check if the SQL created any tables mentioned in the script
                        try:
                            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            names = [r[0] for r in cur.fetchall()]
                            summary["logs"].append(f"Current tables after SQL: {names}")
                        except Exception as e:
                            summary["logs"].append(f"DB introspect failed: {e}")
                    except Exception as e:
                        raise UpgradeApplyError(f"SQL step failed: {e}")
                elif stype == "python":

                    pf = tmpdir / step.get("file")
                    # Run python script in subprocess for isolation
                    try:
                        res = subprocess.run([sys.executable, str(pf)], cwd=str(tmpdir), capture_output=True, text=True, check=True)
                        summary["logs"].append(f"Python step stdout: {res.stdout}")
                        if res.stderr:
                            summary["logs"].append(f"Python step stderr: {res.stderr}")
                    except subprocess.CalledProcessError as e:
                        raise UpgradeApplyError(f"Python step failed: {e.stderr or e}")
                elif stype == "copy":
                    src = tmpdir / step.get("src")
                    dest = install_dir / (step.get("dest") or step.get("src"))
                    # Support copying a file or a directory
                    if src.is_dir():
                        # copytree into destination; if exists, copy contents
                        for item in src.rglob("*"):
                            rel = item.relative_to(src)
                            target = dest / rel
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if item.is_file():
                                _copy_over(item, target, backups)
                        summary["logs"].append(f"Copied directory {step.get('src')} -> {dest}")
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        _copy_over(src, dest, backups)
                        summary["logs"].append(f"Copied file {step.get('src')} -> {dest}")
                elif stype == "command":
                    cmd = step.get("cmd")
                    if not cmd:
                        raise UpgradeApplyError("Command step missing 'cmd' element")
                    res = subprocess.run(cmd, shell=True, cwd=str(tmpdir), capture_output=True, text=True)
                    summary["logs"].append(f"Command exit {res.returncode}; out={res.stdout}; err={res.stderr}")
                    if res.returncode != 0:
                        raise UpgradeApplyError(f"Command failed with exit {res.returncode}")
                else:
                    raise UpgradeApplyError(f"Unhandled step type: {stype}")
            try:
                conn.commit()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

        summary["success"] = True
        summary["logs"].append("Upgrade applied successfully")
        return summary

    except Exception as exc:
        summary["logs"].append(f"Upgrade failed: {exc}")
        # Attempt DB restore if backed up
        try:
            if 'db_backup' in locals() and db_backup and db_backup.exists():
                shutil.copy2(db_backup, db_path)
                summary["logs"].append("Database restored from backup")
                summary["restored"] = True
        except Exception as e:
            summary["logs"].append(f"Failed to restore DB backup: {e}")
        summary["success"] = False
        return summary

    finally:
        # Cleanup tempdir
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


