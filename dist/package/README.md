# Tiny Rogues Tracker

Read-only Windows console tracker for Tiny Rogues save files.

## Deliverables

- `TinyRoguesTracker.exe` — standalone Windows x64 console executable.
- `ids.json` — permanent ID mapping file used by the tracker.
- `README.md` — this file.
- `report.txt` — generated sample plain-text report.
- `report.csv` — CSV export of View 1 and View 2.

## Golden rule

The tracker is strictly read-only. It opens the save file for reading, generates reports, and never writes back to the Tiny Rogues save folder.

## How to use on Windows

Simplest:

1. Put `TinyRoguesTracker.exe`, `ids.json`, and this `README.md` in the same folder.
2. Double-click `TinyRoguesTracker.exe`.
3. It scans the normal Unity save folders:
   - `C:\Users\<you>\AppData\LocalLow\RubyDev\Tiny Rogues`
   - every `C:\Users\*\AppData\LocalLow\RubyDev\Tiny Rogues` profile
4. It parses candidate save files before presenting them.
5. Blank parses are ignored when they have empty `RunRecords` and no meaningful `CinderStreakHistory`.
6. If exactly one non-blank save exists, it is selected automatically. If multiple non-blank saves exist, a concise picker shows save time and run count.
7. The mode picker appears. Choose:
   - `1` best records by character
   - `2` Cinder 16 clear counts
   - `3` character floor × cinder matrix
8. The app only asks for a character after you choose mode 3.
9. `B` goes back, `M` returns to the main mode picker, and `Q` exits from interactive screens.
10. It writes `report.txt` and `report.csv` beside the executable.

Manual path:

```powershell
.\TinyRoguesTracker.exe --save "C:\Users\jorda\AppData\LocalLow\RubyDev\Tiny Rogues\Public_Slot1_Save1.json" --ids .\ids.json --report report.txt --csv report.csv
```

For scripted/non-interactive use:

```powershell
.\TinyRoguesTracker.exe --save "C:\path\to\Public_Slot1_Save1.json" --ids .\ids.json --report report.txt --csv report.csv --character 21 --no-pause
```

## What it shows

### View 1 — Best records by character

Every character is listed, including characters with zero runs. Columns:

- Best Death-clear cinder
- Best Win+ cinder
- Best Eden cinder
- Best Amon cinder
- Best PrimalDeath cinder
- Total recorded runs from `RunRecords`
- Best normalized in-game floor reached (`FloorReached + 1`)

`—` means no qualifying clear was found. A real Cinder 0 clear displays as `0`.

### View 2 — Cinder 16 clear counts by character

Every character is listed. Columns count qualifying Cinder 16 runs, not boolean flags:

- Death C16 clears
- Win+ C16 clears
- Eden C16 clears
- Amon C16 clears
- PrimalDeath C16 clears

### View 3 — Character floor × cinder matrix

One selected character is displayed as a terminal-outcome matrix:

- Columns: cinder `0` through `16`
- Rows: terminal outcome
- Normal unsuccessful runs use displayed floor `FloorReached + 1`
- Any run containing Eden, Amon, or PrimalDeath uses the terminal `Win+` row instead of also appearing as a normal floor outcome

The matrix is mutually exclusive: one run goes into one outcome cell only.

## Completion rules

Boss kills are the source of truth:

- Death clear: `bossesKilled` contains Death boss ID `18`.
- Win+: `bossesKilled` contains Eden, Amon, or PrimalDeath.
- Heaven clear: contains Eden boss ID `23`.
- Hell clear: contains Amon boss ID `24`.
- Law clear: contains PrimalDeath boss ID `19`.
- Reaching Bahamut (`21`), Tiamat (`20`), Geryon (`22`), or their/final-boss floor is **not** a route clear unless the final route boss was killed.
- `FloorReached` is zero-based in the save, so displayed floor is `FloorReached + 1`.

## Data reconciliation

- `RunRecords` are preferred for per-run counts and route-specific outcomes.
- `CinderStreakHistory` is used only to supplement historical Death-best cinder values when `deathKills` proves clears that may be absent from `RunRecords`.
- `CinderStreakHistory` is not counted as extra runs, which avoids double-counting.
- Unknown future save fields are preserved by the save file and ignored safely by the tracker.

## Mapping note

`ids.json` was enriched from the supplied Tiny Rogues metadata and save correlations. Death, Eden, Amon, PrimalDeath, Bahamut, Tiamat, and Geryon are explicitly mapped with confidence/source notes. The decoded character enum currently ends at `Santa` (`33`). Character IDs `34` and `35` are kept as unresolved fallbacks because the supplied metadata did not contain names after `Santa`.

## Build from source

Linux host with MinGW:

```bash
make all
python3 -m pytest -q
```

Outputs:

- Linux test binary: `build/TinyRoguesTracker-linux`
- Windows executable: `dist/TinyRoguesTracker.exe`
- Windows bundle: `dist/TinyRoguesTracker-v2-windows.zip`

Private supplied saves, logs, game binaries, and source archives are not part of the public project bundle.
