import json
from pathlib import Path

import pytest

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import (
    CinderSelection,
    SfmTableState,
    SortState,
    analyze_save,
    cinder_selection_from_click,
    format_rate,
    load_ids,
    top_floor_beaten,
)

ROOT = Path(__file__).resolve().parents[1]
IDS = load_ids(ROOT / "ids.json")
SAMPLE = json.loads((ROOT / "fixtures" / "sample_save.json").read_text(encoding="utf-8"))


def save_with_runs(runs, streaks_len=36):
    return {"TimeOfSave": "test", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(streaks_len)]}


def test_version_is_0431_and_views_are_renamed_in_gui_source():
    assert __version__ == "0.4.3.1"
    gui = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for text in [gui, readme]:
        assert "Cinder Highscores" in text
        assert "Kill Counts" in text
        assert "Class Breakdown" in text
    assert "Character Records" not in gui
    assert "Completion Counts and Rates" not in gui
    assert "Character Run Matrix" not in gui


def test_sort_is_numeric_desc_asc_default_and_stable_no_highlight_state():
    rows = [
        {"name": "a", "value": "0", "_order": 0},
        {"name": "b", "value": "100", "_order": 1},
        {"name": "c", "value": "14", "_order": 2},
        {"name": "d", "value": "17", "_order": 3},
        {"name": "e", "value": "10 (Death)", "_order": 4},
    ]
    state = SortState()
    assert [r["value"] for r in state.click(rows, "value")] == ["100", "17", "14", "10 (Death)", "0"]
    assert state.indicator == "▼"
    assert [r["value"] for r in state.click(rows, "value")] == ["0", "10 (Death)", "14", "17", "100"]
    assert state.indicator == "▲"
    assert [r["_order"] for r in state.click(rows, "value")] == [0, 1, 2, 3, 4]
    assert state.indicator == ""


def test_sfm_three_state_and_and_based_compact_selection():
    sfm = SfmTableState()
    sfm.press()
    assert sfm.state == "selection"
    assert "SFM SELECTION HAS BEEN ACTIVATED" in sfm.message
    sfm.toggle_row(1); sfm.toggle_row(3); sfm.toggle_col(2)
    assert sfm.highlighted_cells() == {(1, 0), (1, 2), (3, 0), (3, 2)}
    sfm.press()
    assert sfm.state == "compact"
    compact = sfm.compact_shape(["r0", "r1", "r2", "r3"], ["c0", "c1", "c2"], [[f"{r}{c}" for c in range(3)] for r in range(4)])
    assert compact == (["r1", "r3"], ["c0", "c2"], [["10", "12"], ["30", "32"]])
    sfm.press()
    assert sfm.state == "normal" and not sfm.selected_rows and not sfm.selected_cols


def test_empty_sfm_selection_stays_in_selection_mode_without_modal_requirement():
    sfm = SfmTableState().press()
    sfm.press()
    assert sfm.state == "selection"
    assert "Select at least one row and one column" in sfm.message


def test_cinder_filter_all_single_range_and_all_shift_lower_bound():
    sel = CinderSelection.all()
    assert sel.display_text == "Cinder filter: ALL"
    sel, anchor = cinder_selection_from_click(sel, 10, shift=True, anchor=None)
    assert sel.label == "C1–10" and anchor == 1
    sel, anchor = cinder_selection_from_click(sel, 16, shift=False, anchor=anchor)
    assert sel.label == "C16" and anchor == 16
    sel, anchor = cinder_selection_from_click(sel, 10, shift=False, anchor=anchor)
    sel, anchor = cinder_selection_from_click(sel, 16, shift=True, anchor=anchor)
    assert sel.label == "C10–16"
    sel, anchor = cinder_selection_from_click(sel, "ALL", shift=False, anchor=anchor)
    assert sel.label == "ALL" and anchor is None


def test_filter_aware_counts_rates_win_plus_and_zero_denominator():
    model = analyze_save(SAMPLE, IDS)
    all_rows = model.completion_rows(CinderSelection.all())
    c16 = model.completion_rows(CinderSelection.single(16))
    assert all_rows.by_name["Ninja"].win_plus_rate == pytest.approx(1.0)
    assert c16.by_name["Ninja"].win_plus_clears == 1
    assert c16.by_name["Ninja"].win_plus_rate == pytest.approx(1.0)
    assert c16.by_name["TheHero"].cx_runs == 0
    assert c16.by_name["TheHero"].death_rate is None
    assert format_rate(c16.by_name["TheHero"].death_rate) == "—"


def test_top_floor_beaten_is_boss_based_and_final_labels():
    assert top_floor_beaten({"FloorReached": 9, "bossesKilled": []}).label == "0"
    assert top_floor_beaten({"FloorReached": 11, "bossesKilled": [18]}).label == "10 (Death)"
    assert top_floor_beaten({"FloorReached": 11, "bossesKilled": [18, 21]}).label == "11 (Dragon)"
    assert top_floor_beaten({"FloorReached": 11, "bossesKilled": [18, 21, 24]}).label == "12 (Win+)"


def test_ninja_historical_death_clear_does_not_show_zero_runs_contradiction():
    save = save_with_runs([])
    save["CinderStreakHistory"][23] = {"highestUsedCinderThisRun": 16, "deathKills": 1}
    model = analyze_save(save, IDS)
    ninja = model.character_records_by_name["Ninja"]
    assert ninja.best_death == 16
    assert ninja.runs_display != "0"
    c16 = model.completion_rows(CinderSelection.single(16)).by_name["Ninja"]
    assert c16.cx_runs == 1
    assert c16.death_clears == 1
    assert c16.win_plus_clears == 0


def test_removed_columns_and_zero_fade_contracts_in_gui_source():
    gui = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    assert '"Total Runs"' not in gui
    assert '"Best Floor"' not in gui
    assert '"Top Floor Beaten"' in gui
    assert "PALETTE['zero']" in gui
    assert "zero_value" in gui
    assert "Sort descending" in gui and "Sort ascending" in gui and "Restore default order" in gui
