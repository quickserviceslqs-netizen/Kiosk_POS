"""
launch_demo.py — Standalone Demo launcher for Kiosk POS.

Cross-platform alternative to launch_demo.bat.
Run directly:

    python launch_demo.py

Or double-click if your OS associates .py with python.exe.

This script resolves the correct Python interpreter (venv-aware),
then relaunches main.py with the --demo flag in a subprocess.
The demo uses an isolated database (database/demo.db) that is
completely separate from your live store data.
"""

import os
import subprocess
import sys
from pathlib import Path


def _find_python(root_dir: Path) -> str:
    """Return the best Python interpreter: venv first, then sys.executable."""
    for candidate in (
        root_dir / ".venv" / "Scripts" / "python.exe",      # Windows venv
        root_dir / ".venv" / "bin" / "python",               # Unix venv
        root_dir / "venv" / "Scripts" / "python.exe",
        root_dir / "venv" / "bin" / "python",
    ):
        if candidate.exists():
            return str(candidate)
    return sys.executable                                     # system Python


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    main_script = app_dir / "main.py"

    if not main_script.exists():
        print(f"[ERROR] Could not find main.py in {app_dir}")
        input("Press Enter to exit…")
        sys.exit(1)

    python = _find_python(app_dir)

    print()
    print("  ================================================")
    print("   Kiosk POS  |  Demo Mode")
    print("   Isolated test environment — live data is safe")
    print("  ================================================")
    print()
    print(f"  Python : {python}")
    print(f"  Script : {main_script}")
    print()

    # Change to app directory so relative paths in main.py resolve correctly
    os.chdir(app_dir)

    result = subprocess.run([python, str(main_script), "--demo"])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
