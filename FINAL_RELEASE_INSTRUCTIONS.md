Kiosk POS v1.002 — Final Release Instructions

Files produced:
- dist/KioskPOS_Installer_v1.002.exe
- dist/main.exe
- dist/checksums.txt
- RELEASE_NOTES_v1.002.md
- dist/KioskPOS_v1.002_release.zip

Steps to finalize and publish:
1. Code-signing (recommended):
   - Use `signing/sign_with_signtool.ps1` or perform signing in CI with secrets:
     - Secret: CODE_SIGN_PFX_PATH -> path to PFX (or upload to runner)
     - Secret: CODE_SIGN_PFX_PWD -> pfx password
   - Example (local):
       powershell .\signing\sign_with_signtool.ps1 -PfxPath C:\path\to\cert.pfx -PfxPassword "<pwd>" -Files "dist\main.exe","dist\KioskPOS_Installer_v1.002.exe"

2. Verify the signed artifacts:
   - Get-FileHash for SHA256 and compare with `dist/checksums.txt`.
   - Run the installer on a clean VM (Windows 10 and 11) and verify first-run initialization, login, create sale, receipts, uninstall.

3. Publish:
   - Create release in your GitHub (or file server) and upload the release zip and checksums.
   - Add release notes (`RELEASE_NOTES_v1.002.md`) and the SHA256 checksum text.

4. Post-release:
   - Monitor first-week installs for issues and be ready to push v1.003 for quick fixes if needed.

Automations added:
- `.github/workflows/release.yml` builds artifacts and can optionally sign using secrets, then creates a GitHub Release with artifacts.

If you want, I can:
- Sign the artifacts for you (you provide the PFX and password),
- Run cross-VM automated QA on Windows 10 & 11, or
- Publish the release to your GitHub (I can create the release and upload the assets).

Tell me which of the final steps you want me to run (sign / vm-test / publish / all / none).