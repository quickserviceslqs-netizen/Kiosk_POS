import sys
import tempfile
import zipfile
from pathlib import Path
import json
from io import StringIO
import contextlib
import shutil

sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from scripts import apply_upgrade
from database.init_db import initialize_database


def test_cli_dry_run():
    td = tempfile.mkdtemp()
    try:
        db_path = Path(td) / 'pos_test.db'
        initialize_database(db_path)

        pkg = Path(td) / 'upgrade_cli.zip'
        manifest = {"version": "1.2.0", "steps": [{"type": "sql", "file": "sql/001.sql"}]}
        with zipfile.ZipFile(pkg, 'w') as z:
            z.writestr('upgrade.json', json.dumps(manifest))
            z.writestr('sql/001.sql', 'CREATE TABLE IF NOT EXISTS t_cli (id INTEGER PRIMARY KEY)')

        out = StringIO()
        with contextlib.redirect_stdout(out):
            code = apply_upgrade.main([str(pkg), '--dry-run', '--db-path', str(db_path)])
        output = out.getvalue()
        assert code == 0
        assert 'DRY RUN: validation passed' in output or 'Manifest version' in output
    finally:
        try:
            shutil.rmtree(td)
        except Exception:
            pass


if __name__ == '__main__':
    test_cli_dry_run()
    print('cli test passed')
