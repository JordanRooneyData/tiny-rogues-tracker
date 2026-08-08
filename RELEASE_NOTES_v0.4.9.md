# Tiny Rogues Tracker v0.4.9 Release Notes

Focused header-interaction and separator-logic release.

## Fixed

- Restored real left-click sorting on custom-rendered table headers.
- Header left-click sorting now cycles descending → ascending → default and uses numeric backing values where available.
- Header clicks in SFM selection mode remain reserved for SFM row/column selection; normal sorting returns immediately after exiting selection mode.
- Replaced the old right-click single sort menu with header reversal menus:
  - Column headers: `Reverse default column order`.
  - Row headers: `Reverse default row order`.
- Removed the standalone Survival Breakdown row/column reversal buttons and associated table-corner controls.
- Kept `Class` permanently leftmost for Cinder Highscores and Kill Counts during reversal, compact SFM, and restoration.
- Fixed Kill Counts separator logic so separators appear only at ordinary/deity group boundaries.
- Prevented false separators between deity columns, including Eden/Amon, Amon/Primal Death, and Eden/Primal Death compact adjacencies.
- Preserved dynamic separators through reversal, sorting, compact SFM mode, and full-table restoration.

## Root cause of lost left-click functionality

v0.4.8 introduced custom `SfmHeaderView` painting for visible header highlights, but replacing Qt's default headers left `sectionsClickable()` disabled on the new `QHeaderView` instances. The existing `sectionClicked` handlers for sorting/SFM were still connected, but real mouse clicks never emitted the signal. v0.4.9 explicitly enables clickable horizontal and vertical header sections and keeps all header input routed through state-aware handlers.

## Separator architecture note

Kill Counts exposed that visual suffix matching was too broad: `ALL Primal Death Kills` matched the ordinary `Death Kills` suffix and was classified into both groups. v0.4.9 adds stable logical column IDs and resolves separators from those IDs first, using visible labels only as a fallback for legacy/simple tables.

## Validation

- Added regression coverage for logical Kill Counts separators, real Qt left-click sorting, SFM click priority, header reversal menu source contracts, Class-column reversal exemption, compact SFM separators, and removed standalone reversal controls.
- Full validation command set:
  - `python3 -m pytest -q`
  - `python3 -m compileall -q tiny_rogues_tracker scripts tests`
