# Tiny Rogues Tracker v0.4.11 Release Notes

## Build mapping hotfix

v0.4.11 independently revalidates both the class and boss ID maps from the supplied Tiny Rogues build instead of trusting the previous tracker interpretation.

The tester report — a C16 Amon clear with The Hero appearing as Eden — is treated only as evidence that the old interpretation was unsafe. The fix does **not** assume Eden/Amon were merely swapped and does **not** assume The Hero's row was already correct.

## Evidence used

Local build files:

- `GameAssembly.dll` SHA-256: `c66eb2fb70ce78e65da227b245cc43a5e92f2ec135bff721629d4c0485844369`
- `global-metadata.dat` SHA-256: `e0d61b7f2173305e081fa0b063ec1fba2a98564262b4dff9ad033aac537a261c`

Recovered mappings:

- `Player.PlayerClassId` was parsed from IL2CPP metadata enum default values, not from tracker row order.
- `Enemies.BossId` was parsed from IL2CPP metadata enum default values.
- Eden/Amon/Primal Death final groupings were cross-checked against native `AchievementManager.CheckIfDoppelgangerDefeatedEdenAmonPrimalDeath` calls in `GameAssembly.dll`.

## Corrected route-final IDs

- Death: `18 = Death`, `46 = MegaDeath`
- Primal Death: `19 = PrimalDeath`, `25 = MegaPrimalDeath`
- Amon: `23 = Amon`, `26 = MegaAmon`
- Eden: `24 = Eden`, `27 = MegaEden`

The previous tracker mapping had `23` and `24` interpreted as Eden/Amon in the wrong order and did not include the mega final IDs as route finals.

## Class mapping

The complete `PlayedClass` mapping remains verified from IL2CPP enum defaults: IDs `0..34`, including `26 = Chaos` and `34 = Santa`.

## Tracker changes

- Route classification now counts Amon IDs `23` and `26` as Amon.
- Route classification now counts Eden IDs `24` and `27` as Eden.
- Primal Death includes `19` and `25`.
- Death includes `18` and `46` in the tracker Death-clear bucket.
- Boss data in `ids.json` now contains the full recovered `Enemies.BossId` enum `0..46`.
- Mapping adapter data now records both the class adapter and boss adapter provenance.

## Validation

Added regression coverage for:

- complete `PlayerClassId` mapping,
- complete `BossId` mapping,
- route-final constants and base/mega boss groupings,
- C16 The Hero Amon clear counting as Amon, not Eden,
- MegaAmon and MegaEden route labels,
- MegaDeath counting as a Death clear but not Win+.

Run locally before release:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
python3 -m compileall -q tiny_rogues_tracker scripts tests
```
