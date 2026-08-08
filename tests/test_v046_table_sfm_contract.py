from pathlib import Path

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import (
    DEATHS_MODE,
    EDEN_ID,
    SfmTableState,
    analyze_save,
    load_ids,
    matrix_presentation,
)

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"
IDS = load_ids(ROOT / "ids.json")


def save_with_runs(runs):
    return {"TimeOfSave": "test", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(36)]}


def run(cls, cinder, floor, bosses):
    return {"PlayedClass": cls, "CinderLevel": cinder, "FloorReached": floor, "bossesKilled": bosses}


def test_version_is_046():
    assert __version__ == "0.4.10"


def test_survival_breakdown_totals_column_and_rate_rows_from_current_table_data():
    model = analyze_save(save_with_runs([
        run(0, 1, 9, [18]),          # Death's Castle clear endpoint at C1
        run(0, 1, 11, [18, EDEN_ID]),# Win+ endpoint at C1
        run(0, 2, 1, []),            # non-clear endpoint at C2
    ]), IDS)
    matrix = model.matrix_for_character(0, DEATHS_MODE)
    pres = matrix_presentation(matrix)
    assert pres.headers[-1] == "Totals"
    win_row = pres.row_labels.index("Win+")
    death_row = pres.row_labels.index("10 (Death's Castle)")
    dragon_row = pres.row_labels.index("11 (Dragon Floor)")
    assert pres.values[win_row][-1] == 1
    assert pres.values[death_row][-1] == 0
    assert pres.values[dragon_row][-1] == 1
    assert pres.row_labels[-2:] == ["Death Kill Rate", "Win+ Rate"]
    c1 = pres.headers.index("C1")
    c0 = pres.headers.index("C0")
    assert pres.values[-2][c1] == "100.0%"
    assert pres.values[-1][c1] == "50.0%"
    assert pres.values[-2][c0] == "—"


def test_matrix_presentation_reversal_keeps_rate_rows_bottom_and_totals_final():
    model = analyze_save(save_with_runs([run(0, 1, 9, [18]), run(0, 2, 11, [18, EDEN_ID])]), IDS)
    matrix = model.matrix_for_character(0, DEATHS_MODE)
    pres = matrix_presentation(matrix, columns_reversed=True, rows_reversed=True)
    assert pres.headers[0] == "C16"
    assert pres.headers[-1] == "Totals"
    assert pres.row_labels[-2:] == ["Death Kill Rate", "Win+ Rate"]
    assert pres.fixed_bottom_rows == 2


def test_sfm_conditional_first_column_auto_selection_and_shift_ranges():
    s = SfmTableState().press(auto_select_first_col=True)
    assert 0 in s.selected_cols
    s2 = SfmTableState().press(auto_select_first_col=False)
    assert 0 not in s2.selected_cols
    s2.toggle_col(2)
    s2.toggle_col(5, shift=True)
    s2.toggle_row(1)
    s2.toggle_row(3, shift=True)
    assert s2.col_anchor == 2
    assert s2.row_anchor == 1
    assert s2.selected_cols == {2, 3, 4, 5}
    assert s2.selected_rows == {1, 2, 3}
    assert (1, 2) in s2.highlighted_cells()
    s2.toggle_col(2)
    assert all(c != 2 for _, c in s2.highlighted_cells())


def test_sfm_exit_selection_control_and_no_header_text_markers_contract():
    gui = GUI.read_text(encoding="utf-8")
    assert "x_sfm = QPushButton(\"X\")" in gui
    assert "Exit SFM selection without creating a mini-table" in gui
    assert "def exit_sfm_selection" in gui
    assert "self.sfm.exit_to_normal()" in gui
    assert 'base + (" [SFM]"' not in gui
    assert "SFM row range anchor" in gui
    assert "SFM column range anchor" in gui


def test_survival_mini_table_context_and_reverse_controls_source_contract():
    gui = GUI.read_text(encoding="utf-8")
    matrix = gui.split("def show_matrix", 1)[1].split("def _check_updates", 1)[0]
    assert "Class selected:" in matrix
    assert "Mode:" in matrix
    assert "Reverse default column order" in gui
    assert "Reverse default row order" in gui
    assert "reverse_cols = QPushButton(\"↔\")" not in matrix
    assert "reverse_rows = QPushButton(\"↕\")" not in matrix
    assert "table.auto_select_first_col = False" in matrix
    assert "table.fixed_bottom_rows = presentation.fixed_bottom_rows" in matrix


def test_geometry_sorting_and_restoration_are_centralised_without_content_divider():
    gui = GUI.read_text(encoding="utf-8")
    assert "default_widths" in gui and "default_heights" in gui
    assert "compact_widths" in gui and "compact_heights" in gui
    assert "def _restore_table_geometry" in gui
    assert "resizeColumnsToContents()" in gui
    assert "resizeRowsToContents()" in gui
    assert "def _fit_compact_geometry" in gui
    assert "def _apply_survival_geometry" in gui
    assert "ColumnDividerDelegate" in gui
    assert "setText(item.text()" not in gui
    assert "divider_delegate.divider_column" in gui


def test_sort_cycle_numeric_and_fixed_rows_contract():
    gui = GUI.read_text(encoding="utf-8")
    assert "{1: 2, 2: 0, 0: 1}" in gui
    assert "item.data(Qt.UserRole)" in gui
    assert "bottom_start = max(self.pinned_rows, len(source) - self.fixed_bottom_rows)" in gui
    assert "pinned + indexed + bottom" in gui
    assert "self.row_order_reversed and self.sort_direction == 0" in gui


def test_kill_counts_cinder_anchor_and_divider_border_contract():
    gui = GUI.read_text(encoding="utf-8")
    counts = gui.split("def show_counts", 1)[1].split("def _toggle_totals", 1)[0]
    assert "value == self.cinder_anchor" in counts
    assert "setProperty(\"sfmAnchor\", True)" in counts
    assert "Cinder range anchor" in counts
    assert "LogicalSeparator(left_ids=(\"death_kills\", \"win_plus_kills\"), right_ids=(\"eden_kills\", \"amon_kills\", \"primal_death_kills\"))" in counts
    assert "divider_columns" in gui
