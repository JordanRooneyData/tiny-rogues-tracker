from pathlib import Path

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import CinderSelection, SfmTableState, cinder_selection_from_click

ROOT = Path(__file__).resolve().parents[1]


def test_version_is_0431():
    assert __version__ == "0.4.6.1"


def test_kill_counts_visible_columns_remove_runs_and_rates_and_use_filter_prefix():
    gui = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    core = (ROOT / "tiny_rogues_tracker" / "core.py").read_text(encoding="utf-8")
    assert 'f"{prefix} Runs"' not in gui
    assert 'f"{prefix} Death Kill Rate"' not in gui
    assert 'f"{prefix} Win+ Rate"' not in gui
    assert '"Death", f"{prefix} Death Kill Rate"' not in gui
    assert 'f"{prefix} Death Kills"' in gui
    assert 'f"{prefix} Eden Kills"' in gui
    assert 'f"{prefix} Amon Kills"' in gui
    assert 'f"{prefix} Primal Death Kills"' in gui
    assert "death_rate" not in core.split('def export_csv', 1)[1]
    assert "win_plus_rate" not in core.split('def export_csv', 1)[1]


def test_cinder_filter_label_and_shift_range_shape():
    assert CinderSelection.range(10, 16).label == "C10–16"
    sel, anchor = cinder_selection_from_click(CinderSelection.all(), 10, shift=True, anchor=None)
    assert sel.label == "C1–10" and anchor == 1
    sel, anchor = cinder_selection_from_click(CinderSelection.single(10), 16, shift=True, anchor=10)
    assert sel.label == "C10–16"


def test_cinder_button_selected_state_styling_contract():
    gui = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    assert 'setObjectName("CinderButton")' in gui
    assert "QPushButton:checked" in gui
    assert "background: {PALETTE['deep_violet']}" not in gui
    assert "Shift-click another level" in gui


def test_sfm_class_column_auto_selected_and_and_rule_removes_obsolete_highlights():
    sfm = SfmTableState()
    sfm.press()
    assert sfm.state == "selection"
    assert 0 in sfm.selected_cols
    sfm.toggle_row(2)
    sfm.toggle_col(3)
    assert sfm.highlighted_cells() == {(2, 0), (2, 3)}
    sfm.toggle_col(3)
    assert sfm.highlighted_cells() == {(2, 0)}
    sfm.toggle_row(2)
    assert sfm.highlighted_cells() == set()


def test_sfm_compact_and_restore_state_model():
    sfm = SfmTableState().press()
    sfm.toggle_row(0)
    sfm.toggle_row(2)
    sfm.toggle_col(2)
    sfm.press()
    rows, cols, values = sfm.compact_shape(
        ["TheHero", "Knight", "Ninja"],
        ["Class", "Death", "Eden"],
        [["TheHero", 0, 0], ["Knight", 1, 0], ["Ninja", 16, 1]],
    )
    assert rows == ["TheHero", "Ninja"]
    assert cols == ["Class", "Eden"]
    assert values == [["TheHero", 0], ["Ninja", 1]]
    sfm.press()
    assert sfm.state == "normal"
    assert not sfm.selected_rows and not sfm.selected_cols


def test_gui_restore_from_authoritative_snapshot_not_mini_table_source():
    gui = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    assert "self.setColumnCount(len(headers))" in gui
    assert "self.setHorizontalHeaderLabels(headers)" in gui
    assert "self.default_widths" in gui
    assert "item.setBackground(QColor())" in gui
    assert "if self.sfm.state == \"selection\":" in gui
    assert "return" in gui.split("def _header_clicked", 1)[1].split("def _row_header_clicked", 1)[0]
