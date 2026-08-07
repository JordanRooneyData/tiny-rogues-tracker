# Tiny Rogues Tracker v0.4.2 Release Notes

## Highlights

- Fixed the installed app's auto-update path so normal GUI startup now checks the latest stable GitHub Release once per launch.
- Added a visible **Check for updates** action in the GUI using the same update path as startup.
- Update prompts now show installed version, available version, and a short release-note summary, with **Update now** and **Skip for now** buttons.
- The updater now selects the Inno Setup installer asset, preferring `TinyRoguesTracker-vX.Y.Z-Setup.exe`, instead of treating any `.exe` as acceptable.
- Downloads are verified as non-empty Windows executables before launch.
- Update failures are recoverable/non-blocking; the current version continues running.
- Draft and prerelease GitHub releases are ignored by default.
- Installer metadata remains per-user and stable: same `AppId`, same `%LOCALAPPDATA%\TinyRoguesTracker` install directory, low privileges, previous app directory reused, and app relaunch after successful upgrade.
- `install_latest.ps1` remains as a fallback/bootstrap tool; the app itself is now the main routine update path.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow builds and publishes:
  - `TinyRoguesTracker-v0.4.2.exe`
  - `TinyRoguesTracker-v0.4.2-Setup.exe`
  - `install_latest.ps1`

## Manual verification note

The Linux VPS cannot run a real installed Windows v0.4.1 → v0.4.2 upgrade. Automated tests cover version comparison, release filtering, installer selection, recoverable failures, GUI startup/manual wiring, and stable Inno upgrade metadata. A real Windows machine should verify launching installed v0.4.1, accepting v0.4.2, and confirming relaunch as v0.4.2.
