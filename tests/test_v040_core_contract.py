import json
from pathlib import Path

import pytest

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import (
    CinderSelection,
    cinder_selection_from_click,
    SortState,
    analyze_save,
    choose_default_save,
    format_rate,
    is_blank_save,
    load_ids,
    top_floor_beaten,
    view3_frontier_highlights,
)

ROOT = Path(__file__).resolve().parents[1]
IDS = load_ids(ROOT / "ids.json")
SAMPLE = json.loads((ROOT / "fixtures" / "sample_save.json").read_text(encoding="utf-8"))


def save_with_runs(runs, streaks_len=36):
    return {"TimeOfSave": "test", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(streaks_len)]}


def test_version_is_0431():
    assert __version__ == "0.4.9"


def test_blank_save_filter_and_single_nonblank_auto_selection(tmp_path):
    blank = tmp_path / "Public_Slot1_Save1.json"
    real = tmp_path / "Public_Slot1_Save2.json"
    blank.write_text(json.dumps(save_with_runs([])), encoding="utf-8")
    real.write_text(json.dumps(SAMPLE), encoding="utf-8")
    assert is_blank_save(json.loads(blank.read_text())) is True
    assert choose_default_save([blank, real], IDS) == real


def test_floor_offset_and_top_floor_beaten_semantics():
    assert top_floor_beaten({"FloorReached": 0, "bossesKilled": []}).display_floor_entered == 1
    assert top_floor_beaten({"FloorReached": 5, "bossesKilled": []}).rank == 0
    assert top_floor_beaten({"bossesKilled": [0, 1, 2]}).rank == 3
    assert top_floor_beaten({"bossesKilled": [0, 18]}).label == "10 (Death)"
    assert top_floor_beaten({"bossesKilled": [18, 21]}).label == "11 (Dragon)"
    assert top_floor_beaten({"bossesKilled": [18, 23]}).label == "12 (Win+)"


def test_death_win_plus_and_route_separation():
    model = analyze_save(SAMPLE, IDS)
    druid = model.character_records_by_name["Druid"]
    ninja = model.character_records_by_name["Ninja"]
    alchemist = model.character_records_by_name["Alchemist"]
    assert druid.best_death == 12 and druid.best_eden == 12 and druid.best_win_plus == 12
    assert ninja.best_death == 16 and ninja.best_amon == 16 and ninja.best_win_plus == 16
    assert alchemist.best_primal_death == 14 and alchemist.best_win_plus == 14


def test_cinder_all_single_range_filtering_and_rates():
    model = analyze_save(SAMPLE, IDS)
    all_counts = model.completion_rows(CinderSelection.all())
    assert all_counts.by_name["Ninja"].cx_runs == 1
    c16 = model.completion_rows(CinderSelection.single(16))
    assert c16.label == "C16"
    assert c16.by_name["Ninja"].win_plus_rate == pytest.approx(1.0)
    rng = model.completion_rows(CinderSelection.range(12, 16))
    assert rng.label == "C12–16"
    assert rng.by_name["Druid"].cx_runs == 1
    selected, anchor = cinder_selection_from_click(CinderSelection.all(), 10, shift=True, anchor=None)
    assert selected.label == "C1–10" and anchor == 1
    selected, anchor = cinder_selection_from_click(selected, 16, shift=True, anchor=10)
    assert selected.label == "C10–16"
    assert format_rate(None) == "—"
    assert format_rate(0.5) == "50%"


def test_sort_cycle_numeric_and_restore_default():
    rows = [{"name": "b", "value": 2, "_order": 0}, {"name": "a", "value": 10, "_order": 1}]
    state = SortState()
    rows1 = state.click(rows, "value")
    assert [r["value"] for r in rows1] == [10, 2]
    rows2 = state.click(rows, "value")
    assert [r["value"] for r in rows2] == [2, 10]
    rows3 = state.click(rows, "value")
    assert [r["_order"] for r in rows3] == [0, 1]


def test_gold_highlighting_ties_and_zero_only_columns():
    model = analyze_save(SAMPLE, IDS)
    highlights = model.character_record_highlights()
    assert ("Druid", "best_eden") in highlights
    assert ("Ninja", "best_amon") in highlights
    assert not any(col == "best_primal_death" and name != "Alchemist" for name, col in highlights)
    zero_column = [(name, col) for name, col in highlights if col == "best_primal_death" and name == "TheHero"]
    assert not zero_column


def test_view3_dual_frontier_highlighting():
    model = analyze_save(SAMPLE, IDS)
    matrix = model.matrix_for_character("Druid")
    highlights = view3_frontier_highlights(matrix)
    assert (12, "Win+") in highlights


def test_historical_clear_without_retained_runs_is_truthful_not_zero():
    save = save_with_runs([])
    save["CinderStreakHistory"][23] = {"highestUsedCinderThisRun": 16, "deathKills": 1}
    model = analyze_save(save, IDS)
    ninja = model.character_records_by_name["Ninja"]
    assert ninja.observed_runs == 0
    assert ninja.minimum_runs == 1
    assert ninja.runs_display in {"≥1", "1+", "Unknown (at least 1)"}
    assert "historical" in ninja.runs_tooltip.lower()
