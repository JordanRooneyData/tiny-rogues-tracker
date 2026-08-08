# Tiny Rogues Tracker v0.4.10

Windows-first, read-only Tiny Rogues save tracker with a PySide6 desktop GUI.

## What v0.4.10 includes

- Universal save/class mapping repair: `RunRecords[].PlayedClass` now uses the verified IL2CPP `Player.PlayerClassId` map for the current build, including `26 = Chaos` and `34 = Santa`.
- `CinderStreakHistory` and Doppelganger variation history are separated from PlayedClass IDs, so long history arrays no longer create phantom `Class ID 35+` rows or attach historical Death clears to the wrong class.
- Unknown/future builds fail safely: actual unknown `PlayedClass` values remain visible as diagnostics, while unverified history-only slots are quarantined instead of confidently named.
- Added copyable mapping diagnostics for future bug reports without exposing raw save contents.
- Kill Counts cleanup: removed the `ALL/Cx Runs`, `ALL/Cx Death Kill Rate`, and `ALL/Cx Win+ Rate` columns from the table/export surface.
- Kill Counts headings now reflect the active filter directly, such as `ALL Death Kills`, `C16 Eden Kills`, and `C10–16 Primal Death Kills`.
- Cinder filter buttons now show selected state persistently; hover no longer mimics selection, and Shift-click range guidance is displayed beside the filter.
- Startup update hotfix: background release checks now marshal results back to the Qt GUI thread before showing prompts, fixing the missing boot prompt seen when updating from v0.4.5.
- SFM range selection now uses shift-click row/column header ranges, subtle header anchor styling, and a compact **X** to leave selection without creating a mini-table.
- SFM first-column auto-selection now applies only when the first column is a class/row-label column; Survival Breakdown no longer auto-selects ordinary data column `C0`.
- Survival Breakdown tables add a final **Totals** column plus fixed bottom **Death Kill Rate** and **Win+ Rate** rows.
- Survival Breakdown reversal now lives in right-click header menus; fixed rate rows stay pinned at the bottom.
- Compact SFM captures now show large, bold per-view titles such as `📊 BARBARIAN DEATHS 📊`, `🔥 CINDER HIGHSCORES 🔥`, and `💀 KILL COUNTS 💀`.
- Table sorting/restoration now preserves saved column widths and row heights rather than resizing from mini-table geometry.
- Kill Counts cinder buttons now show a subtle shift-click range anchor.
- Kill Counts Win+/Eden divider is painted as a border/delegate rather than inserted text, so it stays aligned through sorting/SFM.
- Main menu separates prominent primary tracker views from subdued utility actions.
- Kill Counts has route-aware colouring, a strong Win+/route separator, and an optional pinned **TOTALS** row for the active cinder filter.
- **Survival Breakdown** includes an **ALL** aggregate option plus visible **Deaths** / **Floors Completed** mode buttons and logical Back navigation.
- Cinder Highscores uses red numeric score values, neutral missing values, and gold best-value overrides.
- Working in-app auto-update flow: every normal GUI launch schedules one asynchronous GitHub Releases check after the main window is usable, prompts only when a newer installer exists, downloads the `TinyRoguesTracker-vX.Y.Z-Setup.exe` Inno installer, launches it in update mode, and exits cleanly. No-update auto-checks are silent; offline/check failures are non-blocking.
- Core views remain **Cinder Highscores**, **Kill Counts**, and **Survival Breakdown**.
- Manual **Check for updates** button uses the same installer path as the startup check and still reports when the app is already up to date.

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
dist\TinyRoguesTracker-v0.4.10.exe
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
7. Publishes artifacts for tagged releases like `v0.4.10`.

## Development validation

```bash
python3 -m pytest -q
python3 -m compileall -q tiny_rogues_tracker scripts tests
```

Linux note: PyInstaller cannot cross-build a real Windows `.exe` from Linux. The VPS validates source/tests and provides the Windows GitHub Actions pipeline; the final `.exe`/installer are produced on `windows-latest` or a local Windows machine.

## Mapping data

The bundled current-build class mapping was extracted from `Player.PlayerClassId` in IL2CPP metadata and stored in:

```text
tiny_rogues_tracker/data/tiny_rogues_class_mapping_c66eb2fb_e0d61b7f.json
```

For this build the normal PlayedClass roster is IDs `0..34`; `26` is `Chaos` and `34` is `Santa`. `CinderStreakHistory` is treated as a separate history namespace. Only verified core slots augment historical Death clears; Doppelganger variation/reserved tail slots are quarantined from the normal roster.
