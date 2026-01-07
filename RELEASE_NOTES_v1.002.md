Kiosk POS v1.002 — Release Notes

Release date: 2026-01-03

Highlights
- Ensure installer creates writable DB folder at `{commonappdata}\KioskPOS` and app initializes DB on first run.
- Added System Info panel in Settings showing database path, existence, and DB stats.
- Fixed taskbar icon behavior: regenerated ICO with required sizes and added Win32-level icon setting for reliability.
- Reworked DB initialization to use a system default path (ProgramData on Windows) and added migrations and lightweight schema fixes.
- Added thorough smoke-test and installer verification steps; updated installer metadata to v1.002.

Notes for distribution
- Installer: `dist/KioskPOS_Installer_v1.002.exe`
- EXE: `dist/main.exe`
- SHA256 checksums included in `dist/checksums.txt`

Recommended post-release steps
- Code-sign both EXE and installer using a trusted code-signing cert (High priority).
- Run cross-OS/VM testing on clean Windows 10 and 11 images.
- Publish SHA256 checksums alongside the installer download page for verification.
