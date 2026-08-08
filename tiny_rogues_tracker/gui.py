from __future__ import annotations

import sys
from pathlib import Path

from . import APP_NAME, __version__
from .core import (
    CinderSelection,
    completion_totals,
    matrix_presentation,
    SfmTableState,
    analyze_save,
    choose_default_save,
    cinder_selection_from_click,
    discover_save_files,
    export_csv,
    format_cinder,
    load_ids,
    sort_key,
    DEATHS_MODE,
    FLOORS_COMPLETED_MODE,
    view3_frontier_highlights,
    VIEW_CINDER_HIGHSCORES,
    VIEW_KILL_COUNTS,
    VIEW_SURVIVAL_BREAKDOWN,
)
from .updater import UpdateInfo, check_async, check_latest_release, download_and_launch_installer

# User-facing view labels: Cinder Highscores, Kill Counts, Survival Breakdown.
PALETTE = {
    "void_black": "#03030C",
    "midnight_navy": "#080746",
    "electric_blue": "#0908D8",
    "royal_indigo": "#2410A8",
    "deep_violet": "#490B82",
    "castle_purple": "#770B8B",
    "hot_magenta": "#A60A91",
    "heaven_cyan": "#20DCEB",       # Eden/Heaven only
    "heaven_ice": "#BDEBF4",        # Eden/Heaven only
    "moon_white": "#F2F1F4",
    "hell_red": "#E52A24",          # Amon/Hell only
    "flame_orange": "#F26A16",      # Amon/Hell only
    "rare_gold": "#F0D52C",         # best-value highlights only
    "zero": "#77738A",
    "dim_red": "#8B3538",
}

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QAction, QColor, QPen, QPainter
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
        QMenu, QMessageBox, QPushButton, QStackedWidget, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget, QButtonGroup, QStyledItemDelegate, QStyleOptionViewItem,
    )
except Exception:  # pragma: no cover
    Qt = QTimer = QAction = QColor = QPen = QPainter = QApplication = QFileDialog = QGridLayout = QHBoxLayout = QHeaderView = QLabel = QMainWindow = QMenu = QMessageBox = QPushButton = QStackedWidget = QTableWidget = QTableWidgetItem = QVBoxLayout = QWidget = QButtonGroup = QStyledItemDelegate = QStyleOptionViewItem = None


class ColumnDividerDelegate(QStyledItemDelegate):
    """Paint a strong shared border after one logical column without modifying cell text."""
    def __init__(self, divider_column: int | None = None, parent=None):
        super().__init__(parent)
        self.divider_column = divider_column

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        super().paint(painter, option, index)
        if self.divider_column is not None and index.column() == self.divider_column:
            painter.save()
            painter.setPen(QPen(QColor(PALETTE['rare_gold']), 3))
            painter.drawLine(option.rect.topRight(), option.rect.bottomRight())
            painter.restore()


