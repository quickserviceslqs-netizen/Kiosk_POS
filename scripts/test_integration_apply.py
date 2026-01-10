import sys
import tempfile
import zipfile
from pathlib import Path
import json
import shutil

sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import upgrades
from database.init_db import initialize_database


def test_integration_success():
    td = tempfile.mkdtemp()
    try:
        db_path = Path(td) / 'pos_integ.db'
        initialize_database(db_path)
        install_dir = Path(td) / 'install'
        install_dir.mkdir()

        # Use the generated sample package
        pkg = Path(__file__).parent.parent / 'tests' / 'samples' / 'sample_upgrade.zip'
        assert pkg.exists(), f"sample package not found: {pkg}"

        res = upgrades.apply_package(str(pkg), dry_run=False, backup_db=True, install_dir=str(install_dir), db_path=str(db_path))
        assert res.get('success') is True
        # Verify SQL created table by opening DB
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='t_sample'")
            assert cur.fetchone() is not None

    finally:
        try:
            shutil.rmtree(td)
        except Exception:
            pass


def test_integration_failure_rollback():
    td = tempfile.mkdtemp()
    try:
        db_path = Path(td) / 'pos_integ2.db'
        initialize_database(db_path)
        install_dir = Path(td) / 'install'
        install_dir.mkdir()

        # create failing package
        pkg = Path(td) / 'fail_upgrade.zip'
        manifest = {"version": "1.9.9", "steps": [{"type": "sql", "file": "sql/001.sql"}, {"type": "python", "file": "py/002_fail.py"}]}
        with zipfile.ZipFile(pkg, 'w') as z:
            z.writestr('upgrade.json', json.dumps(manifest))
            z.writestr('sql/001.sql', 'CREATE TABLE IF NOT EXISTS t_fail (id INTEGER PRIMARY KEY)')
            z.writestr('py/002_fail.py', 'import sys\nraise SystemExit(2)')

        res = upgrades.apply_package(str(pkg), dry_run=False, backup_db=True, install_dir=str(install_dir), db_path=str(db_path))
        assert res.get('success') is False
        assert res.get('restored') is True

        # Verify t_fail is NOT present
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='t_fail'")
            assert cur.fetchone() is None
    finally:
        try:
            shutil.rmtree(td)
        except Exception:
            pass


if __name__ == '__main__':
    test_integration_success()
    print('integration success passed')
    test_integration_failure_rollback()
    print('integration rollback passed')
