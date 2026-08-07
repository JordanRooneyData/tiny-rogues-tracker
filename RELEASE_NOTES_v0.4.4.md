# Tiny Rogues Tracker v0.4.4 Release Notes

## Highlights

- Reworked the main menu into clear **Primary Actions** and **Utility Actions** sections.
- Primary tracker views are visually prominent at the top: Cinder Highscores, Kill Counts, and Class Breakdown.
- Utility actions are moved to the bottom and styled with a darker, lower-priority treatment.
- Replaced the Class Breakdown class dropdown and confirmation button with an alphabetical grid of class buttons.
- Class buttons use equal sizing, wrap across rows, and open the selected class immediately.
- The class grid includes a small sprite-ready placeholder beside each class name until safe sprites are available.
- Updated version/build/release metadata to v0.4.4.

## Validation

- `python3 -m pytest -q`
- `python3 -m compileall -q tiny_rogues_tracker scripts tests`
- GitHub Actions Windows release workflow publishes:
  - `TinyRoguesTracker-v0.4.4.exe`
  - `TinyRoguesTracker-v0.4.4-Setup.exe`
  - `install_latest.ps1`
