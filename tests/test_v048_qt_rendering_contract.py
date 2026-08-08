import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker.gui import (
    PALETTE,
    LogicalSeparator,
    SortableTable,
    column_order,
    resolve_logical_separators,
)

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QLabel, QTableWidgetItem

ROOT = Path(__file__).resolve().parents[1]


def app():
    return QApplication.instance() or QApplication([])


def process():
    app().processEvents()


def build_table(headers=("A", "B", "Totals"), rows=("R1", "R2", "Rate")):
    app()
    table = SortableTable("Test")
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setRowCount(len(rows))
    table.setVerticalHeaderLabels(list(rows))
    for r in range(len(rows)):
        for c in range(len(headers)):
            item = QTableWidgetItem(str((r + 1) * (c + 1)))
            item.setData(Qt.UserRole, (r + 1) * (c + 1))
            table.setItem(r, c, item)
    table.resize(520, 260)
    table.show()
    process()
    return table


def section_image(header, logical):
    pos = header.sectionViewportPosition(logical)
    size = header.sectionSize(logical)
    if header.orientation() == Qt.Horizontal:
        rect = QRect(pos, 0, size, header.height())
    else:
        rect = QRect(0, pos, header.width(), size)
    return header.viewport().grab(rect).toImage()


def count_pixels_close(image, expected_hex, tolerance=38):
    expected = QColor(expected_hex)
    count = 0
    for x in range(image.width()):
        for y in range(image.height()):
            color = image.pixelColor(x, y)
            if (
                abs(color.red() - expected.red()) <= tolerance
                and abs(color.green() - expected.green()) <= tolerance
                and abs(color.blue() - expected.blue()) <= tolerance
            ):
                count += 1
    return count


def test_version_is_048():
    assert __version__ == "0.4.9"


def test_selected_column_and_row_headers_visibly_render_yellow_on_qheaderview():
    table = build_table()
    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_col(1)
    table.sfm.toggle_row(0)
    table._apply_sfm_highlights()
    process()

    col_img = section_image(table.horizontalHeader(), 1)
    row_img = section_image(table.verticalHeader(), 0)
    default_img = section_image(table.horizontalHeader(), 0)

    assert count_pixels_close(col_img, PALETTE["rare_gold"]) > 120
    assert count_pixels_close(row_img, PALETTE["rare_gold"]) > 120
    assert count_pixels_close(default_img, PALETTE["rare_gold"]) < 40


def test_anchor_dotted_border_renders_on_actual_header_not_adjacent_body_cell():
    table = build_table()
    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_col(1)
    table.sfm.toggle_col(1)  # deselect but keep anchor
    table._apply_sfm_highlights()
    process()

    anchor_img = section_image(table.horizontalHeader(), 1)
    neighbor_img = section_image(table.horizontalHeader(), 0)
    body_img = table.viewport().grab(table.visualItemRect(table.item(0, 1))).toImage()

    assert count_pixels_close(anchor_img, PALETTE["heaven_cyan"], tolerance=45) > 30
    assert count_pixels_close(neighbor_img, PALETTE["heaven_cyan"], tolerance=45) < 25
    assert count_pixels_close(body_img, PALETTE["heaven_cyan"], tolerance=45) < 20
    assert count_pixels_close(anchor_img, PALETTE["rare_gold"]) < 80  # deselected anchor has no yellow fill


def test_selected_anchor_has_yellow_fill_plus_dotted_border_after_rebuild_sort_reverse_compact_restore():
    table = build_table(headers=("C0", "C1", "Totals"), rows=("1", "2", "Death Kill Rate"))
    table.protected_trailing_headers = ["Totals"]
    table.logical_separators = [LogicalSeparator(before="Totals")]
    table.fixed_bottom_rows = 1
    table.finalize_default_order()
    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_col(1)
    table.sfm.toggle_row(0)
    table._apply_sfm_highlights()
    table.reverse_columns()
    table._cycle_sort_col(0)
    table._apply_sfm_highlights()
    process()
    selected_anchor = section_image(table.horizontalHeader(), 1)
    assert count_pixels_close(selected_anchor, PALETTE["rare_gold"]) > 120
    assert count_pixels_close(selected_anchor, PALETTE["heaven_cyan"], tolerance=45) > 30

    table.toggle_sfm()  # compact
    process()
    assert table.sfm.state == "compact"
    table.toggle_sfm()  # full restore
    process()
    assert table.sfm.state == "normal"
    assert table.cornerWidget() is None or table.cornerWidget().isVisible() is not False


def test_logical_separator_resolution_tracks_survival_highscores_and_kill_counts_boundaries():
    assert resolve_logical_separators(["C0", "C1", "Totals"], [LogicalSeparator(before="Totals")]) == {1}
    assert resolve_logical_separators(["Totals", "C16", "C15"], [LogicalSeparator(after="Totals")]) == {0}
    assert resolve_logical_separators(["Death", "Win+", "Eden", "Amon", "Primal Death", "Top Floor Beaten"], [LogicalSeparator(before="Top Floor Beaten")]) == {4}
    sep = LogicalSeparator(left=("Death Kills", "Win+ Kills"), right=("Eden Kills", "Amon Kills", "Primal Death Kills"))
    assert resolve_logical_separators(["Class", "ALL Death Kills", "ALL Win+ Kills", "ALL Eden Kills", "ALL Amon Kills"], [sep]) == {2}
    assert resolve_logical_separators(["Class", "ALL Amon Kills", "ALL Eden Kills", "ALL Win+ Kills", "ALL Death Kills"], [sep]) == {2}


def test_column_order_keeps_protected_headers_while_reversing_repeatably():
    headers = ["C0", "C1", "C2", "Totals"]
    reversed_once = [headers[i] for i in column_order(headers, True, trailing=("Totals",))]
    assert reversed_once == ["C2", "C1", "C0", "Totals"]
    reversed_twice = [reversed_once[i] for i in column_order(reversed_once, True, trailing=("Totals",))]
    assert reversed_twice == headers
    count_headers = ["Class", "Death", "Win+", "Eden"]
    assert [count_headers[i] for i in column_order(count_headers, True, leading=("Class",))] == ["Class", "Eden", "Win+", "Death"]


def test_compact_screenshot_titles_are_large_bold_and_dynamic():
    table = build_table()
    label = QLabel()
    table.set_compact_title_label(label, "📊 BARBARIAN DEATHS 📊", color=PALETTE["rare_gold"])
    table.sfm.press(auto_select_first_col=False)
    table.sfm.toggle_col(0)
    table.sfm.toggle_row(0)
    table.toggle_sfm()
    process()
    assert label.text() == "📊 BARBARIAN DEATHS 📊"
    assert label.isVisible()
    assert label.font().bold()
    assert label.font().pointSize() >= 20
    assert "text-align: center" in label.styleSheet()
    table.toggle_sfm()
    process()
    assert not label.isVisible()
