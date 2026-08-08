import json
from pathlib import Path

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import (
    AMON_ID,
    EDEN_ID,
    PRIMAL_DEATH_ID,
    DEATHS_MILESTONES,
    FLOORS_COMPLETED_MILESTONES,
    FLOORS_COMPLETED_MODE,
    SortState,
    analyze_save,
    load_ids,
)

ROOT = Path(__file__).resolve().parents[1]
IDS = load_ids(ROOT / "ids.json")
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"


def save_with_runs(runs):
    return {"TimeOfSave": "test", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(36)]}


def run(floor_reached, bosses=None, cinder=0, cls=0):
    return {"PlayedClass": cls, "CinderLevel": cinder, "FloorReached": floor_reached, "bossesKilled": bosses or []}


def test_version_is_0431():
    assert __version__ == "0.4.6.2"


def test_sfm_mini_table_numeric_sort_cycle_and_selection_sets_are_independent():
    rows = [
        {"class": "A", "value": "0", "_order": 0},
        {"class": "B", "value": "100", "_order": 1},
        {"class": "C", "value": "14", "_order": 2},
    ]
    selected_rows = {0, 2}
    selected_cols = {0, 1}
    state = SortState()
    assert [r["value"] for r in state.click(rows, "value")] == ["100", "14", "0"]
    assert state.indicator == "▼"
    assert [r["value"] for r in state.click(rows, "value")] == ["0", "14", "100"]
    assert state.indicator == "▲"
    assert [r["_order"] for r in state.click(rows, "value")] == [0, 1, 2]
    assert state.indicator == ""
    assert selected_rows == {0, 2}
    assert selected_cols == {0, 1}


def test_gui_sfm_compact_sorting_and_restore_contract_source():
    gui = GUI.read_text(encoding="utf-8")
    assert 'self.sfm.state not in ("normal", "compact")' in gui
    assert "self.compact_snapshot" in gui
    assert "self.compact_headers" in gui
    assert "source = self.compact_snapshot if compact else self.default_snapshot" in gui
    assert "headers = self.compact_headers if compact else self.base_headers" in gui
    assert "self.compact_snapshot = []" in gui
    assert "self.sort_direction = 0" in gui


def test_class_breakdown_modes_and_row_labels_contract_source():
    gui = GUI.read_text(encoding="utf-8")
    assert "Survival Breakdown" in gui
    assert "DEATHS_MODE" in gui
    assert "FLOORS_COMPLETED_MODE" in gui
    assert "self.show_matrix(cid, self.survival_mode)" in gui
    assert "self._table_page(VIEW_SURVIVAL_BREAKDOWN, back_target=self.survival_picker_widget)" in gui
    assert "Survival Breakdown —" not in gui
    assert DEATHS_MILESTONES == [
        "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "10 (Death's Castle)", "11 (Dragon Floor)", "12 (Deity Floor)", "Win+",
    ]
    assert FLOORS_COMPLETED_MILESTONES == DEATHS_MILESTONES[:-1]


def test_deaths_mode_maps_adjusted_floor_values_to_rows_1_through_12():
    runs = [run(floor_reached=i - 1, cinder=i % 17) for i in range(1, 13)]
    model = analyze_save(save_with_runs(runs), IDS)
    matrix = model.matrix_for_character(0)
    for i, label in enumerate(DEATHS_MILESTONES[:-1], start=1):
        assert matrix.cells[(i % 17, label)].count == 1


def test_completed_route_bosses_map_only_to_win_plus_deaths_row():
    model = analyze_save(save_with_runs([
        run(11, [EDEN_ID], cinder=1),
        run(11, [AMON_ID], cinder=2),
        run(11, [PRIMAL_DEATH_ID], cinder=3),
    ]), IDS)
    matrix = model.matrix_for_character(0)
    assert matrix.cells[(1, "Win+")].count == 1
    assert matrix.cells[(2, "Win+")].count == 1
    assert matrix.cells[(3, "Win+")].count == 1
    assert matrix.cells[(1, "12 (Deity Floor)")].count == 0
    assert matrix.cells[(2, "12 (Deity Floor)")].count == 0
    assert matrix.cells[(3, "12 (Deity Floor)")].count == 0


def test_floor_three_ending_deaths_and_floors_completed_counts():
    model = analyze_save(save_with_runs([run(2, [], cinder=7)]), IDS)
    deaths = model.matrix_for_character(0)
    completed = model.matrix_for_character(0, FLOORS_COMPLETED_MODE)
    assert deaths.cells[(7, "3")].count == 1
    assert completed.cells[(7, "1")].count == 1
    assert completed.cells[(7, "2")].count == 1
    assert completed.cells[(7, "3")].count == 0
    assert completed.cells[(7, "4")].count == 0


def test_win_plus_contributes_to_every_floor_completed_row_1_to_12():
    model = analyze_save(save_with_runs([run(11, [EDEN_ID], cinder=16)]), IDS)
    completed = model.matrix_for_character(0, FLOORS_COMPLETED_MODE)
    for label in FLOORS_COMPLETED_MILESTONES:
        assert completed.cells[(16, label)].count == 1
    assert "Win+" not in completed.milestones


def test_early_game_forced_end_uses_recorded_floor_not_previous_boss_advancement():
    # Stored/adjusted floor 3 with previous regular bosses killed remains a floor-3 ending.
    model = analyze_save(save_with_runs([run(2, [0, 1], cinder=5)]), IDS)
    deaths = model.matrix_for_character(0)
    assert deaths.cells[(5, "3")].count == 1
    assert deaths.cells[(5, "4")].count == 0
    completed = model.matrix_for_character(0, FLOORS_COMPLETED_MODE)
    assert completed.cells[(5, "1")].count == 1
    assert completed.cells[(5, "2")].count == 1
    assert completed.cells[(5, "3")].count == 0
