# Tiny Rogues Tracker v0.4.5 Release Notes

## Highlights

- Startup now schedules one asynchronous automatic update check after the main window is usable.
- Automatic update checks show the normal update prompt only when an update exists; no-update results stay silent while manual checks still report “up to date”.
- Back navigation now follows logical pages instead of walking through table/filter/sort/SFM state history.
- Renamed **Class Breakdown** to **Survival Breakdown** throughout the user-facing UI/docs.
- Survival Breakdown selection now has a separate **ALL** aggregate option plus visible **Deaths** / **Floors Completed** mode buttons instead of a dropdown.
- Kill Counts now supports a hidden-by-default totals row, pinned above class rows when enabled.
- Kill Counts route colours now apply only to positive Eden/Amon values and route headers; zero values stay faded.
- Added a strong separator between aggregate Win+ counts and route-specific boss counts.
- Cinder Highscores numeric score cells now render red, with gold still overriding for highest-value highlights and dashes remaining neutral.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow publishes:
  - `TinyRoguesTracker-v0.4.5.exe`
  - `TinyRoguesTracker-v0.4.5-Setup.exe`
  - `install_latest.ps1`
