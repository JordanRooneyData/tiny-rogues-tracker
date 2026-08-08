# Tiny Rogues Tracker v0.4.7 Release Notes

Focused correctness and table-behaviour release.

## Fixed

- Corrected Survival Breakdown Death Kill Rate and Win+ Rate rows so they appear only in Deaths mode, stay pinned at the bottom, and use displayed Deaths-mode run endpoints as their denominator.
- Treat Death-killed floor-10 progression-gated endings as floor 11 Deaths-mode endpoints while leaving ordinary floor-10 deaths unchanged.
- Fixed Survival Breakdown reversal behaviour so headers, values, totals, pinned rate rows, sorting indicators, and compact SFM headers move as one coherent table view.
- Moved Survival Breakdown reversal controls into the table corner cell and tightened cinder-column sizing.
- Kept Top Floor Beaten default values white while preserving gold highlights and muted empty values.
- Hardened header right-click sorting/menu handling against invalid header positions and repeated use.
- Improved SFM selection visuals so actual header cells are highlighted, anchors stay on the true clicked header, deselected-anchor shift ranges deselect, and stale intersection highlights clear immediately.
- Stabilised table geometry across sorting, reversals, SFM selection, and compact-table return paths.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
