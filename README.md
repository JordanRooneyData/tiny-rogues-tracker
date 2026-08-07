# Tiny Rogues Tracker v0.4.3

Windows-first, read-only Tiny Rogues save tracker with a PySide6 desktop GUI.

## What v0.4.3 includes

- Kill Counts cleanup: removed the `ALL/Cx Runs`, `ALL/Cx Death Kill Rate`, and `ALL/Cx Win+ Rate` columns from the table/export surface.
- Kill Counts headings now reflect the active filter directly, such as `ALL Death Kills`, `C16 Eden Kills`, and `C10–16 Primal Death Kills`.
- Cinder filter buttons now show selected state persistently; hover no longer mimics selection, and Shift-click range guidance is displayed beside the filter.
- Screenshot Friendly Mode now auto-selects the first/Class column, recalculates AND-rule highlights immediately, and restores the full original table from the authoritative snapshot after mini-table mode.
- Working in-app auto-update flow: every normal GUI launch checks GitHub Releases once, compares semantic versions, prompts with **Update now** / **Skip for now**, downloads the `TinyRoguesTracker-vX.Y.Z-Setup.exe` Inno installer, launches it in update mode, and exits cleanly. Offline/check failures are non-blocking.
- Core views remain **Cinder Highscores**, **Kill Counts**, and **Class Breakdown**.
- Manual **Check for updates** button uses the same installer path as the startup check.

## Run from source on Windows

```powershell
cd tiny-rogues-tracker
py -m pip install -e ".[test]"
py -m pip install PySide6
py scripts\run_gui.py
```

## Build the Windows app locally

```powershell
cd tiny-rogues-tracker
scripts\build_windows.ps1
```

Expected output:

```text
dist\TinyRoguesTracker-v0.4.3.exe
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

The main update mechanism is in-app auto-update. On every normal GUI launch the app checks this public GitHub Releases endpoint once with a short timeout:

```text
https://api.github.com/repos/JordanRooneyData/tiny-rogues-tracker/releases/latest
```

If a newer stable release exists, the app shows a small prompt with installed/available versions and release-note summary. **Update now** downloads the matching Inno installer asset, preferring `TinyRoguesTracker-vX.Y.Z-Setup.exe`, verifies that it is a non-empty Windows executable, launches the installer with per-user upgrade arguments, and exits. The installer keeps the stable `AppId`, reuses `%LOCALAPPDATA%\TinyRoguesTracker`, preserves user settings/config files under that directory, and relaunches the app after installation.

The fallback/bootstrap script remains:

```powershell
scripts\install_latest.ps1
```

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
7. Publishes artifacts for tagged releases like `v0.4.3`.

## Development validation

```bash
python3 -m pytest -q
python3 -m compileall -q tiny_rogues_tracker scripts tests
```

Linux note: PyInstaller cannot cross-build a real Windows `.exe` from Linux. The VPS validates source/tests and provides the Windows GitHub Actions pipeline; the final `.exe`/installer are produced on `windows-latest` or a local Windows machine.

## Mapping limits

The available decoded character metadata still ends at `Santa` (`33`). Character IDs `34` and `35` remain explicit unresolved mappings until newer game metadata identifies them.
