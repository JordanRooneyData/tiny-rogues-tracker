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
3. It will try to auto-locate a Tiny Rogues save by searching common Windows user save locations for JSON files containing `RunRecords` and `CinderStreakHistory`.
4. It prints a clean console table and writes `report.txt` beside the executable.

Manual path:

```powershell
.\TinyRoguesTracker.exe --save "C:\path\to\Public_Slot1_Save1.json" --ids .\ids.json --report report.txt
```

## Current v1 behaviour

The tool extracts:

- Character/class IDs from `CinderStreakHistory` and `RunRecords[].PlayedClass`
- Death highest cinder from `CinderStreakHistory[].highestUsedCinderThisRun`
- Death kills from `CinderStreakHistory[].deathKills`
- Mega Death kills from `CinderStreakHistory[].megaDeathKills`
- Recent run max cinder from `RunRecords[].CinderLevel`
- Recent max floor from `RunRecords[].FloorReached`
- Boss IDs from `RunRecords[].bossesKilled`
- Cinder modifier IDs from `CinderModifiersEnabled`
- Gift IDs from `SelectedGift` / `UnlockedGifts` where present
- Objective IDs from `CompletedObjectives`
- Teleport IDs from `DiscoveredTeleportDestinations`
- Meta perk keys from `MetaPerks`

## Important mapping note

This build includes a real, permanent `ids.json`, but the friendly names are only partially resolved because Hermes could not access the Google Drive `gpt sources` folder during this run: the configured Google token was expired/revoked (`invalid_grant`).

So v1 is structurally complete and usable, but unresolved labels intentionally remain as safe fallbacks such as `Class ID 23` and `Boss ID 21`.

Once `GameAssembly.dll` and `global-metadata.dat` are available locally, `ids.json` can be upgraded without changing the parser.

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

Private supplied saves are not required by tests and are not part of the public project bundle.
