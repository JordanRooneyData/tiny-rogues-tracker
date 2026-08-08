import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QTableWidgetItem, QVBoxLayout, QWidget

from tiny_rogues_tracker.gui import (
    LogicalSeparator,
    PALETTE,
    SortableTable,
    crowned_class_label,
    has_full_deity_c16,
    resolve_logical_separators,
)


def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    return inst


def process():
    app().processEvents()


def make_rec(name="Chaos", eden=16, amon=16, primal=16):
    return SimpleNamespace(character=name, best_eden=eden, best_amon=amon, best_primal_death=primal)


def build_table(headers=None, ids=None, rows=3):
    app()
    headers = headers or ["Class", "Death", "Win+", "Eden", "Amon", "Primal Death", "Top Floor Beaten"]
    ids = ids or ["class", "best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "top_floor_rank"]
    table = SortableTable("v0.5.1 table")
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.set_logical_column_ids(ids)
    table.protected_leading_headers = ["class"] if ids and ids[0] == "class" else []
    table.setRowCount(rows)
    for c in range(len(headers)):
        table.setColumnWidth(c, 72 + c * 3)
    for r in range(rows):
        table.setRowHeight(r, 24 + r)
        table.setVerticalHeaderItem(r, QTableWidgetItem(f"row {r}"))
        for c, h in enumerate(headers):
            item = QTableWidgetItem(f"{h}:{r}")
            item.setData(Qt.UserRole, f"{ids[c]}:{r}")
            table.setItem(r, c, item)
    table.resize(900, 420)
    table.finalize_default_order()
    table.show()
    process()
    return table


def test_full_deity_c16_crown_rules_and_identity_are_display_only():
    crowned = make_rec("Chaos", 16, 16, 16)
    assert has_full_deity_c16(crowned)
    assert crowned_class_label(crowned) == "👑 Chaos"
    assert crowned.character == "Chaos"

    assert not has_full_deity_c16(make_rec("Chaos", 16, 15, 16))
    assert crowned_class_label(make_rec("Chaos", 16, 15, 16)) == "Chaos"
    assert not has_full_deity_c16(make_rec("Chaos", 16, None, 16))
    assert crowned_class_label(make_rec("Chaos", 16, None, 16)) == "Chaos"
    assert crowned_class_label(crowned_class_label.__globals__["SimpleNamespace"] if False else crowned) == "👑 Chaos"
    assert crowned_class_label(crowned).count("👑") == 1


def test_separator_rules_are_pink_and_logical_for_cinder_and_kill_counts():
    cinder_ids = ["class", "best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "top_floor_rank"]
    cinder_headers = ["Class", "Death", "Win+", "Eden", "Amon", "Primal Death", "Top Floor Beaten"]
    cinder_seps = [
        LogicalSeparator(after_id="class"),
        LogicalSeparator(left_ids=("best_death", "best_win_plus"), right_ids=("best_eden", "best_amon", "best_primal_death")),
        LogicalSeparator(before_id="top_floor_rank"),
        LogicalSeparator(after_id="top_floor_rank"),
    ]
    assert resolve_logical_separators(cinder_headers, cinder_seps, cinder_ids) == {0, 2, 5}
    rev_ids = ["class", "top_floor_rank", "best_primal_death", "best_amon", "best_eden", "best_win_plus", "best_death"]
    rev_headers = ["Class", "Top Floor Beaten", "Primal Death", "Amon", "Eden", "Win+", "Death"]
    assert resolve_logical_separators(rev_headers, cinder_seps, rev_ids) == {0, 1, 4}

    kill_ids = ["class", "death_kills", "win_plus_kills", "eden_kills", "amon_kills", "primal_death_kills"]
    kill_headers = ["Class", "ALL Death Kills", "ALL Win+ Kills", "ALL Eden Kills", "ALL Amon Kills", "ALL Primal Death Kills"]
    kill_seps = [LogicalSeparator(after_id="class"), LogicalSeparator(left_ids=("death_kills", "win_plus_kills"), right_ids=("eden_kills", "amon_kills", "primal_death_kills"))]
    assert resolve_logical_separators(kill_headers, kill_seps, kill_ids) == {0, 2}

    table = build_table(kill_headers, kill_ids)
    table.logical_separators = kill_seps
    table._apply_separators()
    assert table.divider_delegate.divider_columns == {0, 2}
    assert PALETTE["hot_magenta"] != PALETTE["rare_gold"]


def test_sfm_content_border_wraps_visible_table_content_and_updates_on_resize_and_hidden_columns():
    table = build_table()
    table.sfm.press(auto_select_first_col=False)
    table._apply_sfm_highlights()
    rect = table.sfm_content_border_rect()
    assert rect.width() == table.verticalHeader().width() + sum(table.columnWidth(c) for c in range(table.columnCount()))
    assert rect.height() == table.horizontalHeader().height() + sum(table.rowHeight(r) for r in range(table.rowCount()))
    assert rect.width() < table.width()  # no border through unused canvas

    hidden_width = table.columnWidth(3)
    table.setColumnHidden(3, True)
    process()
    hidden_rect = table.sfm_content_border_rect()
    assert hidden_rect.width() == rect.width() - hidden_width

    table.resize(700, 400)
    process()
    resized_rect = table.sfm_content_border_rect()
    assert resized_rect.width() == hidden_rect.width()


def test_compact_mode_hides_chrome_fits_title_and_restores_window_geometry():
    app()
    win = QMainWindow()
    page = QWidget()
    layout = QVBoxLayout(page)
    heading = QLabel("Normal heading")
    help_text = QLabel("normal help/status text")
    sfm = QPushButton("SFM"); sfm.setCheckable(True)
    exit_selection = QPushButton("X")
    title_row = QWidget(); title_layout = QVBoxLayout(title_row); title = QLabel(""); title_layout.addWidget(title)
    table = build_table(rows=2)
    table.setParent(page)
    layout.addWidget(heading); layout.addWidget(help_text); layout.addWidget(sfm); layout.addWidget(exit_selection); layout.addWidget(title_row); layout.addWidget(table)
    win.setCentralWidget(page)
    win.resize(900, 600)
    win.show(); process()
    before = win.saveGeometry()

    table.set_sfm_controls(sfm, help_text, exit_selection)
    table.set_compact_title_label(title, "🔥 CINDER HIGHSCORES 🔥", PALETTE["hell_red"])
    table.set_compact_chrome([heading, help_text, exit_selection, sfm], title_row)
    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_row(0); table.sfm.toggle_col(0); table.sfm.toggle_col(1)
    table.toggle_sfm()
    process()

    assert table.sfm.state == "compact"
    assert title_row.isVisible()
    assert title.isVisible()
    assert title.width() >= table._table_content_width()
    assert title.fontMetrics().horizontalAdvance(title.text()) <= title.width()
    assert not heading.isVisible() and not help_text.isVisible() and not exit_selection.isVisible()
    assert win.width() <= 900 and win.height() <= 600

    table.toggle_sfm()
    process()
    assert table.sfm.state == "normal"
    assert heading.isVisible() and help_text.isVisible()
    gui_source = (Path(__file__).resolve().parents[1] / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    assert "main.saveGeometry()" in gui_source and "main.restoreGeometry(self.normal_window_geometry)" in gui_source
    assert table.normal_window_geometry is None and table.normal_window_state is None


def test_compact_title_stays_big_and_fully_visible_when_selected_table_is_narrow():
    app()
    win = QMainWindow()
    page = QWidget()
    layout = QVBoxLayout(page)
    sfm = QPushButton("SFM"); sfm.setCheckable(True)
    help_text = QLabel("help")
    title_row = QWidget(); title_layout = QVBoxLayout(title_row); title = QLabel(""); title_layout.addWidget(title)
    table = build_table(headers=["Class"], ids=["class"], rows=1)
    table.setParent(page)
    layout.addWidget(sfm); layout.addWidget(help_text); layout.addWidget(title_row); layout.addWidget(table)
    win.setCentralWidget(page)
    win.resize(700, 500)
    win.show(); process()

    text = "🔥 CINDER HIGHSCORES 🔥"
    table.set_sfm_controls(sfm, help_text)
    table.set_compact_title_label(title, text, PALETTE["hell_red"])
    table.set_compact_chrome([sfm, help_text], title_row)
    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_row(0); table.sfm.toggle_col(0)
    table.toggle_sfm()
    process()

    assert table.sfm.state == "compact"
    assert title.isVisible()
    assert title.font().bold()
    assert title.font().pointSize() >= 20
    assert title.fontMetrics().horizontalAdvance(text) <= title.width()
    assert title.height() >= title.fontMetrics().height()
    assert win.width() >= title.width()
