from pathlib import Path
import tempfile
import shutil
import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import upgrades
from database.init_db import initialize_database

if __name__ == '__main__':
    td = tempfile.mkdtemp()
    db_path = Path(td) / 'pos_integ.db'
    initialize_database(db_path)
    install_dir = Path(td) / 'install'
    install_dir.mkdir()
    pkg = Path(r'c:\Users\ADMIN\Kiosk_Pos\tests\samples\sample_upgrade.zip')
    print('Using pkg:', pkg)
    res = upgrades.apply_package(str(pkg), dry_run=False, backup_db=True, install_dir=str(install_dir), db_path=str(db_path))
    print('RES:', res)
    shutil.rmtree(td)
