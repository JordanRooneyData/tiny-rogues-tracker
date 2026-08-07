# Tiny Rogues Tracker v0.4.0

Windows-first, read-only Tiny Rogues save tracker with a PySide6 desktop GUI.

## What v0.4.0 includes

- PySide6 desktop app with Home screen, Character Records, Completion Counts/Rates, and Character Run Matrix.
- Read-only save loading; the app never writes to the Tiny Rogues save directory.
- Automatic save discovery at `C:\Users\*\AppData\LocalLow\RubyDev\Tiny Rogues`.
- Blank/new-save filtering and newest valid save defaulting.
- Save browse/reload path from the GUI.
- Correct Death vs Win+ rules:
  - Death clear = boss ID `18` killed.
  - Win+ = Eden `23`, Amon `24`, or Primal Death `19` killed.
  - Reaching a final floor without the final boss kill is not a clear.
- Corrected `Top Floor Beaten` semantics using actual boss kills, not merely deepest floor entered.
- Historical-clear provenance reconciliation: if a clear exists in `CinderStreakHistory` but retained `RunRecords` are missing, runs display as `≥1` with a tooltip rather than a misleading exact `0`.
- Sortable tables with numeric sort and default restoration model coverage.
- Screenshot Friendly Mode (`SFM`) table collapse workflow.
- Rare Gold best-value highlighting, faded zero/no-data values, and strict Tiny Rogues palette roles.
- Lightweight asynchronous GitHub Releases update check; offline failures do not block startup.

## Run from source on Windows

```powershell
cd TinyRoguesTracker
py -m pip install -e ".[test]"
py -m pip install PySide6
py scripts\run_gui.py
```

## Build the Windows app locally

```powershell
cd TinyRoguesTracker
scripts\build_windows.ps1
```

Expected output:

```text
dist\TinyRoguesTracker-v0.4.0.exe
```

## Installer

The installer definition is:

```text
installer\TinyRoguesTracker.iss
```

It installs into a user-writable directory:

```text
%LOCALAPPDATA%\TinyRoguesTracker
```

It does not install mutable files into the Steam/game directory.

## Bootstrap/update path

For public GitHub Releases, the bootstrap script is:

```powershell
scripts\install_latest.ps1
```

The app checks this release endpoint asynchronously on startup:

```text
https://api.github.com/repos/JDollan/TinyRoguesTracker/releases/latest
```

If a newer release exists, the user is offered an opt-in update. The app downloads the release installer, launches it, and exits cleanly rather than replacing a running executable.

## GitHub Actions release workflow

```text
.github\workflows\windows-release.yml
```

On Windows it:

1. Installs Python dependencies including PySide6.
2. Runs tests.
3. Runs compile checks.
4. Builds the PyInstaller executable.
5. Builds an Inno Setup installer.
6. Uploads artifacts.
7. Publishes artifacts for tagged releases like `v0.4.0`.

## Development validation

```bash
python3 -m pytest -q
python3 -m compileall -q tiny_rogues_tracker scripts tests
```

Linux note: PyInstaller cannot cross-build a real Windows `.exe` from Linux. The VPS validates source/tests and provides the Windows GitHub Actions pipeline; the final `.exe`/installer are produced on `windows-latest` or a local Windows machine.

## Mapping limits

The available decoded character metadata still ends at `Santa` (`33`). Character IDs `34` and `35` remain explicit unresolved mappings until newer game metadata identifies them.
