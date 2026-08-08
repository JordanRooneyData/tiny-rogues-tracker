import json
from pathlib import Path

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.core import (
    CinderSelection,
    EDEN_ID,
    AMON_ID,
    VIEW_SURVIVAL_BREAKDOWN,
    analyze_save,
    completion_totals,
    load_ids,
)

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"
IDS = load_ids(ROOT / "ids.json")


def save_with_runs(runs):
    return {"TimeOfSave": "test", "RunRecords": runs, "CinderStreakHistory": [{} for _ in range(36)]}


def run(cls, cinder, bosses):
    return {"PlayedClass": cls, "CinderLevel": cinder, "FloorReached": 11, "bossesKilled": bosses}


def test_version_is_045_and_survival_breakdown_label():
    assert __version__ == "0.4.11"
    assert VIEW_SURVIVAL_BREAKDOWN == "Survival Breakdown"


def test_automatic_update_check_is_deferred_once_and_manual_no_update_remains_visible():
    gui = GUI.read_text(encoding="utf-8")
    assert "QTimer.singleShot(0, self._check_updates)" in gui
    assert "if self.update_check_started:" in gui
    assert "self.update_check_started = True" in gui
    assert "check_async(done)" in gui
    assert "self.pending_update_result = (info, err)" in gui
    assert "QTimer.singleShot(0, lambda: self._offer_update" not in gui
    auto = gui.split("def _check_updates", 1)[1].split("def manual_check_for_updates", 1)[0]
    manual = gui.split("def manual_check_for_updates", 1)[1].split("def _offer_update", 1)[0]
    assert "QMessageBox.information" not in auto
    assert "statusBar().showMessage" in auto
    assert "self._offer_update(info, manual=False)" in auto
    assert "Tiny Rogues Tracker is up to date" in manual
    assert "QMessageBox.information" in manual


def test_logical_back_navigation_uses_page_parents_not_stack_index_history():
    gui = GUI.read_text(encoding="utf-8")
    assert "self.page_parents" in gui
    assert "def _go_back" in gui
    assert "self.page_parents.get(current)" in gui
    assert "self.stack.setCurrentIndex(max(0, self.stack.currentIndex() - 1))" not in gui
    assert "back_target=self.survival_picker_widget" in gui


def test_kill_counts_totals_toggle_pinned_and_separator_contract():
    gui = GUI.read_text(encoding="utf-8")
    counts = gui.split("def show_counts", 1)[1].split("def _class_grid_columns", 1)[0]
    assert "Show Totals" in counts and "Hide Totals" in counts
    assert "display_rows = ([completion_totals(rows)] if self.show_totals else []) + rows" in counts
    assert "table.pinned_rows = 1 if self.show_totals else 0" in counts
    assert "table.set_logical_column_ids([\"class\", \"death_kills\", \"win_plus_kills\", \"eden_kills\", \"amon_kills\", \"primal_death_kills\"])" in counts
    assert "LogicalSeparator(left_ids=(\"death_kills\", \"win_plus_kills\"), right_ids=(\"eden_kills\", \"amon_kills\", \"primal_death_kills\"))" in counts
    assert "TOTALS" in (ROOT / "tiny_rogues_tracker" / "core.py").read_text(encoding="utf-8")
    assert "ColumnDividerDelegate" in gui
    assert "drawLine(option.rect.topRight(), option.rect.bottomRight())" in gui


def test_totals_respect_active_cinder_filter():
    model = analyze_save(save_with_runs([
        run(0, 16, [18]),
        run(1, 16, [18, EDEN_ID]),
        run(1, 10, [18, AMON_ID]),
    ]), IDS)
    rows = model.completion_rows(CinderSelection.single(16)).rows
    totals = completion_totals(rows)
    assert totals.character == "TOTALS"
    assert totals.cx_runs == 2
    assert totals.death_clears == 2
    assert totals.win_plus_clears == 1
    assert totals.eden_clears == 1
    assert totals.amon_clears == 0


def test_kill_counts_route_colours_skip_zero_and_headers_are_route_coloured():
    gui = GUI.read_text(encoding="utf-8")
    style = gui.split("def _style_item", 1)[1].split("def _style_route_headers", 1)[0]
    assert "if zero_value(val):" in style
    assert "return" in style.split("if zero_value(val):", 1)[1].split("if route ==", 1)[0]
    assert "route == \"eden\"" in style and "PALETTE['heaven_cyan']" in style
    assert "route == \"amon\"" in style and "PALETTE['flame_orange']" in style
    headers = gui.split("def _style_route_headers", 1)[1].split("def show_records", 1)[0]
    assert "Eden" in headers and "heaven_cyan" in headers
    assert "Amon" in headers and "flame_orange" in headers


def test_survival_breakdown_all_and_mode_buttons_not_dropdown():
    gui = GUI.read_text(encoding="utf-8")
    picker = gui.split("def show_matrix_picker", 1)[1].split("def show_matrix", 1)[0]
    assert "ALL classes" in picker
    assert "all_button = QPushButton(\"ALL\")" in picker
    assert "self.show_matrix(\"ALL\", self.survival_mode)" in picker
    assert "deaths = QPushButton(DEATHS_MODE)" in picker
    assert "floors = QPushButton(FLOORS_COMPLETED_MODE)" in picker
    assert "setCheckable(True)" in picker
    assert "QComboBox" not in picker
    assert "records = sorted(self.model.records, key=lambda r: r.character.lower())" in picker


def test_survival_breakdown_all_aggregates_all_classes():
    model = analyze_save(save_with_runs([
        {"PlayedClass": 0, "CinderLevel": 1, "FloorReached": 2, "bossesKilled": []},
        {"PlayedClass": 1, "CinderLevel": 1, "FloorReached": 2, "bossesKilled": []},
    ]), IDS)
    matrix = model.matrix_for_character("ALL")
    assert matrix.character == "ALL"
    assert matrix.cells[(1, "3")].count == 2


def test_cinder_highscores_numeric_red_gold_priority_and_dashes_neutral():
    gui = GUI.read_text(encoding="utf-8")
    style = gui.split("def _style_item", 1)[1].split("def _style_route_headers", 1)[0]
    assert "gold and not zero_value(val)" in style
    assert "PALETTE['rare_gold']" in style.split("gold and not zero_value(val)", 1)[1].split("if zero_value", 1)[0]
    assert "numeric_score" in style
    assert "PALETTE['hell_red']" in style
    assert "PALETTE['zero']" in style
    records = gui.split("def show_records", 1)[1].split("def show_counts", 1)[0]
    assert "numeric_score=(c > 0)" in records
