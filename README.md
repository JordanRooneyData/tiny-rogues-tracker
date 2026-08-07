# Tiny Rogues Tracker v0.4.1

Windows-first, read-only Tiny Rogues save tracker with a PySide6 desktop GUI.

## What v0.4.1 includes

- Focused GUI/functionality correction release on top of the previous desktop GUI release.
- Renamed views:
  - **Cinder Highscores** — per-class high cinder clears and **Top Floor Beaten**.
  - **Kill Counts** — filter-aware run/kill/rate table.
  - **Class Breakdown** — per-class cinder/progression matrix.
- Read-only save loading; the app never writes to the Tiny Rogues save directory.
- Automatic save discovery at `C:\Users\*\AppData\LocalLow\RubyDev\Tiny Rogues`.
- Blank/new-save filtering and newest valid save defaulting.
- Boss-kill based clear rules:
  - Death clear = boss ID `18` killed.
  - Win+ = Eden `23`, Amon `24`, or Primal Death `19` killed.
  - Reaching a final floor without the final boss kill is not a clear.
- **Top Floor Beaten** is calculated from defeated bosses, not deepest floor entered:
  - `10 (Death)` only when Death is killed.
  - `11 (Dragon)` only when a route dragon is killed without a final route boss.
  - `12 (Win+)` only when Eden, Amon, or Primal Death is killed.
- Kill Counts cinder selector defaults to `ALL` and supports single level plus Shift-click inclusive ranges from `1–16`.
- Numeric table sorting uses underlying numeric values, with click cycle descending → ascending → default.
- Screenshot Friendly Mode (`SFM`) now has a three-state flow: normal table → row/column selection → compact screenshot table.
- Zero values are faded but legible; Rare Gold highlights and route-specific colour rules still take precedence.
- Historical-clear reconciliation: detailed `RunRecords` are the source for route/floor analysis, while `CinderStreakHistory` can add a minimum historical Death-clear/run where retained detailed runs are missing. The app does not fabricate route, floor, or Win+ details from history-only data.
- Lightweight asynchronous GitHub Releases update check; offline failures do not block startup.

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
dist\TinyRoguesTracker-v0.4.1.exe
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
https://api.github.com/repos/JordanRooneyData/tiny-rogues-tracker/releases/latest
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
7. Publishes artifacts for tagged releases like `v0.4.1`.

## Development validation

```bash
python3 -m pytest -q
python3 -m compileall -q tiny_rogues_tracker scripts tests
```

Linux note: PyInstaller cannot cross-build a real Windows `.exe` from Linux. The VPS validates source/tests and provides the Windows GitHub Actions pipeline; the final `.exe`/installer are produced on `windows-latest` or a local Windows machine.

## Mapping limits

The available decoded character metadata still ends at `Santa` (`33`). Character IDs `34` and `35` remain explicit unresolved mappings until newer game metadata identifies them.
