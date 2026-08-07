# Tiny Rogues Tracker

Read-only Windows console tracker for Tiny Rogues save files.

## Deliverables

- `TinyRoguesTracker.exe` — standalone Windows x64 console executable.
- `ids.json` — permanent ID mapping file used by the tracker.
- `README.md` — this file.
- `report.txt` — generated report from the supplied save.

## Golden rule

The tracker is read-only. It opens the save file for reading, generates a report, and never writes back to the save.

## How to use on Windows

Simplest:

1. Put `TinyRoguesTracker.exe` and `ids.json` in the same folder.
2. Double-click `TinyRoguesTracker.exe`.
3. It checks the normal Tiny Rogues Unity save folder for the current Windows user:
   `C:\Users\<you>\AppData\LocalLow\RubyDev\Tiny Rogues`
4. It also scans each profile under `C:\Users\*` for:
   `AppData\LocalLow\RubyDev\Tiny Rogues`
5. If exactly one save location is found, it uses it automatically. If multiple saves/locations are found, it asks you to pick one.
6. It prints a clean console table and writes `report.txt` beside the executable.

Manual path:

```powershell
.\TinyRoguesTracker.exe --save "C:\Users\jorda\AppData\LocalLow\RubyDev\Tiny Rogues\Public_Slot1_Save1.json" --ids .\ids.json --report report.txt
```

## Current v2 behaviour

The tool reports the highest completed cinder value per character for:

- `Death` — from `CinderStreakHistory[].highestUsedCinderThisRun`, backed by `deathKills`.
- `Heaven` — inferred from observed post-Death boss pair `[21,23]`; final/completion boss ID `23` is labelled `Eden`.
- `Hell` — inferred from observed post-Death boss pair `[22,24]`; final/completion boss ID `24` is labelled `Amon`.
- `Law` / Shadow Planes — inferred from observed post-Death boss pair `[20,19]`; final/completion boss ID `19` is labelled `Primal Death`.

It also extracts and preserves mapping sections for:

- Character/class IDs
- Boss IDs
- Cinder modifier IDs
- Gifts
- Objectives
- Teleports
- Meta perks

## Mapping note

Google Drive auth was restored and the `gpt sources` archive was downloaded. `global-metadata.dat` yielded enum names for player classes, boss IDs, cinder modifiers, gifts, and objectives.

The supplied `GameAssembly.dll` inside the RAR extracted short by 207,360 bytes, so this build does **not** trust binary disassembly. `ids.json` is still permanent and upgradeable; unresolved entries are kept as safe fallback labels like `Boss ID 45`.

Route final boss labels are based on the save's observed post-Death boss pairs plus public route naming:

- High Heavens / Heaven → Eden
- Burning Hells / Hell → Amon
- Shadow Planes / Law → Primal Death

## Build from source

Linux host with MinGW:

```bash
make all
make test
```

Outputs:

- Linux test binary: `build/TinyRoguesTracker-linux`
- Windows executable: `dist/TinyRoguesTracker.exe`

## Files

```text
src/main.cpp                 C++17 read-only tracker
ids.json                     mapping file
fixtures/sample_save.json    minimal non-private test fixture
tests/test_tracker_contract.py
Makefile
```

Private supplied saves, logs, game binaries, and Google Drive source archives are not part of the public project bundle.
