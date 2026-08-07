# Tiny Rogues Tracker v0.4.3.1 Release Notes

## Highlights

- Screenshot Friendly Mode mini-tables now keep normal numeric header sorting while compacted: descending, ascending, then mini-table default order.
- Mini-table sorting is scoped to the compact table and does not mutate selected SFM row/column sets.
- Leaving SFM restores the full authoritative table with normal default order and interactions.
- Class Breakdown now has a visible sub-mode selector for `Deaths` and `Floors Completed`.
- Deaths mode uses adjusted recorded `FloorReached` as the death/end floor, with completed Eden/Amon/Primal Death runs counted only in `Win+`.
- Floors Completed mode derives cumulative floor completion counts from the Deaths-mode ending floor; Win+ counts every floor 1–12 as completed.
- Early-game forced-end cases remain faithful to recorded run endings and are not advanced by ordinary boss kills.
- Updated version/build/release metadata to v0.4.3.1.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow publishes:
  - `TinyRoguesTracker-v0.4.3.1.exe`
  - `TinyRoguesTracker-v0.4.3.1-Setup.exe`
  - `install_latest.ps1`
