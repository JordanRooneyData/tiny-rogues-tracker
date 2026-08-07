# Tiny Rogues Tracker v0.4.0 Release Notes

## Highlights

- Rebuilt tracker as a PySide6 desktop GUI.
- Added home/view-picker navigation and Back/Home actions.
- Added Character Records, Completion Counts/Rates, and Character Run Matrix views.
- Added read-only save discovery, blank-save filtering, newest valid save defaulting, manual browse, and reload path.
- Corrected floor offset and `Top Floor Beaten` to use actual beaten bosses.
- Fixed Death vs Win+ route rules: Eden, Amon, and Primal Death are boss-kill based and separated while also contributing to Win+.
- Added CinderSelection model for ALL, single cinder, and shift-click range semantics.
- Added historical-clear provenance reconciliation: clears from `CinderStreakHistory` without retained detailed runs display as `≥1` rather than exact zero.
- Added Rare Gold best-value highlighting models and zero/no-data subdued rendering.
- Added asynchronous GitHub Releases update checker and opt-in installer launch flow.
- Added GitHub Actions Windows workflow, PyInstaller build script, Inno Setup installer definition, and bootstrap installer script.

## Validation

- `python3 -m pytest -q` — 23 passed.
- `python3 -m compileall -q tiny_rogues_tracker scripts tests` — passed.
- GUI source contract validates PySide6 use, required views, SFM, navigation, palette, build workflow, installer, and updater endpoint.

## Limits

- Linux VPS cannot cross-build a real Windows PyInstaller executable. Windows artifacts are produced by GitHub Actions on `windows-latest` or by running `scripts/build_windows.ps1` locally on Windows.
- Character IDs 34 and 35 remain unresolved because available decoded metadata still ends at Santa (33).
