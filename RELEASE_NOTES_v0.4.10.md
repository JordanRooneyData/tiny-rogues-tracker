# Tiny Rogues Tracker v0.4.10 Release Notes

Universal save/class mapping repair release.

## Fixed

- Corrected the authoritative `RunRecords[].PlayedClass` mapping for the current Tiny Rogues IL2CPP build.
- Restored missing/shifted class identity: `PlayedClass` ID `26` is now `Chaos`; ID `34` is now `Santa`.
- Removed phantom normal class rows such as `Class ID 35+` that were created from long `CinderStreakHistory` arrays.
- Stopped treating `RunRecords[].PlayedClass`, `CinderStreakHistory` indexes, and Doppelganger variation history indexes as the same namespace.
- Prevented historical Death-clear evidence from being attached to the wrong class by numeric position.
- Unknown class rows now appear only when an actual retained `RunRecords` entry contains an unknown `PlayedClass` ID.

## Mapping source/method

The bundled v0.4.10 map comes from the matching Tiny Rogues IL2CPP files supplied locally:

- `GameAssembly.dll` SHA256: `c66eb2fb70ce78e65da227b245cc43a5e92f2ec135bff721629d4c0485844369`
- `global-metadata.dat` SHA256: `e0d61b7f2173305e081fa0b063ec1fba2a98564262b4dff9ad033aac537a261c`

`Player.PlayerClassId` was extracted from IL2CPP metadata and stored in a build-specific adapter file:

- `tiny_rogues_tracker/data/tiny_rogues_class_mapping_c66eb2fb_e0d61b7f.json`

## New parser rules

- `RunRecords` are authoritative for detailed run statistics, route clears, Win+, deity clears, rates, and Survival Breakdown.
- `CinderStreakHistory` is a separate history namespace and can only augment historical Death clears through verified core class slot mappings.
- `DoppelgangerVariationWins` and any unverified/reserved history slots are quarantined from the normal roster.
- Save-array length no longer controls the normal class roster.
- Unknown/future builds fail safely: detailed run IDs remain visible, unverified history positions are not confidently named, and phantom roster rows are not fabricated.

## Diagnostics

Added a compact mapping diagnostics report for future bug reports. It summarizes version, run counts, distinct PlayedClass IDs, history lengths, quarantined slots, adapter source, unknown run IDs, and warnings without including raw save contents.

## Validation

Added synthetic regression coverage for:

- baseline history with no variations
- longer history with variation/reserved records
- mismatched history/variation lengths
- empty `DoppelgangerVariationWins`
- unused canonical classes
- actual unknown `PlayedClass` IDs
- unknown/reserved history-only slots
- unknown-build fallback
- pruned detailed runs plus historical Death evidence
- duplicate Death evidence prevention
- stable class mapping across unrelated saves
- diagnostics fields
