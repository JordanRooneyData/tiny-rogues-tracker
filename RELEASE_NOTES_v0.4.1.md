# Tiny Rogues Tracker v0.4.1 Release Notes

## Highlights

- Fixed Screenshot Friendly Mode with the intended three-state workflow: normal table, row/column selection mode, and compact screenshot table.
- Fixed table sorting to use numeric backing values instead of rendered strings, with descending → ascending → default click cycle.
- Renamed views to **Cinder Highscores**, **Kill Counts**, and **Class Breakdown**.
- Removed Total Runs/rate-derived columns from Cinder Highscores and retained highscore/progression metrics.
- Renamed and reinforced **Top Floor Beaten** as boss-kill based, including the `10 (Death)`, `11 (Dragon)`, and `12 (Win+)` final labels.
- Added a visible Kill Counts cinder filter defaulting to `ALL`, with single-level and Shift-click range selection.
- Added filter-aware `Cx Runs`, `Cx Death Kill Rate`, and `Cx Win+ Rate` columns.
- Preserved zero-value fading, Rare Gold best-value highlighting, and route-specific colour semantics.
- Fixed the Ninja historical-run contradiction at the model level: `RunRecords` remain the source for route/floor detail, while `CinderStreakHistory` can add minimum historical Death-clear evidence without fabricating Win+/route/floor details.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`

## Limits

- Linux VPS cannot cross-build a real Windows PyInstaller executable. Windows artifacts are produced by GitHub Actions on `windows-latest` or by running `scripts/build_windows.ps1` locally on Windows.
- Character IDs 34 and 35 remain unresolved because available decoded metadata still ends at Santa (33).
