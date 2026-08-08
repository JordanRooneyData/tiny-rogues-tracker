from tiny_rogues_tracker.core import (
    AMON_ID,
    DEATH_IDS,
    EDEN_ID,
    PRIMAL_DEATH_IDS,
    CinderSelection,
    analyze_save,
    load_ids,
)


ROOT_IDS = load_ids("ids.json")


def run(cid=0, cinder=16, bosses=None, floor=11):
    return {
        "PlayedClass": cid,
        "CinderLevel": cinder,
        "FloorReached": floor,
        "bossesKilled": list(bosses or []),
    }


def save_with_runs(runs):
    return {"TimeOfSave": "synthetic", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(35)]}


def test_played_class_mapping_is_recovered_from_il2cpp_enum_defaults():
    expected = {
        0: "TheHero",
        1: "Knight",
        2: "Sorcerer",
        3: "Ranger",
        4: "Bandit",
        5: "Cleric",
        6: "Pyromancer",
        7: "Thief",
        8: "Wanderer",
        9: "Warrior",
        10: "Deprived",
        11: "Gunslinger",
        12: "Doppelganger",
        13: "Wizard",
        14: "Soldier",
        15: "Bard",
        16: "Mystic",
        17: "Monk",
        18: "Paladin",
        19: "SuperHero",
        20: "Necromancer",
        21: "Druid",
        22: "Barbarian",
        23: "Ninja",
        24: "DemonHunter",
        25: "Cyborg",
        26: "Chaos",
        27: "Dancer",
        28: "Dragoon",
        29: "Esper",
        30: "Jester",
        31: "Pirate",
        32: "Samurai",
        33: "Alchemist",
        34: "Santa",
    }
    assert {int(k): v["name"] for k, v in ROOT_IDS["characters"].items()} == expected


def test_boss_mapping_is_recovered_from_il2cpp_bossid_enum_and_not_route_inference():
    expected = {
        0: "Minotaur",
        1: "SpiderQueen",
        2: "Lich",
        3: "Banshee",
        4: "QueenBee",
        5: "Mandrake",
        6: "Gargoyles",
        7: "Vampire",
        8: "Sphinx",
        9: "Pharaoh",
        10: "Kraken",
        11: "Neptune",
        12: "RedDragon",
        13: "Phoenix",
        14: "Cerberus",
        15: "Succubus",
        16: "KingOoze",
        17: "MindFlamer",
        18: "Death",
        19: "PrimalDeath",
        20: "Geryon",
        21: "Tiamat",
        22: "Bahamut",
        23: "Amon",
        24: "Eden",
        25: "MegaPrimalDeath",
        26: "MegaAmon",
        27: "MegaEden",
        28: "GoblinKing",
        29: "MoleKing",
        30: "Troll",
        31: "ShamblingMound",
        32: "ThePiedPiper",
        33: "BookGolem",
        34: "IceDragon",
        35: "TheKingsGuard",
        36: "ArcaneGolem",
        37: "EvilOak",
        38: "RockGolem",
        39: "TangleMawJaw",
        40: "VerminKing",
        41: "JoustingChampion",
        42: "LibraryGuardian",
        43: "CommanderWalrus",
        44: "TheArchPontiff",
        45: "TheAbomination",
        46: "MegaDeath",
    }
    assert {int(k): v["name"] for k, v in ROOT_IDS["bosses"].items()} == expected


def test_route_final_constants_and_ids_include_base_and_mega_final_bosses():
    assert EDEN_ID == 24
    assert AMON_ID == 23
    assert DEATH_IDS == {18, 46}
    assert PRIMAL_DEATH_IDS == {19, 25}
    assert ROOT_IDS["routes"]["heaven"]["completion_boss_ids"] == [24, 27]
    assert ROOT_IDS["routes"]["hell"]["completion_boss_ids"] == [23, 26]
    assert ROOT_IDS["routes"]["law"]["completion_boss_ids"] == [19, 25]


def test_c16_amon_clear_counts_as_amon_not_eden_for_the_hero():
    model = analyze_save(save_with_runs([run(cid=0, cinder=16, bosses=[18, 23])]), ROOT_IDS)
    hero = model.character_records_by_name["TheHero"]
    assert hero.best_amon == 16
    assert hero.best_eden is None

    row = {r.character_id: r for r in model.completion_rows(CinderSelection.single(16)).rows}[0]
    assert row.amon_clears == 1
    assert row.eden_clears == 0


def test_c16_mega_amon_and_mega_eden_use_their_own_route_labels():
    model = analyze_save(
        save_with_runs([
            run(cid=0, cinder=16, bosses=[18, 26]),
            run(cid=1, cinder=16, bosses=[18, 27]),
        ]),
        ROOT_IDS,
    )
    by_name = model.character_records_by_name
    assert by_name["TheHero"].best_amon == 16
    assert by_name["TheHero"].best_eden is None
    assert by_name["Knight"].best_eden == 16
    assert by_name["Knight"].best_amon is None


def test_mega_death_counts_as_death_clear_but_not_win_plus():
    model = analyze_save(save_with_runs([run(cid=0, cinder=16, bosses=[46], floor=10)]), ROOT_IDS)
    hero = model.character_records_by_name["TheHero"]
    assert hero.best_death == 16
    assert hero.best_win_plus is None
    assert hero.top_floor_label == "10 (Death)"
