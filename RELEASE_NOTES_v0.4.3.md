# Tiny Rogues Tracker v0.4.3 Release Notes

## Highlights

- Cleaned up the Kill Counts table by removing the visible/backing runs and rate columns from the UI/export table surface.
- Renamed Kill Counts headings to include the active cinder filter, for example `ALL Death Kills`, `C16 Eden Kills`, and `C10–16 Primal Death Kills`.
- Improved the cinder selector so selected buttons stay visibly selected, multiple selected range buttons remain selected together, and hover no longer looks like selection.
- Added a visible Shift-click range hint beside the cinder filter status.
- Fixed Screenshot Friendly Mode restoration from mini-table mode by restoring from the authoritative full table snapshot rather than the compact table.
- SFM selection mode now auto-selects the first/Class column so class names are included by default.
- SFM highlight recalculation now clears obsolete intersections immediately when selected row/column headers are unselected.
- Updated version/build/release metadata to v0.4.3.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow builds and publishes:
  - `TinyRoguesTracker-v0.4.3.exe`
  - `TinyRoguesTracker-v0.4.3-Setup.exe`
  - `install_latest.ps1`

## Limits

The Linux VPS cannot run the Windows GUI interactively or perform an installed Inno upgrade smoke test. Windows artifacts are built and published by GitHub Actions on `windows-latest`.
