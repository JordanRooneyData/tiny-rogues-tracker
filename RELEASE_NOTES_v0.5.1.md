# Tiny Rogues Tracker v0.5.1 Release Notes

v0.5.1 is a focused Compact Screenshot Mode hotfix.

## Fix

- Fixed Compact Screenshot Mode title clipping/near-invisible shrinking when the selected compact table is narrow.
- The bold mode title now stays fully visible and readable, using a minimum 20pt bold title size.
- Compact window sizing now accounts for the title width and title height, not just the compact table content.
- The title remains display-only chrome; save parsing, class mapping, boss mapping, filters, sorting, SFM selection, crowns, separators, updater, and exports are unchanged.

## Validation

- Added a regression test that enters compact mode with a one-column narrow table and asserts the full title fits at a readable bold size.
- Validation commands:
  - `python3 -m pytest -q`
  - `python3 -m compileall -q tiny_rogues_tracker scripts tests`
