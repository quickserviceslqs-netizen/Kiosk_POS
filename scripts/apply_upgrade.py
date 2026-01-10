"""CLI to preview and apply upgrade packages.

Usage:
  python scripts/apply_upgrade.py [--preview] [--dry-run] [--db-path DB] [--install-dir DIR] package.zip

Exits 0 on success, non-zero on failure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from modules import upgrades


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply or preview an upgrade package")
    parser.add_argument("package", help="Path to upgrade zip package")
    parser.add_argument("--preview", action="store_true", help="Validate and print steps (no apply)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run (validate only)")
    parser.add_argument("--db-path", type=str, help="Path to the SQLite DB to use")
    parser.add_argument("--install-dir", type=str, help="Install directory for copy steps")
    parser.add_argument("--no-backup", action="store_true", help="Do not create an automatic DB backup before applying")
    parser.add_argument("--verbose", action="store_true", help="Print detailed logs")

    args = parser.parse_args(argv)
    pkg = Path(args.package)
    if not pkg.exists():
        print(f"Package not found: {pkg}")
        return 2

    try:
        if args.preview or args.dry_run:
            # validate and list steps
            manifest = upgrades.validate_package(str(pkg))
            print(f"Manifest version: {manifest.get('version')}")
            steps = manifest.get('steps', [])
            for i, s in enumerate(steps, 1):
                print(f"{i}. {s.get('type')}: {s}")
            if args.dry_run:
                # call apply_package with dry_run True to run any checks
                res = upgrades.apply_package(str(pkg), dry_run=True, backup_db=not args.no_backup, install_dir=args.install_dir, db_path=args.db_path)
                if args.verbose:
                    for l in res.get('logs', []):
                        print(l)
                return 0
            return 0

        # Normal apply
        res = upgrades.apply_package(str(pkg), dry_run=False, backup_db=not args.no_backup, install_dir=args.install_dir, db_path=args.db_path)
        for l in res.get('logs', []):
            print(l)
        if res.get('success'):
            print("Upgrade applied successfully")
            return 0
        else:
            print("Upgrade failed")
            return 3
    except Exception as e:
        print("Error during upgrade:", e)
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
