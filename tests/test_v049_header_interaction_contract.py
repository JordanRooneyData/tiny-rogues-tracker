import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.gui import LogicalSeparator, PALETTE, SortableTable, resolve_logical_separators

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"


def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    return inst


def process():
    app().processEvents()


def clean_headers(table):
    return [table._clean_header_text(table.horizontalHeaderItem(c).text()) for c in range(table.columnCount())]


def row_labels(table):
    return [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]


def click_header(table, column, modifier=Qt.NoModifier):
    header = table.horizontalHeader()
    point = QPoint(header.sectionViewportPosition(column) + header.sectionSize(column) // 2, header.height() // 2)
    QTest.mouseClick(header.viewport(), Qt.LeftButton, modifier, point)
    process()


def build_sort_table():
    app()
    table = SortableTable("Sort Test")
    table.setColumnCount(2)
    table.setHorizontalHeaderLabels(["Score", "Name"])
    table.setRowCount(3)
    table.setVerticalHeaderLabels(["one", "ten", "two"])
    for r, score in enumerate([1, 10, 2]):
        item = table.item(r, 0) or __import__("PySide6.QtWidgets", fromlist=["QTableWidgetItem"]).QTableWidgetItem(str(score))
        item.setText(str(score))
        item.setData(Qt.UserRole, score)
        table.setItem(r, 0, item)
        table.setItem(r, 1, __import__("PySide6.QtWidgets", fromlist=["QTableWidgetItem"]).QTableWidgetItem(chr(65 + r)))
    table.finalize_default_order()
    table.show()
    process()
    return table


def build_kill_count_like_table():
    app()
    table = SortableTable("Kill Counts")
    headers = ["Class", "ALL Death Kills", "ALL Win+ Kills", "ALL Eden Kills", "ALL Amon Kills", "ALL Primal Death Kills"]
    ids = ["class", "death_kills", "win_plus_kills", "eden_kills", "amon_kills", "primal_death_kills"]
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.set_logical_column_ids(ids)
    table.protected_leading_headers = ["class"]
    table.logical_separators = [LogicalSeparator(left_ids=("death_kills", "win_plus_kills"), right_ids=("eden_kills", "amon_kills", "primal_death_kills"))]
    table.setRowCount(2)
    table.setVerticalHeaderLabels(["Barbarian", "Mage"])
    for r in range(2):
        for c, h in enumerate(headers):
            item = __import__("PySide6.QtWidgets", fromlist=["QTableWidgetItem"]).QTableWidgetItem(f"{h}:{r}")
            item.setData(Qt.UserRole, r * 10 + c)
            table.setItem(r, c, item)
    table.finalize_default_order()
    table.show()
    process()
    return table


def test_version_is_v049():
    assert __version__ == "0.5.1"


def test_kill_counts_separator_uses_logical_ids_not_death_suffix_overlap():
    sep = LogicalSeparator(left_ids=("death_kills", "win_plus_kills"), right_ids=("eden_kills", "amon_kills", "primal_death_kills"))
    ids = ["class", "death_kills", "win_plus_kills", "eden_kills", "amon_kills", "primal_death_kills"]
    headers = ["Class", "ALL Death Kills", "ALL Win+ Kills", "ALL Eden Kills", "ALL Amon Kills", "ALL Primal Death Kills"]
    assert resolve_logical_separators(headers, [sep], ids) == {2}
    reversed_ids = ["class", "primal_death_kills", "amon_kills", "eden_kills", "win_plus_kills", "death_kills"]
    reversed_headers = ["Class", "ALL Primal Death Kills", "ALL Amon Kills", "ALL Eden Kills", "ALL Win+ Kills", "ALL Death Kills"]
    assert resolve_logical_separators(reversed_headers, [sep], reversed_ids) == {3}
    compact_ids = ["class", "amon_kills", "primal_death_kills"]
    compact_headers = ["Class", "ALL Amon Kills", "ALL Primal Death Kills"]
    assert resolve_logical_separators(compact_headers, [sep], compact_ids) == set()
    compact_ids = ["class", "death_kills", "primal_death_kills"]
    compact_headers = ["Class", "ALL Death Kills", "ALL Primal Death Kills"]
    assert resolve_logical_separators(compact_headers, [sep], compact_ids) == {1}


def test_real_left_click_header_cycles_numeric_sort_and_preserves_geometry():
    table = build_sort_table()
    widths = [table.columnWidth(c) for c in range(table.columnCount())]
    heights = [table.rowHeight(r) for r in range(table.rowCount())]
    assert table.horizontalHeader().sectionsClickable()

    click_header(table, 0)
    assert table.sort_direction == 1
    assert row_labels(table) == ["ten", "two", "one"]
    assert "▼" in table.horizontalHeaderItem(0).text()

    click_header(table, 0)
    assert table.sort_direction == 2
    assert row_labels(table) == ["one", "two", "ten"]
    assert "▲" in table.horizontalHeaderItem(0).text()

    click_header(table, 0)
    assert table.sort_direction == 0
    assert row_labels(table) == ["one", "ten", "two"]
    assert "▲" not in table.horizontalHeaderItem(0).text() and "▼" not in table.horizontalHeaderItem(0).text()
    assert [table.columnWidth(c) for c in range(table.columnCount())] == widths
    assert [table.rowHeight(r) for r in range(table.rowCount())] == heights


def test_left_click_sfm_selection_does_not_sort_then_sort_returns_after_sfm():
    table = build_sort_table()
    table.sfm.press(auto_select_first_col=False)
    table._apply_sfm_highlights()
    click_header(table, 0)
    assert table.sfm.state == "selection"
    assert table.sfm.selected_cols == {0}
    assert table.sort_direction == 0
    assert row_labels(table) == ["one", "ten", "two"]
    table.exit_sfm_selection()
    click_header(table, 0)
    assert table.sort_direction == 1
    assert row_labels(table) == ["ten", "two", "one"]


def test_right_click_menu_source_reverses_not_sorts_and_buttons_removed():
    gui = GUI.read_text(encoding="utf-8")
    init = gui.split("def __init__(self, title: str, parent=None):", 1)[1].split("def set_sfm_controls", 1)[0]
    assert "setSectionsClickable(True)" in init
    assert "self.verticalHeader().customContextMenuRequested.connect(self._row_header_menu)" in init
    header_menu = gui.split("def _header_menu", 1)[1].split("def _row_header_menu", 1)[0]
    row_menu = gui.split("def _row_header_menu", 1)[1].split("def _explicit_sort", 1)[0]
    assert "Reverse default column order" in header_menu
    assert "reverse_columns" in header_menu
    assert "_cycle_sort_col" not in header_menu
    assert "Reverse default row order" in row_menu
    assert "reverse_rows" in row_menu
    matrix = gui.split("def show_matrix", 1)[1].split("def _check_updates", 1)[0]
    assert 'QPushButton("↔")' not in matrix
    assert 'QPushButton("↕")' not in matrix
    assert "set_corner_controls(reverse_cols, reverse_rows)" not in matrix


def test_column_reversal_keeps_class_leftmost_values_together_and_separator_correct_in_compact_restore():
    table = build_kill_count_like_table()
    original = clean_headers(table)
    table.reverse_columns()
    assert clean_headers(table)[0] == "Class"
    assert clean_headers(table)[1:] == list(reversed(original[1:]))
    assert table.item(0, 1).text().startswith("ALL Primal Death Kills")
    assert table.divider_delegate.divider_columns == {3}

    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_row(0)
    table.sfm.toggle_row(1)
    table.sfm.toggle_col(0)  # class
    table.sfm.toggle_col(1)  # primal
    table.sfm.toggle_col(2)  # amon, deity/deity adjacency must not divide
    table.toggle_sfm()
    assert clean_headers(table) == ["Class", "ALL Primal Death Kills", "ALL Amon Kills"]
    assert table.divider_delegate.divider_columns == set()

    table.toggle_sfm()
    assert clean_headers(table)[0] == "Class"
    assert clean_headers(table)[1:] == list(reversed(original[1:]))
    assert table.divider_delegate.divider_columns == {3}


def test_reverse_rows_and_columns_noop_during_sfm_selection():
    table = build_kill_count_like_table()
    original_headers = clean_headers(table)
    original_rows = row_labels(table)
    table.sfm.press(auto_select_first_col=False)
    table.reverse_columns()
    table.reverse_rows()
    assert clean_headers(table) == original_headers
    assert row_labels(table) == original_rows
    assert table.column_order_reversed is False
    assert table.row_order_reversed is False
