import sys
import json
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')
from modules import upgrades


def make_sample_package(tmpdir: Path, include_extra: bool = False) -> Path:
    pkg = tmpdir / "upgrade_sample.zip"
    manifest = {
        "version": "1.1.0",
        "description": "Sample upgrade",
        "min_app_version": "1.0.0",
        "steps": [
            {"type": "sql", "file": "sql/001_add_table.sql"},
            {"type": "python", "file": "py/002_migrate.py"},
            {"type": "copy", "src": "assets/new.png"}
        ]
    }

    # Create files in a temp dir then zip them
    with zipfile.ZipFile(pkg, "w") as z:
        z.writestr("upgrade.json", json.dumps(manifest))
        z.writestr("sql/001_add_table.sql", "-- sample sql")
        z.writestr("py/002_migrate.py", "# sample python migration")
        z.writestr("assets/new.png", "PNGDATA")
        if include_extra:
            z.writestr("docs/readme.txt", "extra")
    return pkg


# Test: valid package
with tempfile.TemporaryDirectory() as td:
    p = make_sample_package(Path(td))
    m = upgrades.validate_package(str(p), current_app_version="1.2.0")
    print("PASS: valid manifest parsed; version=", m["version"])

# Test: missing manifest
with tempfile.TemporaryDirectory() as td:
    pkg = Path(td) / "broken.zip"
    with zipfile.ZipFile(pkg, "w") as z:
        z.writestr("some.txt", "hi")
    try:
        upgrades.validate_package(str(pkg))
        print("FAIL: expected missing manifest to raise")
    except upgrades.UpgradeValidationError as e:
        print("PASS: missing manifest raised:", e)

# Test: manifest refers missing file
with tempfile.TemporaryDirectory() as td:
    pkg = Path(td) / "badref.zip"
    bad_manifest = {"version": "1.0", "steps": [{"type":"sql","file":"sql/missing.sql"}]}
    with zipfile.ZipFile(pkg, "w") as z:
        z.writestr("upgrade.json", json.dumps(bad_manifest))
    try:
        upgrades.validate_package(str(pkg))
        print("FAIL: expected missing referenced file to raise")
    except upgrades.UpgradeValidationError as e:
        print("PASS: missing referenced file raised:", e)

print('All tests in test_upgrade_manifest.py completed')
