from pathlib import Path

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import (
    DEATHS_MODE,
    FLOORS_COMPLETED_MODE,
    EDEN_ID,
    SfmTableState,
    analyze_save,
    load_ids,
    matrix_presentation,
)

ROOT = Path(__file__).resolve().parents[1]
IDS = load_ids(ROOT / "ids.json")
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"


def save_with_runs(runs):
    return {"TimeOfSave": "test", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(36)]}


def run(cls=0, cinder=0, floor=0, bosses=None):
    return {"PlayedClass": cls, "CinderLevel": cinder, "FloorReached": floor, "bossesKilled": bosses or []}


def test_version_is_047():
    assert __version__ == "0.5.1"


def test_death_and_win_rates_use_displayed_deaths_mode_endpoints_only():
    model = analyze_save(save_with_runs([
        run(cinder=5, floor=0, bosses=[]),          # floor 1 endpoint
        run(cinder=5, floor=9, bosses=[]),          # ordinary floor 10 death, not after floor 10
        run(cinder=5, floor=9, bosses=[18]),        # Death killed -> progression-gated floor 11 death
        run(cinder=5, floor=11, bosses=[]),         # floor 12 endpoint
        run(cinder=5, floor=11, bosses=[18, EDEN_ID]),  # Win+
    ]), IDS)
    pres = matrix_presentation(model.matrix_for_character(0, DEATHS_MODE))
    c5 = pres.headers.index("C5")
    assert pres.values[pres.row_labels.index("10 (Death's Castle)")][c5] == 1
    assert pres.values[pres.row_labels.index("11 (Dragon Floor)")][c5] == 1
    assert pres.values[pres.row_labels.index("12 (Deity Floor)")][c5] == 1
    assert pres.values[pres.row_labels.index("Win+")][c5] == 1
    assert pres.values[pres.row_labels.index("Death Kill Rate")][c5] == "60.0%"
    assert pres.values[pres.row_labels.index("Win+ Rate")][c5] == "20.0%"


def test_rate_rows_exist_only_in_deaths_mode_and_are_pinned():
    model = analyze_save(save_with_runs([run(cinder=1, floor=11, bosses=[18, EDEN_ID])]), IDS)
    deaths = matrix_presentation(model.matrix_for_character(0, DEATHS_MODE))
    floors = matrix_presentation(model.matrix_for_character(0, FLOORS_COMPLETED_MODE))
    assert deaths.row_labels[-2:] == ["Death Kill Rate", "Win+ Rate"]
    assert deaths.fixed_bottom_rows == 2
    assert "Death Kill Rate" not in floors.row_labels
    assert "Win+ Rate" not in floors.row_labels
    assert floors.fixed_bottom_rows == 0


def test_reversal_moves_headers_and_values_together_with_rates_pinned():
    model = analyze_save(save_with_runs([
        run(cinder=1, floor=9, bosses=[18]),
        run(cinder=16, floor=11, bosses=[18, EDEN_ID]),
    ]), IDS)
    pres = matrix_presentation(model.matrix_for_character(0, DEATHS_MODE), columns_reversed=True, rows_reversed=True)
    assert pres.headers[:2] == ["C16", "C15"]
    assert pres.headers[-1] == "Totals"
    assert pres.row_labels[0] == "Win+"
    assert pres.row_labels[-2:] == ["Death Kill Rate", "Win+ Rate"]
    assert pres.values[pres.row_labels.index("Win+")][0] == 1
    assert pres.values[pres.row_labels.index("11 (Dragon Floor)")][pres.headers.index("C1")] == 1
    assert pres.values[pres.row_labels.index("Death Kill Rate")][0] == "100.0%"


def test_sfm_anchor_selected_and_deselected_shift_ranges():
    sfm = SfmTableState().press(auto_select_first_col=False)
    sfm.toggle_col(2)
    sfm.toggle_col(5, shift=True)
    assert sfm.selected_cols == {2, 3, 4, 5}
    assert sfm.col_anchor == 2
    sfm.toggle_col(2)  # deselect the anchor, but keep it as the visible anchor
    assert 2 not in sfm.selected_cols
    assert sfm.col_anchor == 2
    sfm.toggle_col(5, shift=True)
    assert sfm.selected_cols == set()
    assert sfm.highlighted_cells() == set()


def test_v047_gui_source_contracts_for_header_menu_corner_controls_and_geometry():
    gui = GUI.read_text(encoding="utf-8")
    assert "def _clear_sfm_header_marks" in gui
    assert "setCornerWidget" in gui
    assert "Reverse default column order" in gui
    assert "Reverse default row order" in gui
    assert "reverse_cols = QPushButton(\"↔\")" not in gui
    assert "reverse_rows = QPushButton(\"↕\")" not in gui
    matrix = gui.split("def show_matrix", 1)[1].split("def _check_updates", 1)[0]
    assert "switch.addWidget(reverse_cols)" not in matrix
    assert "set_corner_controls" not in matrix
    assert "def _fit_compact_geometry" in gui
    assert "def _apply_survival_geometry" in gui
    assert "col < 0 or col >= self.columnCount()" in gui
    assert "self._cycle_sort_col(column)" in gui
    collapse = gui.split("def _collapse_to_sfm_compact", 1)[1].split("def _apply_separator", 1)[0]
    assert "horizontalHeaderItem(c)" in collapse
    assert "self.base_headers[c] for c in cols" not in collapse


def test_top_floor_beaten_default_style_is_white_not_score_red():
    gui = GUI.read_text(encoding="utf-8")
    records = gui.split("def show_records", 1)[1].split("def show_counts", 1)[0]
    assert "top_floor_neutral=True" in records
    assert "PALETTE['moon_white']" in gui
