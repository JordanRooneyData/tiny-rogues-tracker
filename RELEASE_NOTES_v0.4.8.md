# Tiny Rogues Tracker v0.4.8 Release Notes

Focused screenshot/table rendering release.

## Fixed

- Reworked Screenshot Friendly Mode header visuals so selected row and column headers are painted directly by a custom `QHeaderView` layer.
- Selected headers now render visibly yellow using the existing gold/yellow palette colour.
- Current SFM anchor headers now render with a dotted cyan border on the actual header section; selected anchors show both yellow fill and dotted border, while deselected anchors keep normal fill plus the dotted border.
- Body-cell highlighting still follows the selected-row AND selected-column intersection rule, and `[SFM]` text is not added to labels.
- Added large bold compact screenshot titles:
  - `📊 <CLASS> DEATHS/FLOORS COMPLETED 📊` for Survival Breakdown.
  - `🔥 CINDER HIGHSCORES 🔥` for Cinder Highscores.
  - `💀 KILL COUNTS 💀` for Kill Counts.
- Restored/persisted Survival Breakdown reversal buttons and reinstalled them after table rebuilds, sorting, SFM compacting, and returning to the full table.
- Replaced the old single physical separator index with reusable logical separators that recompute from current visible headers.
- Dynamic separators now follow:
  - Survival Breakdown `Totals` boundary.
  - Cinder Highscores `Top Floor Beaten` boundary.
  - Kill Counts ordinary/deity boundary.

## Root cause of repeated header failures

Earlier patches styled `QTableWidgetItem` header items, but the app stylesheet paints native `QHeaderView::section` backgrounds directly. Qt's native/header stylesheet painting can overwrite or ignore model-level header item background roles, so tests that inspected internal item state passed while the actual rendered headers stayed unchanged. v0.4.8 moves selection, anchor, and separator rendering to a reusable custom `QHeaderView.paintSection()` layer and adds offscreen Qt rendering tests that inspect actual header pixels.

## Validation

- Added rendered Qt regression coverage for selected headers, anchor borders, compact titles, logical separator resolution, protected reversal ordering, and compact/full transitions.
- Full validation command set:
  - `python3 -m pytest -q`
  - `python3 -m compileall -q tiny_rogues_tracker scripts tests`
