# Tiny Rogues Tracker v0.5.0 Release Notes

v0.5.0 polishes Screenshot Friendly Mode and table presentation while preserving the v0.4.11 save parsing, class mapping, boss mapping, updater, sorting, filters, navigation, and release pipeline.

## Screenshot Friendly Mode

- Compact Screenshot Mode now uses a dedicated screenshot-only layout: the compact table, a large bold fitted title, and one compact **Exit SFM** button.
- Compact mode hides normal page chrome including Back/Home/page headings, help text, filters, mode controls, save/update/export controls, and ordinary SFM instructions.
- Compact mode automatically resizes the app window to fit the selected title/table content with small margins, while respecting the available screen area.
- Leaving compact mode restores the previous normal window geometry/state and normal UI visibility.
- The yellow SFM selection perimeter now tracks the actual visible table content bounds instead of the unused table-widget canvas.

## Full C16 deity completion crown

- Cinder Highscores now visually rewards classes that have all three deity routes at Cinder 16:
  - Eden 16
  - Amon 16
  - Primal Death 16
- Qualifying classes show a yellow crowned visible label such as `👑 Chaos`.
- The crown is display-only: canonical class identity, sorting data, CSV export, and diagnostics are unchanged.
- Regression coverage verifies complete/missing/below-16 deity cases and duplicate-crown prevention.

## Pink logical divider system

- Thick logical dividers now use the shared pink/magenta UI accent instead of yellow, keeping yellow reserved for SFM/highlight states.
- Cinder Highscores now dynamically separates:
  - Class from metrics
  - non-deity metrics (`Death`, `Win+`) from deity metrics (`Eden`, `Amon`, `Primal Death`)
  - `Top Floor Beaten` from adjacent score metrics
- Kill Counts now dynamically separates:
  - Class from metrics
  - ordinary kills (`Death Kills`, `Win+ Kills`) from deity kills (`Eden Kills`, `Amon Kills`, `Primal Death Kills`)
- The separator rules use stable logical column IDs and survive sorting, default-order reversal, SFM selection, compact mode, and restoration.

## Validation

- Added v0.5.0 GUI regression tests for crowns, table-content SFM border geometry, compact chrome hiding/restoration, fitted compact titles, window restoration, and pink logical separators.
- Validation commands:
  - `python3 -m pytest -q`
  - `python3 -m compileall -q tiny_rogues_tracker scripts tests`