class SortableTable(QTableWidget):
    """QTableWidget with numeric stable sort and SFM row/column selection."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.sort_column: int | None = None
        self.sort_direction = 0  # 0 default, 1 descending, 2 ascending
        self.base_headers: list[str] = []
        self.default_snapshot: list[list[QTableWidgetItem]] = []
        self.default_vertical_headers: list[str] = []
        self.default_widths: list[int] = []
        self.default_heights: list[int] = []
        self.compact_snapshot: list[list[QTableWidgetItem]] = []
        self.compact_headers: list[str] = []
        self.compact_vertical_headers: list[str] = []
        self.compact_widths: list[int] = []
        self.compact_heights: list[int] = []
        self.pinned_rows = 0
        self.fixed_bottom_rows = 0
        self.row_order_reversed = False
        self.column_order_reversed = False
        self.auto_select_first_col = True
        self.separator_after_column: int | None = None
        self.divider_delegate = ColumnDividerDelegate(None, self)
        self.setItemDelegate(self.divider_delegate)
        self.sfm = SfmTableState()
        self.sfm_button = None
        self.sfm_exit_button = None
        self.sfm_label = None
        self.scroll_row = 0
        self.scroll_col = 0
        self.setSortingEnabled(False)
        self.horizontalHeader().sectionClicked.connect(self._header_clicked)
        self.verticalHeader().sectionClicked.connect(self._row_header_clicked)
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._header_menu)
        self.verticalHeader().setVisible(True)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(False)

    def set_sfm_controls(self, button, label, exit_button=None):
        self.sfm_button = button
        self.sfm_label = label
        self.sfm_exit_button = exit_button
        if self.sfm_exit_button:
            self.sfm_exit_button.clicked.connect(self.exit_sfm_selection)
        self._sync_sfm_controls()

    def set_corner_controls(self, *buttons):
        corner = QWidget(self)
        layout = QHBoxLayout(corner)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(2)
        for button in buttons:
            button.setParent(corner)
            button.setFixedSize(28, 24)
            layout.addWidget(button)
        layout.addStretch(1)
        self.setCornerWidget(corner)

    def finalize_default_order(self):
        self.base_headers = [self.horizontalHeaderItem(c).text().replace(" ▲", "").replace(" ▼", "") for c in range(self.columnCount())]
        self.default_vertical_headers = [self.verticalHeaderItem(r).text() if self.verticalHeaderItem(r) else str(r + 1) for r in range(self.rowCount())]
        self.default_snapshot = []
        self.default_widths = [self.columnWidth(c) for c in range(self.columnCount())]
        self.default_heights = [self.rowHeight(r) for r in range(self.rowCount())]
        for r in range(self.rowCount()):
            self.default_snapshot.append([self.item(r, c).clone() if self.item(r, c) else QTableWidgetItem("") for c in range(self.columnCount())])
        self._apply_header_indicators()
        self._apply_separator()
        self._restore_table_geometry(self.default_widths, self.default_heights)

    def _header_clicked(self, column: int):
        if self.sfm.state == "selection":
            self.sfm.toggle_col(column, bool(QApplication.keyboardModifiers() & Qt.ShiftModifier))
            self._apply_sfm_highlights()
            return
        if self.sfm.state not in ("normal", "compact"):
            return
        self._cycle_sort_col(column)

    def _cycle_sort_col(self, visible_column: int):
        if visible_column < 0 or visible_column >= self.columnCount():
            return
        column = self._source_column_for_visible(visible_column)
        if self.sort_column != column:
            self.sort_column = column
            self.sort_direction = 1
        else:
            self.sort_direction = {1: 2, 2: 0, 0: 1}[self.sort_direction]
        self.apply_sort()

    def _source_column_for_visible(self, visible_column: int) -> int:
        if self.sfm.state == "compact":
            return visible_column
        header_item = self.horizontalHeaderItem(visible_column)
        header = self._clean_header_text(header_item.text()) if header_item else ""
        if header in self.base_headers:
            return self.base_headers.index(header)
        return visible_column

    def _visible_column_for_source(self, source_column: int) -> int | None:
        source_headers = self.compact_headers if self.sfm.state == "compact" and self.compact_headers else self.base_headers
        if source_column < 0 or source_column >= len(source_headers):
            return None
        wanted = source_headers[source_column]
        for c in range(self.columnCount()):
            item = self.horizontalHeaderItem(c)
            if item and self._clean_header_text(item.text()) == wanted:
                return c
        return source_column if source_column < self.columnCount() else None

    def _clean_header_text(self, text: str) -> str:
        return text.replace(" ▲", "").replace(" ▼", "")

    def _row_header_clicked(self, row: int):
        if self.sfm.state == "selection":
            self.sfm.toggle_row(row, bool(QApplication.keyboardModifiers() & Qt.ShiftModifier))
            self._apply_sfm_highlights()

    def _header_menu(self, pos):
        if self.sfm.state not in ("normal", "compact"):
            return
        col = self.horizontalHeader().logicalIndexAt(pos)
        if col < 0 or col >= self.columnCount():
            return
        menu = QMenu(self)
        action = QAction("Sort descending / Sort ascending / Restore default order", menu)
        action.triggered.connect(lambda _=False: self._cycle_sort_col(col))
        menu.addAction(action)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _explicit_sort(self, col, direction):
        if col is None or col < 0 or col >= self.columnCount():
            return
        self.sort_column = self._source_column_for_visible(col)
        self.sort_direction = direction
        self.apply_sort()

    def _row_sort_value(self, row_items, col):
        if col is None or col < 0 or col >= len(row_items):
            return sort_key(None)
        item = row_items[col]
        value = item.data(Qt.UserRole)
        return sort_key(value if value is not None else item.text())

    def apply_sort(self):
        if not self.default_snapshot:
            self.finalize_default_order()
        compact = self.sfm.state == "compact"
        source = self.compact_snapshot if compact else self.default_snapshot
        vheaders = self.compact_vertical_headers if compact else self.default_vertical_headers
        headers = self.compact_headers if compact else self.base_headers
        widths = self.compact_widths if compact else self.default_widths
        bottom_start = max(self.pinned_rows, len(source) - self.fixed_bottom_rows) if not compact and self.fixed_bottom_rows else len(source)
        pinned = [(i, row, vheaders[i]) for i, row in enumerate(source[:self.pinned_rows])] if not compact else []
        bottom = [(i, row, vheaders[i]) for i, row in enumerate(source[bottom_start:], start=bottom_start)] if not compact and self.fixed_bottom_rows else []
        sortable_source = source[self.pinned_rows:bottom_start] if not compact else source
        indexed = [(i, row, vheaders[i]) for i, row in enumerate(sortable_source, start=(0 if compact else self.pinned_rows))]
        if self.sort_direction != 0 and self.sort_column is not None:
            reverse = self.sort_direction == 1
            indexed.sort(key=lambda x: (self._row_sort_value(x[1], self.sort_column), x[0]), reverse=reverse)
            # Restore stable default ordering for ties after reversing primary value.
            from itertools import groupby
            grouped = []
            for _, group in groupby(indexed, key=lambda x: self._row_sort_value(x[1], self.sort_column)):
                tie = sorted(list(group), key=lambda x: x[0])
                grouped.extend(tie)
            if reverse:
                keys = sorted({self._row_sort_value(row, self.sort_column) for _, row, _ in indexed}, reverse=True)
                order = []
                for k in keys:
                    order.extend([x for x in grouped if self._row_sort_value(x[1], self.sort_column) == k])
                indexed = order
        else:
            indexed.sort(key=lambda x: x[0])
        if self.row_order_reversed and self.sort_direction == 0:
            indexed = list(reversed(indexed))
        if self.column_order_reversed:
            headers, widths, indexed, bottom, pinned = self._reverse_columns(headers, widths, indexed, bottom, pinned)
        self._load_snapshot(pinned + indexed + bottom, headers, widths)
        self._apply_header_indicators()
        self._apply_separator()

    def _load_snapshot(self, indexed, headers: list[str], widths: list[int]):
        self.clearContents()
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setRowCount(len(indexed))
        self.setVerticalHeaderLabels([h.replace(" [SFM]", "") for _, _, h in indexed])
        for r, (_, row, _) in enumerate(indexed):
            for c, item in enumerate(row):
                self.setItem(r, c, item.clone())
        self._restore_table_geometry(widths, self.compact_heights if self.sfm.state == "compact" else self.default_heights)

    def _reverse_columns(self, headers, widths, *groups):
        start = 1 if headers and headers[0] == "Class" else 0
        order = list(range(start)) + list(reversed(range(start, len(headers))))
        headers = [headers[i] for i in order]
        widths = [widths[i] for i in order]
        out_groups = []
        for group in groups:
            out_groups.append([(i, [row[j] for j in order], vh) for i, row, vh in group])
        return (headers, widths, *out_groups)

    def _restore_table_geometry(self, widths, heights):
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(False)
        for c, width in enumerate(widths):
            if width > 0 and c < self.columnCount():
                self.setColumnWidth(c, width)
        for r, height in enumerate(heights):
            if height > 0 and r < self.rowCount():
                self.setRowHeight(r, height)

    def reverse_columns(self):
        self.column_order_reversed = not self.column_order_reversed
        self.apply_sort()

    def reverse_rows(self):
        self.row_order_reversed = not self.row_order_reversed
        self.apply_sort()

    def _apply_header_indicators(self):
        visible_sort_col = self._visible_column_for_source(self.sort_column) if self.sort_column is not None else None
        for c in range(self.columnCount()):
            item = self.horizontalHeaderItem(c)
            text = self._clean_header_text(item.text()) if item else str(c + 1)
            suffix = ""
            if c == visible_sort_col:
                suffix = " ▼" if self.sort_direction == 1 else (" ▲" if self.sort_direction == 2 else "")
            header = QTableWidgetItem(text + suffix)
            if "Eden" in text:
                header.setForeground(QColor(PALETTE['heaven_cyan']))
            elif "Amon" in text:
                header.setForeground(QColor(PALETTE['flame_orange']))
            self.setHorizontalHeaderItem(c, header)

    def toggle_sfm(self):
        previous = self.sfm.state
        if previous == "normal":
            self.scroll_row = self.rowAt(0)
            self.scroll_col = self.columnAt(0)
        self.sfm.press(auto_select_first_col=self.auto_select_first_col)
        if previous == "selection" and self.sfm.state == "compact":
            self._collapse_to_sfm_compact()
        elif previous == "compact" and self.sfm.state == "normal":
            self.sort_column = None
            self.sort_direction = 0
            self.compact_snapshot = []
            self.compact_headers = []
            self.compact_vertical_headers = []
            self.compact_widths = []
            self.compact_heights = []
            self.apply_sort()
            if self.scroll_row >= 0:
                self.scrollToItem(self.item(min(self.scroll_row, max(0, self.rowCount() - 1)), 0))
        self._sync_sfm_controls()
        self._apply_sfm_highlights()

    def _sync_sfm_controls(self):
        if self.sfm_label:
            self.sfm_label.setText(self.sfm.message)
            if self.sfm.state == "selection":
                self.sfm_label.setStyleSheet(f"font-weight: bold; color: {PALETTE['rare_gold']};")
            else:
                self.sfm_label.setStyleSheet("")
        if self.sfm_button:
            self.sfm_button.setText({"normal": "SFM", "selection": "Create compact SFM", "compact": "Exit SFM"}[self.sfm.state])
            self.sfm_button.setChecked(self.sfm.state != "normal")
        if self.sfm_exit_button:
            self.sfm_exit_button.setVisible(self.sfm.state == "selection")
        if self.sfm.state == "selection":
            self.setStyleSheet(f"QTableWidget {{ border: 3px solid {PALETTE['rare_gold']}; }}")
        else:
            self.setStyleSheet("")

    def _apply_sfm_highlights(self):
        selected_cells = self.sfm.highlighted_cells()
        self._clear_sfm_header_marks()
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if not item:
                    continue
                item.setBackground(QColor())
                if (r, c) in selected_cells:
                    item.setBackground(QColor(PALETTE['deep_violet']))
        # SFM selection uses styling/tooltip state only; header text is never mutated.
        if self.sfm.state == "selection":
            for c in range(self.columnCount()):
                header = self.horizontalHeaderItem(c) or QTableWidgetItem(str(c + 1))
                if c in self.sfm.selected_cols:
                    header.setBackground(QColor(PALETTE['deep_violet']))
                if c == self.sfm.col_anchor:
                    header.setToolTip("SFM column range anchor")
                    header.setForeground(QColor(PALETTE['rare_gold']))
                self.setHorizontalHeaderItem(c, header)
            for r in range(self.rowCount()):
                header = self.verticalHeaderItem(r) or QTableWidgetItem(str(r + 1))
                if r in self.sfm.selected_rows:
                    header.setBackground(QColor(PALETTE['deep_violet']))
                if r == self.sfm.row_anchor:
                    header.setToolTip("SFM row range anchor")
                    header.setForeground(QColor(PALETTE['rare_gold']))
                self.setVerticalHeaderItem(r, header)

    def _clear_sfm_header_marks(self):
        for c in range(self.columnCount()):
            header = self.horizontalHeaderItem(c)
            if not header:
                continue
            header.setBackground(QColor())
            header.setToolTip("")
        for r in range(self.rowCount()):
            header = self.verticalHeaderItem(r)
            if not header:
                continue
            header.setBackground(QColor())
            header.setForeground(QColor())
            header.setToolTip("")

    def exit_sfm_selection(self):
        if self.sfm.state == "selection":
            self.sfm.exit_to_normal()
            self._sync_sfm_controls()
            self._apply_header_indicators()
            self._apply_sfm_highlights()

    def _collapse_to_sfm_compact(self):
        rows = sorted(self.sfm.selected_rows)
        cols = sorted(self.sfm.selected_cols)
        self.compact_headers = [self._clean_header_text(self.horizontalHeaderItem(c).text()) if self.horizontalHeaderItem(c) else str(c + 1) for c in cols]
        self.compact_vertical_headers = [self.verticalHeaderItem(r).text().replace(" [SFM]", "") if self.verticalHeaderItem(r) else str(r + 1) for r in rows]
        self.compact_snapshot = [[self.item(r, c).clone() if self.item(r, c) else QTableWidgetItem("") for c in cols] for r in rows]
        self.compact_widths = [self.columnWidth(c) for c in cols]
        self.compact_heights = [self.rowHeight(r) for r in rows]
        self.sort_column = None
        self.sort_direction = 0
        data = self.compact_snapshot
        headers = self.compact_headers
        vheaders = self.compact_vertical_headers
        self.clear()
        self.setRowCount(len(data)); self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers); self.setVerticalHeaderLabels(vheaders)
        for r, row in enumerate(data):
            for c, item in enumerate(row):
                self.setItem(r, c, item)
        self._restore_table_geometry(self.compact_widths, self.compact_heights)
        self._fit_compact_geometry()

    def _fit_compact_geometry(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        for c in range(self.columnCount()):
            self.setColumnWidth(c, min(max(self.columnWidth(c), 48), 140))
        for r in range(self.rowCount()):
            self.setRowHeight(r, min(max(self.rowHeight(r), 22), 32))
        self.compact_widths = [self.columnWidth(c) for c in range(self.columnCount())]
        self.compact_heights = [self.rowHeight(r) for r in range(self.rowCount())]

    def _apply_survival_geometry(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        for c in range(self.columnCount()):
            header = self.horizontalHeaderItem(c)
            is_total = header and self._clean_header_text(header.text()) == "Totals"
            minimum = 60 if is_total else 48
            maximum = 92 if is_total else 78
            self.setColumnWidth(c, min(max(self.columnWidth(c), minimum), maximum))
        self.verticalHeader().setMinimumWidth(150)
        for r in range(self.rowCount()):
            self.setRowHeight(r, min(max(self.rowHeight(r), 22), 32))

    def _apply_separator(self):
        if self.separator_after_column is None:
            return
        left_name = self.base_headers[self.separator_after_column] if self.separator_after_column < len(self.base_headers) else None
        visible_headers = [self.horizontalHeaderItem(c).text().replace(" ▲", "").replace(" ▼", "") for c in range(self.columnCount())]
        if left_name not in visible_headers:
            return
        c = visible_headers.index(left_name)
        self.divider_delegate.divider_column = c
        self.viewport().update()



def zero_value(val) -> bool:
    return val in (0, "0", "0%", "—")


class TrackerApp(QMainWindow):
    def __init__(self, ids_path: str | Path | None = None, save_path: str | Path | None = None):
        super().__init__()
        if QApplication is None:
            raise RuntimeError("PySide6 is required to run the desktop GUI. Install with: py -m pip install PySide6")
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.resize(1180, 760)
        self.ids_path = Path(ids_path or Path.cwd() / "ids.json")
        self.ids = load_ids(self.ids_path)
        self.save_path = Path(save_path) if save_path else choose_default_save(discover_save_files(), self.ids)
        self.model = None
        self.current_selection = CinderSelection.all()
        self.cinder_anchor: int | None = None
        self.update_check_started = False
        self.pending_update_result: tuple[UpdateInfo | None, Exception | None] | None = None
        self.update_result_timer = QTimer(self)
        self.update_result_timer.setInterval(250)
        self.update_result_timer.timeout.connect(self._drain_update_result)
        self.show_totals = False
        self.survival_mode = DEATHS_MODE
        self.survival_picker_widget = None
        self.page_parents = {}
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._apply_style()
        self._load_model()
        self._build_home()
        QTimer.singleShot(0, self._check_updates)

    def _apply_style(self):
        self.setStyleSheet(f"""
        QMainWindow, QWidget {{ background: {PALETTE['void_black']}; color: {PALETTE['moon_white']}; font-size: 13px; }}
        QPushButton {{ background: {PALETTE['royal_indigo']}; border: 1px solid {PALETTE['castle_purple']}; padding: 8px; border-radius: 5px; }}
        QPushButton#PrimaryAction {{ background: {PALETTE['royal_indigo']}; border: 2px solid {PALETTE['hot_magenta']}; padding: 14px; border-radius: 7px; font-size: 17px; font-weight: bold; }}
        QPushButton#UtilityAction {{ background: {PALETTE['midnight_navy']}; border: 1px solid {PALETTE['deep_violet']}; color: {PALETTE['zero']}; padding: 7px; border-radius: 5px; font-size: 12px; }}
        QPushButton#ClassGridButton {{ background: {PALETTE['midnight_navy']}; border: 1px solid {PALETTE['castle_purple']}; padding: 10px; border-radius: 6px; min-width: 145px; min-height: 48px; text-align: left; }}
        QLabel#SectionLabel {{ font-size: 15px; font-weight: bold; color: {PALETTE['heaven_ice']}; margin-top: 12px; }}
        QPushButton:hover {{ border: 1px solid {PALETTE['moon_white']}; }}
        QPushButton:checked {{ background: {PALETTE['rare_gold']}; color: {PALETTE['void_black']}; border: 2px solid {PALETTE['moon_white']}; font-weight: bold; }}
        QPushButton[sfmAnchor="true"] {{ border: 2px dashed {PALETTE['heaven_ice']}; }}
        QTableWidget {{ background: {PALETTE['midnight_navy']}; alternate-background-color: {PALETTE['void_black']}; gridline-color: {PALETTE['deep_violet']}; }}
        QHeaderView::section {{ background: {PALETTE['royal_indigo']}; color: {PALETTE['moon_white']}; padding: 5px; }}
        QLabel#Title {{ font-size: 28px; font-weight: bold; color: {PALETTE['moon_white']}; }}
        """)

    def _load_model(self):
        if self.save_path and self.save_path.exists():
            import json
            self.model = analyze_save(json.loads(self.save_path.read_text(encoding="utf-8")), self.ids)

    def _go_home(self):
        self.stack.setCurrentIndex(0)

    def _go_back(self):
        current = self.stack.currentWidget()
        parent = self.page_parents.get(current)
        if parent is not None:
            self.stack.setCurrentWidget(parent)
        else:
            self._go_home()

    def nav(self):
        bar = QHBoxLayout()
        back = QPushButton("Back")
        home = QPushButton("Home")
        back.clicked.connect(self._go_back)
        home.clicked.connect(self._go_home)
        bar.addWidget(back); bar.addWidget(home); bar.addStretch(1)
        return bar

    def _page(self, title, back_target=None):
        w = QWidget(); layout = QVBoxLayout(w); layout.addLayout(self.nav())
        self.page_parents[w] = back_target if back_target is not None else (self.stack.widget(0) if self.stack.count() else None)
        lab = QLabel(title); lab.setObjectName("Title"); layout.addWidget(lab)
        return w, layout

    def _section_label(self, text: str):
        label = QLabel(text)
        label.setObjectName("SectionLabel")
        return label

    def _make_home_button(self, text: str, callback, role: str):
        button = QPushButton(text)
        button.setObjectName(role)
        button.clicked.connect(callback)
        return button

    def _build_home(self):
        w = QWidget(); layout = QVBoxLayout(w)
        title = QLabel(f"{APP_NAME} v{__version__}"); title.setObjectName("Title"); layout.addWidget(title)
        layout.addWidget(QLabel("Read-only Tiny Rogues save viewer. Saves are never modified."))
        layout.addWidget(QLabel(f"Loaded save: {self.save_path or 'None found'}"))
        layout.addSpacing(10)
        layout.addWidget(self._section_label("Primary Actions"))
        primary_grid = QGridLayout(); primary_grid.setSpacing(12)
        for col, (label, fn) in enumerate([(VIEW_CINDER_HIGHSCORES, self.show_records), (VIEW_KILL_COUNTS, self.show_counts), (VIEW_SURVIVAL_BREAKDOWN, self.show_matrix_picker)]):
            primary_grid.addWidget(self._make_home_button(label, fn, "PrimaryAction"), 0, col)
        layout.addLayout(primary_grid)
        layout.addSpacing(28)
        layout.addStretch(1)
        layout.addWidget(self._section_label("Utility Actions"))
        utility_grid = QGridLayout(); utility_grid.setSpacing(8)
        utilities = [
            ("Browse / Reload Save", self._browse_save),
            ("Check for Updates", self.manual_check_for_updates),
            ("Export CSV", self._export),
        ]
        for col, (label, fn) in enumerate(utilities):
            utility_grid.addWidget(self._make_home_button(label, fn, "UtilityAction"), 0, col)
        layout.addLayout(utility_grid)
        self.stack.addWidget(w)

    def _browse_save(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Tiny Rogues save", str(Path.home()), "Tiny Rogues saves (Public_Slot*_Save*.json);;JSON (*.json)")
        if path:
            self.save_path = Path(path); self._load_model(); QMessageBox.information(self, "Loaded", str(self.save_path))

    def _export(self):
        if not self.model: return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "tiny_rogues_report.csv", "CSV (*.csv)")
        if path:
            export_csv(self.model, path, self.current_selection); QMessageBox.information(self, "Exported", path)

    def _table_page(self, title, back_target=None):
        w, layout = self._page(title, back_target=back_target)
        top = QHBoxLayout(); sfm = QPushButton("SFM"); sfm.setCheckable(True); x_sfm = QPushButton("X"); x_sfm.setToolTip("Exit SFM selection without creating a mini-table"); x_sfm.setVisible(False); expl = QLabel("SFM inactive. Press SFM to choose rows and columns for a compact screenshot table.")
        top.addWidget(expl); top.addStretch(1); top.addWidget(sfm); top.addWidget(x_sfm); layout.addLayout(top)
        table = SortableTable(title); table.set_sfm_controls(sfm, expl, x_sfm); sfm.clicked.connect(table.toggle_sfm); layout.addWidget(table)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)
        return table

    def _style_item(self, item, val, gold=False, route=None, numeric_score=False, top_floor_neutral=False):
        if gold and not zero_value(val):
            item.setForeground(QColor(PALETTE['rare_gold']))
            return
        if zero_value(val):
            item.setForeground(QColor(PALETTE['dim_red'] if numeric_score and str(val) == "0" else PALETTE['zero']))
            return
        if top_floor_neutral:
            item.setForeground(QColor(PALETTE['moon_white']))
            return
        if numeric_score and isinstance(item.data(Qt.UserRole), (int, float)):
            item.setForeground(QColor(PALETTE['hell_red']))
            return
        if route == "eden":
            item.setForeground(QColor(PALETTE['heaven_cyan']))
        elif route == "amon":
            item.setForeground(QColor(PALETTE['flame_orange']))

    def _style_route_headers(self, table):
        for c in range(table.columnCount()):
            item = table.horizontalHeaderItem(c)
            if not item:
                continue
            text = item.text()
            if "Eden" in text:
                item.setForeground(QColor(PALETTE['heaven_cyan']))
            elif "Amon" in text:
                item.setForeground(QColor(PALETTE['flame_orange']))

    def show_records(self):
        if not self.model: return
        table = self._table_page(VIEW_CINDER_HIGHSCORES)
        headers = ["Class", "Death", "Win+", "Eden", "Amon", "Primal Death", "Top Floor Beaten"]
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); self._style_route_headers(table); table.setRowCount(len(self.model.records))
        gold = self.model.character_record_highlights()
        cols = [None, "best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "top_floor_rank"]
        for r, rec in enumerate(self.model.records):
            vals = [rec.character, format_cinder(rec.best_death), format_cinder(rec.best_win_plus), format_cinder(rec.best_eden), format_cinder(rec.best_amon), format_cinder(rec.best_primal_death), rec.top_floor_label]
            raw = [rec.character, rec.best_death if rec.best_death is not None else -1, rec.best_win_plus if rec.best_win_plus is not None else -1, rec.best_eden if rec.best_eden is not None else -1, rec.best_amon if rec.best_amon is not None else -1, rec.best_primal_death if rec.best_primal_death is not None else -1, rec.top_floor_rank]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(str(val)); item.setData(Qt.UserRole, raw[c]); item.setToolTip(rec.sources.get(cols[c] or "", "RunRecords / CinderStreakHistory"))
                if cols[c] == "top_floor_rank":
                    self._style_item(item, val, gold=bool((rec.character, cols[c]) in gold), numeric_score=True, top_floor_neutral=True)
                else:
                    self._style_item(item, val, gold=bool(cols[c] and (rec.character, cols[c]) in gold), route="eden" if cols[c] == "best_eden" else ("amon" if cols[c] == "best_amon" else None), numeric_score=(c > 0))
                table.setItem(r, c, item)
        table.finalize_default_order()

    def show_counts(self):
        if not self.model: return
        w, layout = self._page(VIEW_KILL_COUNTS)
        filter_label = QLabel(self.current_selection.display_text); layout.addWidget(filter_label)
        layout.addWidget(QLabel("Shift-click another level to select the full range between them."))
        selector = QHBoxLayout(); group = QButtonGroup(w); group.setExclusive(False)
        def add_filter_button(text, value):
            b = QPushButton(text); b.setCheckable(True); b.setObjectName("CinderButton"); b.setChecked((value == "ALL" and self.current_selection.label == "ALL") or (isinstance(value, int) and self.current_selection.low <= value <= self.current_selection.high if self.current_selection.low is not None else False))
            if isinstance(value, int) and value == self.cinder_anchor:
                b.setProperty("sfmAnchor", True)
                b.setToolTip("Cinder range anchor")
            group.addButton(b); selector.addWidget(b)
            def clicked(checked=False, v=value, button=b):
                mods = QApplication.keyboardModifiers()
                self.current_selection, self.cinder_anchor = cinder_selection_from_click(self.current_selection, v, bool(mods & Qt.ShiftModifier), self.cinder_anchor)
                self.show_counts()
            b.clicked.connect(clicked)
        add_filter_button("ALL", "ALL")
        for i in range(1, 17): add_filter_button(str(i), i)
        selector.addStretch(1); layout.addLayout(selector)
        totals_button = QPushButton("Hide Totals" if self.show_totals else "Show Totals")
        totals_button.setObjectName("UtilityAction")
        totals_button.clicked.connect(lambda: self._toggle_totals())
        layout.addWidget(totals_button)
        top = QHBoxLayout(); sfm = QPushButton("SFM"); sfm.setCheckable(True); x_sfm = QPushButton("X"); x_sfm.setToolTip("Exit SFM selection without creating a mini-table"); x_sfm.setVisible(False); expl = QLabel("SFM inactive. Press SFM to choose rows and columns for a compact screenshot table.")
        top.addWidget(expl); top.addStretch(1); top.addWidget(sfm); top.addWidget(x_sfm); layout.addLayout(top)
        table = SortableTable(VIEW_KILL_COUNTS); table.set_sfm_controls(sfm, expl, x_sfm); sfm.clicked.connect(table.toggle_sfm); layout.addWidget(table)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)
        rows = self.model.completion_rows(self.current_selection).rows
        display_rows = ([completion_totals(rows)] if self.show_totals else []) + rows
        prefix = self.current_selection.label
        headers = ["Class", f"{prefix} Death Kills", f"{prefix} Win+ Kills", f"{prefix} Eden Kills", f"{prefix} Amon Kills", f"{prefix} Primal Death Kills"]
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); self._style_route_headers(table); table.setRowCount(len(display_rows))
        table.pinned_rows = 1 if self.show_totals else 0
        table.separator_after_column = 2
        hi = self.model.completion_highlights(self.current_selection)
        fields = [None, "death_clears", "win_plus_clears", "eden_clears", "amon_clears", "primal_death_clears"]
        for r, row in enumerate(display_rows):
            vals = [row.character, row.death_clears, row.win_plus_clears, row.eden_clears, row.amon_clears, row.primal_death_clears]
            raws = [row.character, row.death_clears, row.win_plus_clears, row.eden_clears, row.amon_clears, row.primal_death_clears]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(str(val)); item.setData(Qt.UserRole, raws[c])
                is_total = row.character == "TOTALS"
                if is_total:
                    item.setForeground(QColor(PALETTE['rare_gold']))
                else:
                    self._style_item(item, val, gold=bool(fields[c] and (row.character, fields[c]) in hi), route="eden" if fields[c] == "eden_clears" else ("amon" if fields[c] == "amon_clears" else None))
                if row.inferred_historical_death_runs and c == 1:
                    item.setToolTip("Includes minimum historical Death clear evidence from CinderStreakHistory.")
                table.setItem(r, c, item)
        table.finalize_default_order()

    def _toggle_totals(self):
        self.show_totals = not self.show_totals
        self.show_counts()

    def _class_grid_columns(self) -> int:
        return max(3, min(6, max(1, self.width() // 180)))

    def _set_survival_mode(self, mode: str, deaths_button=None, floors_button=None):
        self.survival_mode = FLOORS_COMPLETED_MODE if mode == FLOORS_COMPLETED_MODE else DEATHS_MODE
        if deaths_button and floors_button:
            deaths_button.setChecked(self.survival_mode == DEATHS_MODE)
            floors_button.setChecked(self.survival_mode == FLOORS_COMPLETED_MODE)

    def show_matrix_picker(self):
        if not self.model: return
        w, layout = self._page(VIEW_SURVIVAL_BREAKDOWN)
        self.survival_picker_widget = w
        mode_row = QHBoxLayout()
        deaths = QPushButton(DEATHS_MODE); deaths.setCheckable(True)
        floors = QPushButton(FLOORS_COMPLETED_MODE); floors.setCheckable(True)
        self._set_survival_mode(self.survival_mode, deaths, floors)
        deaths.clicked.connect(lambda: self._set_survival_mode(DEATHS_MODE, deaths, floors))
        floors.clicked.connect(lambda: self._set_survival_mode(FLOORS_COMPLETED_MODE, deaths, floors))
        mode_row.addWidget(QLabel("Mode:")); mode_row.addWidget(deaths); mode_row.addWidget(floors); mode_row.addStretch(1)
        layout.addLayout(mode_row)
        layout.addWidget(QLabel("ALL classes:"))
        all_button = QPushButton("ALL")
        all_button.setObjectName("ClassGridButton")
        all_button.setMinimumSize(150, 52)
        all_button.clicked.connect(lambda: self.show_matrix("ALL", self.survival_mode))
        layout.addWidget(all_button)
        layout.addWidget(QLabel("Choose a class:"))
        grid = QGridLayout(); grid.setSpacing(8)
        records = sorted(self.model.records, key=lambda r: r.character.lower())
        columns = self._class_grid_columns()
        for index, record in enumerate(records):
            button = QPushButton(f"□  {record.character}")
            button.setObjectName("ClassGridButton")
            button.setMinimumSize(150, 52)
            button.clicked.connect(lambda checked=False, cid=record.character_id: self.show_matrix(cid, self.survival_mode))
            grid.addWidget(button, index // columns, index % columns)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)

    def show_matrix(self, cid, mode=DEATHS_MODE):
        matrix = self.model.matrix_for_character(cid, mode)
        table = self._table_page(VIEW_SURVIVAL_BREAKDOWN, back_target=self.survival_picker_widget)
        table.auto_select_first_col = False
        layout = table.parentWidget().layout()
        switch = QHBoxLayout()
        reverse_cols = QPushButton("↔"); reverse_cols.setToolTip("Reverse cinder column order")
        reverse_rows = QPushButton("↕"); reverse_rows.setToolTip("Reverse Survival Breakdown row order; fixed rate rows stay at the bottom")
        reverse_cols.clicked.connect(table.reverse_columns); reverse_rows.clicked.connect(table.reverse_rows)
        table.set_corner_controls(reverse_cols, reverse_rows)
        deaths = QPushButton(DEATHS_MODE); deaths.setCheckable(True); deaths.setChecked(matrix.mode == DEATHS_MODE)
        floors = QPushButton(FLOORS_COMPLETED_MODE); floors.setCheckable(True); floors.setChecked(matrix.mode == FLOORS_COMPLETED_MODE)
        deaths.clicked.connect(lambda: self.show_matrix(cid, DEATHS_MODE))
        floors.clicked.connect(lambda: self.show_matrix(cid, FLOORS_COMPLETED_MODE))
        switch.addWidget(QLabel("Mode:")); switch.addWidget(deaths); switch.addWidget(floors); switch.addStretch(1)
        layout.insertLayout(2, switch)
        context = QLabel(f"Class selected: {matrix.character}\nMode: {matrix.mode}")
        context.setObjectName("SfmContext")
        layout.insertWidget(4, context)
        presentation = matrix_presentation(matrix)
        table.setColumnCount(len(presentation.headers)); table.setHorizontalHeaderLabels(presentation.headers)
        table.setRowCount(len(presentation.row_labels)); table.setVerticalHeaderLabels(presentation.row_labels)
        table.fixed_bottom_rows = presentation.fixed_bottom_rows
        hi = view3_frontier_highlights(matrix)
        for r, row_label in enumerate(presentation.row_labels):
            for c, value in enumerate(presentation.values[r]):
                item = QTableWidgetItem(str(value)); item.setData(Qt.UserRole, value if isinstance(value, int) else -1)
                item.setToolTip(f"{matrix.character}; {matrix.mode}; {row_label}; {presentation.headers[c]}; value {value}")
                raw_cinder = matrix.cinders[c] if c < len(matrix.cinders) else None
                self._style_item(item, value, gold=(raw_cinder, row_label) in hi if isinstance(raw_cinder, int) else False)
                table.setItem(r, c, item)
        table._apply_survival_geometry()
        table.finalize_default_order()

    def _check_updates(self):
        """Run the normal startup update check once per launch without blocking startup."""
        if self.update_check_started:
            return
        self.update_check_started = True
        self.pending_update_result = None
        self.update_result_timer.start()
        def done(info: UpdateInfo | None, err: Exception | None):
            # Worker-thread callback: store only. The GUI thread drains this via QTimer.
            # Context-free QTimer.singleShot from a Python worker can bind to the worker
            # thread with no Qt event loop, which drops the startup prompt silently.
            self.pending_update_result = (info, err)
        check_async(done)

    def _drain_update_result(self):
        result = self.pending_update_result
        if result is None:
            return
        self.update_result_timer.stop()
        self.pending_update_result = None
        info, err = result
        if info:
            self._offer_update(info, manual=False)
        elif err:
            self.statusBar().showMessage(f"Update check failed; running current version. {err}", 8000)

    def manual_check_for_updates(self):
        """Visible manual Check for updates action using the same installer path."""
        try:
            info = check_latest_release()
        except Exception as exc:
            QMessageBox.information(self, "Update check failed", f"Could not check for updates. The current version will keep running.\n\n{exc}")
            return
        if info:
            self._offer_update(info, manual=True)
        else:
            QMessageBox.information(self, "Tiny Rogues Tracker is up to date", f"Installed version: {__version__}\nNo newer public release was found.")

    def _offer_update(self, info: UpdateInfo, manual: bool = False):
        box = QMessageBox(self)
        box.setWindowTitle("Tiny Rogues Tracker update available")
        box.setIcon(QMessageBox.Information)
        box.setText(f"Update available: {info.current_version} → {info.latest_version}")
        details = [f"Installed version: {info.current_version}", f"Available version: {info.latest_version}"]
        if info.summary:
            details.append("")
            details.append(info.summary)
        if info.html_url:
            details.append("")
            details.append(info.html_url)
        if not info.asset_url:
            details.append("")
            details.append("No Windows installer asset was found; this update cannot be installed automatically yet.")
        box.setInformativeText("\n".join(details))
        update_button = box.addButton("Update now", QMessageBox.AcceptRole)
        skip_button = box.addButton("Skip for now", QMessageBox.RejectRole)
        box.setDefaultButton(update_button if info.asset_url else skip_button)
        box.exec()
        if box.clickedButton() != update_button or not info.asset_url:
            return
        try:
            download_and_launch_installer(info)
        except Exception as exc:
            QMessageBox.information(self, "Update failed", f"The update could not be installed automatically. The current version will keep running.\n\n{exc}")
            return
        QApplication.quit()


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    app = QApplication(argv)
    win = TrackerApp()
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
