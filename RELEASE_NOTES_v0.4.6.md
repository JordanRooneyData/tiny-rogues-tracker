# Tiny Rogues Tracker v0.4.6 Release Notes

## Highlights

- Survival Breakdown tables now include a final **Totals** column for each row.
- Survival Breakdown adds fixed bottom **Death Kill Rate** and **Win+ Rate** rows with percentage formatting and `—` for zero denominators.
- Added compact row/column reverse controls for Survival Breakdown; fixed rate rows remain pinned at the bottom.
- Screenshot Friendly Mode now auto-selects the first column only on tables where it is a class/row-label column.
- SFM row and column headers support shift-click range selection with subtle anchor styling and no header-text mutation.
- Added an **X** control to leave SFM selection without creating a mini-table.
- Survival Breakdown SFM captures include compact context labels for selected class/ALL and mode.
- Table sort/restore now preserves saved widths/heights instead of resizing from mini-table state.
- Kill Counts cinder filter now shows a subtle range anchor.
- Kill Counts Win+/Eden divider is now a painted border/delegate rather than inserted cell text.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow publishes:
  - `TinyRoguesTracker-v0.4.6.exe`
  - `TinyRoguesTracker-v0.4.6-Setup.exe`
  - `install_latest.ps1`
