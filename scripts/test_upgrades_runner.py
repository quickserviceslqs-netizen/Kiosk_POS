import sys
import tempfile
import zipfile
from pathlib import Path
import json
import shutil
import gc
import time

sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import upgrades
from database.init_db import initialize_database, get_default_db_path
import sqlite3

# Prepare a temporary DB path for safe testing
td = tempfile.mkdtemp()
try:
    db_path = Path(td) / 'pos_test.db'
    resolved_db = initialize_database(db_path)
    print('initialize_database returned', resolved_db)
    db_path = resolved_db
    # Ensure DB file exists by touching it (some environments may delay create)
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
    except Exception as e:
        print('Failed to ensure db exists:', e)

    # Create package: one SQL step that creates table t_upgrade
    pkg = Path(td) / 'upgrade_pkg.zip'
    manifest = {
        "version": "1.1.0",
        "steps": [
            {"type": "sql", "file": "sql/001_create_table.sql"}
        ]
    }
    with zipfile.ZipFile(pkg, 'w') as z:
        z.writestr('upgrade.json', json.dumps(manifest))
        z.writestr('sql/001_create_table.sql', 'CREATE TABLE IF NOT EXISTS t_upgrade (id INTEGER PRIMARY KEY, name TEXT);')

    # Apply package pointing to this DB (monkeypatch get_default_db_path by environment)
    # Temporarily override DB_PATH by setting environment variable is not available, so we pass install_dir but function uses get_default_db_path()
    # Verify db file exists before apply
    print('Test db exists?', db_path.exists(), db_path)
    # Apply - should succeed (specify db_path to avoid touching default DB)
    res = upgrades.apply_package(str(pkg), dry_run=False, backup_db=True, install_dir=str(Path(td)/"install"), db_path=str(db_path))
    print('Apply result success:', res['success'])
    print('Summary:', res)
    print('Logs:', '\n'.join(res.get('logs', [])))
    assert res['success'] is True

    # Check that the SQL step was applied (verify via logs produced during apply)
    assert any('t_upgrade' in s for s in res.get('logs', []))

    # Now create a failing package (python step that errors) and ensure rollback
    pkg2 = Path(td) / 'upgrade_pkg_fail.zip'
    manifest2 = {
        "version": "1.1.1",
        "steps": [
            {"type": "sql", "file": "sql/001_create_table.sql"},
            {"type": "python", "file": "py/002_fail.py"}
        ]
    }
    with zipfile.ZipFile(pkg2, 'w') as z:
        z.writestr('upgrade.json', json.dumps(manifest2))
        z.writestr('sql/001_create_table.sql', 'CREATE TABLE IF NOT EXISTS t_upgrade2 (id INTEGER PRIMARY KEY, name TEXT);')
        z.writestr('py/002_fail.py', 'import sys\nraise SystemExit(2)')

    res2 = upgrades.apply_package(str(pkg2), dry_run=False, backup_db=True, install_dir=str(Path(td)/"install"), db_path=str(db_path))
    print('Apply fail result success:', res2['success'], 'restored:', res2.get('restored'))
    assert res2['success'] is False
    assert res2.get('restored') is True

finally:
    # Robust cleanup: ensure objects are finalized and retry removal to avoid transient Windows file-locks
    gc.collect()
    time.sleep(0.25)
    try:
        shutil.rmtree(td)
    except Exception as e:
        print('cleanup warning (ignored):', e)

print('test_upgrades_runner completed')
