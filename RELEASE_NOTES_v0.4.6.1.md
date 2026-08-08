# Tiny Rogues Tracker v0.4.6.1 Release Notes

## Hotfix

- Fixed the startup update prompt being silently dropped when the background update-check thread found a newer release.
- The worker-thread callback now stores the result only; the Qt GUI thread drains it with a main-thread `QTimer` and shows the normal update prompt there.
- Manual **Check for updates** behaviour is unchanged.

## Why this matters

v0.4.5 could successfully detect v0.4.6 in the background, but the prompt scheduling used a context-free `QTimer.singleShot` from the worker thread. On Windows this can attach to the worker thread, which has no Qt event loop, so the prompt never appears.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow publishes:
  - `TinyRoguesTracker-v0.4.6.1.exe`
  - `TinyRoguesTracker-v0.4.6.1-Setup.exe`
  - `install_latest.ps1`
