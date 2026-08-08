from tiny_rogues_tracker.core import (
    CinderSelection,
    all_character_ids,
    analyze_save,
    build_mapping_diagnostics,
    canonical_character_ids,
    cinder_history_slot_map,
    classify_cinder_history_slots,
    historical_death_cinders,
    load_ids,
)


def ids_with_history_map():
    return {
        "schema_version": 3,
        "characters": {
            "0": {"name": "TheHero", "logical_id": "the_hero"},
            "1": {"name": "Knight", "logical_id": "knight"},
            "23": {"name": "Ninja", "logical_id": "ninja"},
            "26": {"name": "Chaos", "logical_id": "chaos"},
            "34": {"name": "Santa", "logical_id": "santa"},
        },
        "character_roster": [0, 1, 23, 26, 34],
        "cinder_history_slots": {"0": 0, "1": 1, "23": 23, "26": 26, "34": 34},
        "class_mapping_adapters": [
            {
                "adapter_id": "synthetic-current-build",
                "status": "verified",
                "played_class_ids": {"26": "Chaos", "34": "Santa"},
                "core_cinder_history_slots": {"0": 0, "1": 1, "23": 23, "26": 26, "34": 34},
            }
        ],
    }


def save_with_history(length=36, variations=None, runs=None):
    save = {
        "TimeOfSave": "synthetic",
        "RunRecords": list(runs or []),
        "CinderStreakHistory": [{} for _ in range(length)],
    }
    if variations is not None:
        save["DoppelgangerVariationWins"] = variations
    return save


def run(cid, cinder=16, floor=11, bosses=None):
    return {"PlayedClass": cid, "CinderLevel": cinder, "FloorReached": floor, "bossesKilled": list(bosses or [])}


def test_current_build_registry_maps_chaos_and_santa_from_verified_data_file():
    ids = load_ids("ids.json")
    assert ids["characters"]["26"]["name"] == "Chaos"
    assert ids["characters"]["34"]["name"] == "Santa"
    assert canonical_character_ids(ids) == set(range(35))
    assert cinder_history_slot_map(ids)[26] == 26
    assert cinder_history_slot_map(ids)[34] == 34


def test_history_length_does_not_create_phantom_character_rows():
    ids = ids_with_history_map()
    save = save_with_history(length=65, variations=[{} for _ in range(29)])

    assert all_character_ids(ids, save) == [0, 1, 23, 26, 34]

    model = analyze_save(save, ids)
    assert [r.character_id for r in model.records] == [0, 1, 23, 26, 34]
    assert all(not r.character.startswith("Class ID 35") for r in model.records)


def test_historical_death_uses_verified_slot_map_not_history_index_namespace():
    ids = ids_with_history_map()
    save = save_with_history(length=65, variations=[{} for _ in range(29)])
    save["CinderStreakHistory"][23] = {"highestUsedCinderThisRun": 16, "deathKills": 1}
    save["CinderStreakHistory"][37] = {"highestUsedCinderThisRun": 16, "deathKills": 1}

    assert historical_death_cinders(save, ids) == [(23, 16)]

    model = analyze_save(save, ids)
    by_name = model.character_records_by_name
    assert by_name["Ninja"].best_death == 16
    assert by_name["Ninja"].minimum_runs == 1
    assert "Class ID 37" not in by_name

    rows = model.completion_rows(CinderSelection.single(16)).rows
    by_id = {r.character_id: r for r in rows}
    assert by_id[23].death_clears == 1
    assert 37 not in by_id


def test_unknown_played_class_rows_are_allowed_only_from_run_records():
    ids = ids_with_history_map()
    save = save_with_history(length=65, variations=[{} for _ in range(29)], runs=[run(99, cinder=5)])
    save["CinderStreakHistory"][37] = {"highestUsedCinderThisRun": 16, "deathKills": 1}

    model = analyze_save(save, ids)
    by_id = {r.character_id: r for r in model.records}
    assert 99 in by_id
    assert by_id[99].character == "Unknown PlayedClass ID 99"
    assert 37 not in by_id


def test_longer_history_classification_quarantines_variation_and_reserved_slots():
    ids = ids_with_history_map()
    save = save_with_history(length=65, variations=[{} for _ in range(29)])

    slots = classify_cinder_history_slots(save, ids)
    assert slots.core_slots == {0, 1, 23, 26, 34}
    assert len(slots.quarantined_slots) == 60
    assert slots.variation_count == 29
    assert 35 in slots.quarantined_slots and 64 in slots.quarantined_slots


def test_mismatched_history_variation_lengths_are_diagnostic_only():
    ids = ids_with_history_map()
    save = save_with_history(length=40, variations=[{} for _ in range(29)])

    slots = classify_cinder_history_slots(save, ids)
    assert slots.variation_count == 29
    assert slots.history_length == 40
    assert 35 in slots.quarantined_slots
    assert slots.warnings


def test_empty_variation_wins_and_unused_classes_keep_normal_roster():
    ids = ids_with_history_map()
    save = save_with_history(length=36, variations=[], runs=[run(26, cinder=16, bosses=[18, 23])])

    model = analyze_save(save, ids)
    assert [r.character_id for r in model.records] == [0, 1, 23, 26, 34]
    assert model.character_records_by_name["Chaos"].best_win_plus == 16
    assert model.character_records_by_name["Santa"].observed_runs == 0


def test_unknown_future_build_without_verified_history_map_fails_safe():
    ids = {"characters": {"0": {"name": "TheHero"}}, "character_roster": [0]}
    save = save_with_history(length=65, variations=[{} for _ in range(29)], runs=[run(37, cinder=12)])
    save["CinderStreakHistory"][0] = {"highestUsedCinderThisRun": 16, "deathKills": 1}

    assert historical_death_cinders(save, ids) == []
    model = analyze_save(save, ids)
    by_id = {r.character_id: r for r in model.records}
    assert set(by_id) == {0, 37}
    assert by_id[37].character == "Unknown PlayedClass ID 37"
    assert by_id[0].best_death is None


def test_no_duplicate_death_count_when_run_and_history_both_contain_same_clear():
    ids = ids_with_history_map()
    save = save_with_history(length=36, runs=[run(23, cinder=16, floor=10, bosses=[18])])
    save["CinderStreakHistory"][23] = {"highestUsedCinderThisRun": 16, "deathKills": 1}

    row = {r.character_id: r for r in analyze_save(save, ids).completion_rows(CinderSelection.single(16)).rows}[23]
    assert row.death_clears == 1
    assert row.inferred_historical_death_runs == 0


def test_mapping_diagnostics_report_compact_bug_report_fields():
    ids = ids_with_history_map()
    save = save_with_history(length=65, variations=[{} for _ in range(29)], runs=[run(26), run(99)])
    report = build_mapping_diagnostics(save, ids, game_assembly_sha256="ga", global_metadata_sha256="gm")

    assert "app_version" in report
    assert report["run_records"] == 2
    assert report["distinct_played_class_ids"] == [26, 99]
    assert report["cinder_streak_history_length"] == 65
    assert report["doppelganger_variation_wins_length"] == 29
    assert report["unknown_run_ids"] == [99]
    assert report["build_hashes"] == {"game_assembly_sha256": "ga", "global_metadata_sha256": "gm"}
    assert report["quarantined_history_slots_count"] == 60
