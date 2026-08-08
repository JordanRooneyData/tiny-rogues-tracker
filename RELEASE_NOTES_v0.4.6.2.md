# Tiny Rogues Tracker v0.4.6.2 Release Notes

## Purpose

This is a deliberately small test-dummy update so the installed auto-update flow can be exercised after the v0.4.6.1 startup update-prompt hotfix.

## Changes

- Bumped app/package/build metadata to `0.4.6.2`.
- Updated Windows artifact names to `TinyRoguesTracker-v0.4.6.2.exe` and `TinyRoguesTracker-v0.4.6.2-Setup.exe`.
- Added this release-note file and README note identifying the release as an updater test.

## Tracker behaviour

No save parsing, GUI navigation, table, SFM, cinder, survival, updater logic, or save-write behaviour was intentionally changed.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
