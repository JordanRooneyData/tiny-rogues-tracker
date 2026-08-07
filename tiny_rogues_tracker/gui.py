from __future__ import annotations

import sys
from pathlib import Path

from . import APP_NAME, __version__
from .core import (
    CinderSelection,
    SfmTableState,
    analyze_save,
    choose_default_save,
    cinder_selection_from_click,
    discover_save_files,
    export_csv,
    format_cinder,
    format_rate,
    load_ids,
    sort_key,
    view3_frontier_highlights,
    VIEW_CINDER_HIGHSCORES,
    VIEW_KILL_COUNTS,
    VIEW_CLASS_BREAKDOWN,
)
from .updater import check_async, download_and_launch_installer

# User-facing view labels: Cinder Highscores, Kill Counts, Class Breakdown.
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
}

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QAction, QColor
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
        QMenu, QMessageBox, QPushButton, QStackedWidget, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget, QComboBox, QButtonGroup,
    )
except Exception:  # pragma: no cover
    Qt = QTimer = QAction = QColor = QApplication = QFileDialog = QHBoxLayout = QHeaderView = QLabel = QMainWindow = QMenu = QMessageBox = QPushButton = QStackedWidget = QTableWidget = QTableWidgetItem = QVBoxLayout = QWidget = QComboBox = QButtonGroup = None


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
        self.sfm = SfmTableState()
        self.sfm_button = None
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

    def set_sfm_controls(self, button, label):
        self.sfm_button = button
        self.sfm_label = label
        self._sync_sfm_controls()

    def finalize_default_order(self):
        self.base_headers = [self.horizontalHeaderItem(c).text().replace(" ▲", "").replace(" ▼", "") for c in range(self.columnCount())]
        self.default_vertical_headers = [self.verticalHeaderItem(r).text() if self.verticalHeaderItem(r) else str(r + 1) for r in range(self.rowCount())]
        self.default_snapshot = []
        for r in range(self.rowCount()):
            self.default_snapshot.append([self.item(r, c).clone() if self.item(r, c) else QTableWidgetItem("") for c in range(self.columnCount())])
        self._apply_header_indicators()
        self.resizeColumnsToContents()

    def _header_clicked(self, column: int):
        if self.sfm.state == "selection":
            self.sfm.toggle_col(column)
            self._apply_sfm_highlights()
            return
        if self.sfm.state != "normal":
            return
        if self.sort_column != column:
            self.sort_column = column
            self.sort_direction = 1
        else:
            self.sort_direction = {1: 2, 2: 0, 0: 1}[self.sort_direction]
        self.apply_sort()

    def _row_header_clicked(self, row: int):
        if self.sfm.state == "selection":
            self.sfm.toggle_row(row)
            self._apply_sfm_highlights()

    def _header_menu(self, pos):
        if self.sfm.state != "normal":
            return
        col = self.horizontalHeader().logicalIndexAt(pos)
        menu = QMenu(self)
        for label, direction in [("Sort descending", 1), ("Sort ascending", 2), ("Restore default order", 0)]:
            action = QAction(label, self)
            action.triggered.connect(lambda _=False, d=direction: self._explicit_sort(col, d))
            menu.addAction(action)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _explicit_sort(self, col, direction):
        self.sort_column = col
        self.sort_direction = direction
        self.apply_sort()

    def _row_sort_value(self, row_items, col):
        item = row_items[col]
        value = item.data(Qt.UserRole)
        return sort_key(value if value is not None else item.text())

    def apply_sort(self):
        if not self.default_snapshot:
            self.finalize_default_order()
        indexed = [(i, row, self.default_vertical_headers[i]) for i, row in enumerate(self.default_snapshot)]
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
        self._load_snapshot(indexed)
        self._apply_header_indicators()

    def _load_snapshot(self, indexed):
        self.clearContents()
        self.setRowCount(len(indexed))
        self.setVerticalHeaderLabels([h for _, _, h in indexed])
        for r, (_, row, _) in enumerate(indexed):
            for c, item in enumerate(row):
                self.setItem(r, c, item.clone())

    def _apply_header_indicators(self):
        for c, text in enumerate(self.base_headers or [self.horizontalHeaderItem(i).text() for i in range(self.columnCount())]):
            suffix = ""
            if c == self.sort_column:
                suffix = " ▼" if self.sort_direction == 1 else (" ▲" if self.sort_direction == 2 else "")
            self.setHorizontalHeaderItem(c, QTableWidgetItem(text + suffix))

    def toggle_sfm(self):
        previous = self.sfm.state
        if previous == "normal":
            self.scroll_row = self.rowAt(0)
            self.scroll_col = self.columnAt(0)
        self.sfm.press()
        if previous == "selection" and self.sfm.state == "compact":
            self._collapse_to_sfm_compact()
        elif previous == "compact" and self.sfm.state == "normal":
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
        if self.sfm.state == "selection":
            self.setStyleSheet(f"QTableWidget {{ border: 3px solid {PALETTE['rare_gold']}; }}")
        else:
            self.setStyleSheet("")

    def _apply_sfm_highlights(self):
        selected_cells = self.sfm.highlighted_cells()
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item and (r, c) in selected_cells:
                    item.setBackground(QColor(PALETTE['deep_violet']))
        # Header selections remain reversible and visible through header text markers.
        if self.sfm.state == "selection":
            for c in range(self.columnCount()):
                base = (self.base_headers[c] if c < len(self.base_headers) else self.horizontalHeaderItem(c).text()).replace(" [SFM]", "")
                self.setHorizontalHeaderItem(c, QTableWidgetItem(base + (" [SFM]" if c in self.sfm.selected_cols else "")))
            for r in range(self.rowCount()):
                item = self.verticalHeaderItem(r) or QTableWidgetItem(str(r + 1))
                base = item.text().replace(" [SFM]", "")
                self.setVerticalHeaderItem(r, QTableWidgetItem(base + (" [SFM]" if r in self.sfm.selected_rows else "")))

    def _collapse_to_sfm_compact(self):
        rows = sorted(self.sfm.selected_rows)
        cols = sorted(self.sfm.selected_cols)
        data = [[self.item(r, c).clone() if self.item(r, c) else QTableWidgetItem("") for c in cols] for r in rows]
        headers = [self.base_headers[c] for c in cols]
        vheaders = [self.verticalHeaderItem(r).text().replace(" [SFM]", "") if self.verticalHeaderItem(r) else str(r + 1) for r in rows]
        self.clear()
        self.setRowCount(len(data)); self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers); self.setVerticalHeaderLabels(vheaders)
        for r, row in enumerate(data):
            for c, item in enumerate(row):
                self.setItem(r, c, item)
        self.resizeColumnsToContents(); self.resizeRowsToContents()


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
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self._apply_style()
        self._load_model()
        self._build_home()
        self._check_updates()

    def _apply_style(self):
        self.setStyleSheet(f"""
        QMainWindow, QWidget {{ background: {PALETTE['void_black']}; color: {PALETTE['moon_white']}; font-size: 13px; }}
        QPushButton {{ background: {PALETTE['royal_indigo']}; border: 1px solid {PALETTE['castle_purple']}; padding: 8px; border-radius: 5px; }}
        QPushButton:hover {{ background: {PALETTE['deep_violet']}; }}
        QTableWidget {{ background: {PALETTE['midnight_navy']}; alternate-background-color: {PALETTE['void_black']}; gridline-color: {PALETTE['deep_violet']}; }}
        QHeaderView::section {{ background: {PALETTE['royal_indigo']}; color: {PALETTE['moon_white']}; padding: 5px; }}
        QLabel#Title {{ font-size: 28px; font-weight: bold; color: {PALETTE['moon_white']}; }}
        """)

    def _load_model(self):
        if self.save_path and self.save_path.exists():
            import json
            self.model = analyze_save(json.loads(self.save_path.read_text(encoding="utf-8")), self.ids)

    def nav(self):
        bar = QHBoxLayout()
        back = QPushButton("Back")
        home = QPushButton("Home")
        back.clicked.connect(lambda: self.stack.setCurrentIndex(max(0, self.stack.currentIndex() - 1)))
        home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        bar.addWidget(back); bar.addWidget(home); bar.addStretch(1)
        return bar

    def _page(self, title):
        w = QWidget(); layout = QVBoxLayout(w); layout.addLayout(self.nav())
        lab = QLabel(title); lab.setObjectName("Title"); layout.addWidget(lab)
        return w, layout

    def _build_home(self):
        w = QWidget(); layout = QVBoxLayout(w)
        title = QLabel(f"{APP_NAME} v{__version__}"); title.setObjectName("Title"); layout.addWidget(title)
        layout.addWidget(QLabel("Read-only Tiny Rogues save viewer. Saves are never modified."))
        layout.addWidget(QLabel(f"Loaded save: {self.save_path or 'None found'}"))
        browse = QPushButton("Browse / Reload Save")
        browse.clicked.connect(self._browse_save)
        layout.addWidget(browse)
        for label, fn in [(VIEW_CINDER_HIGHSCORES, self.show_records), (VIEW_KILL_COUNTS, self.show_counts), (VIEW_CLASS_BREAKDOWN, self.show_matrix_picker)]:
            b = QPushButton(label); b.clicked.connect(fn); layout.addWidget(b)
        export = QPushButton("Export CSV")
        export.clicked.connect(self._export)
        layout.addWidget(export)
        layout.addStretch(1)
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

    def _table_page(self, title):
        w, layout = self._page(title)
        top = QHBoxLayout(); sfm = QPushButton("SFM"); sfm.setCheckable(True); expl = QLabel("SFM inactive. Press SFM to choose rows and columns for a compact screenshot table.")
        top.addWidget(expl); top.addStretch(1); top.addWidget(sfm); layout.addLayout(top)
        table = SortableTable(title); table.set_sfm_controls(sfm, expl); sfm.clicked.connect(table.toggle_sfm); layout.addWidget(table)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)
        return table

    def _style_item(self, item, val, gold=False, route=None):
        if zero_value(val):
            item.setForeground(QColor(PALETTE['zero']))
        if route == "eden":
            item.setForeground(QColor(PALETTE['heaven_cyan']))
        elif route == "amon":
            item.setForeground(QColor(PALETTE['flame_orange']))
        if gold and not zero_value(val):
            item.setForeground(QColor(PALETTE['rare_gold']))

    def show_records(self):
        if not self.model: return
        table = self._table_page(VIEW_CINDER_HIGHSCORES)
        headers = ["Class", "Death", "Win+", "Eden", "Amon", "Primal Death", "Top Floor Beaten"]
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(self.model.records))
        gold = self.model.character_record_highlights()
        cols = [None, "best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "top_floor_rank"]
        for r, rec in enumerate(self.model.records):
            vals = [rec.character, format_cinder(rec.best_death), format_cinder(rec.best_win_plus), format_cinder(rec.best_eden), format_cinder(rec.best_amon), format_cinder(rec.best_primal_death), rec.top_floor_label]
            raw = [rec.character, rec.best_death if rec.best_death is not None else -1, rec.best_win_plus if rec.best_win_plus is not None else -1, rec.best_eden if rec.best_eden is not None else -1, rec.best_amon if rec.best_amon is not None else -1, rec.best_primal_death if rec.best_primal_death is not None else -1, rec.top_floor_rank]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(str(val)); item.setData(Qt.UserRole, raw[c]); item.setToolTip(rec.sources.get(cols[c] or "", "RunRecords / CinderStreakHistory"))
                self._style_item(item, val, gold=bool(cols[c] and (rec.character, cols[c]) in gold), route="eden" if cols[c] == "best_eden" else ("amon" if cols[c] == "best_amon" else None))
                table.setItem(r, c, item)
        table.finalize_default_order()

    def show_counts(self):
        if not self.model: return
        w, layout = self._page(VIEW_KILL_COUNTS)
        filter_label = QLabel(self.current_selection.display_text); layout.addWidget(filter_label)
        selector = QHBoxLayout(); group = QButtonGroup(w); group.setExclusive(False)
        def add_filter_button(text, value):
            b = QPushButton(text); b.setCheckable(True); b.setChecked((value == "ALL" and self.current_selection.label == "ALL") or (isinstance(value, int) and self.current_selection.low <= value <= self.current_selection.high if self.current_selection.low is not None else False))
            group.addButton(b); selector.addWidget(b)
            def clicked(checked=False, v=value, button=b):
                mods = QApplication.keyboardModifiers()
                self.current_selection, self.cinder_anchor = cinder_selection_from_click(self.current_selection, v, bool(mods & Qt.ShiftModifier), self.cinder_anchor)
                self.show_counts()
            b.clicked.connect(clicked)
        add_filter_button("ALL", "ALL")
        for i in range(1, 17): add_filter_button(str(i), i)
        selector.addStretch(1); layout.addLayout(selector)
        top = QHBoxLayout(); sfm = QPushButton("SFM"); sfm.setCheckable(True); expl = QLabel("SFM inactive. Press SFM to choose rows and columns for a compact screenshot table.")
        top.addWidget(expl); top.addStretch(1); top.addWidget(sfm); layout.addLayout(top)
        table = SortableTable(VIEW_KILL_COUNTS); table.set_sfm_controls(sfm, expl); sfm.clicked.connect(table.toggle_sfm); layout.addWidget(table)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)
        rows = self.model.completion_rows(self.current_selection).rows
        prefix = self.current_selection.label
        headers = ["Class", f"{prefix} Runs", "Death", f"{prefix} Death Kill Rate", "Win+", f"{prefix} Win+ Rate", "Eden", "Amon", "Primal Death"]
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(rows))
        hi = self.model.completion_highlights(self.current_selection)
        fields = [None, "cx_runs", "death_clears", "death_rate", "win_plus_clears", "win_plus_rate", "eden_clears", "amon_clears", "primal_death_clears"]
        for r, row in enumerate(rows):
            vals = [row.character, row.cx_runs, row.death_clears, format_rate(row.death_rate), row.win_plus_clears, format_rate(row.win_plus_rate), row.eden_clears, row.amon_clears, row.primal_death_clears]
            raws = [row.character, row.cx_runs, row.death_clears, row.death_rate if row.death_rate is not None else -1, row.win_plus_clears, row.win_plus_rate if row.win_plus_rate is not None else -1, row.eden_clears, row.amon_clears, row.primal_death_clears]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(str(val)); item.setData(Qt.UserRole, raws[c])
                self._style_item(item, val, gold=bool(fields[c] and (row.character, fields[c]) in hi), route="eden" if fields[c] == "eden_clears" else ("amon" if fields[c] == "amon_clears" else None))
                if row.inferred_historical_death_runs and c in (1, 2, 3):
                    item.setToolTip("Includes minimum historical Death clear evidence from CinderStreakHistory.")
                table.setItem(r, c, item)
        table.finalize_default_order()

    def show_matrix_picker(self):
        if not self.model: return
        w, layout = self._page(VIEW_CLASS_BREAKDOWN)
        combo = QComboBox(); [combo.addItem(r.character, r.character_id) for r in self.model.records]
        btn = QPushButton("Open Class Breakdown")
        btn.clicked.connect(lambda: self.show_matrix(combo.currentData()))
        layout.addWidget(QLabel("Choose a class:")); layout.addWidget(combo); layout.addWidget(btn)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)

    def show_matrix(self, cid):
        matrix = self.model.matrix_for_character(int(cid))
        table = self._table_page(f"{VIEW_CLASS_BREAKDOWN} — {matrix.character}")
        table.setColumnCount(len(matrix.cinders)); table.setHorizontalHeaderLabels([f"C{c}" for c in matrix.cinders])
        table.setRowCount(len(matrix.milestones)); table.setVerticalHeaderLabels(matrix.milestones)
        hi = view3_frontier_highlights(matrix)
        for r, milestone in enumerate(matrix.milestones):
            for c, cinder in enumerate(matrix.cinders):
                cell = matrix.cells[(cinder, milestone)]
                item = QTableWidgetItem(str(cell.count)); item.setData(Qt.UserRole, cell.count)
                item.setToolTip(f"{matrix.character}; Cinder {cinder}; {milestone}; count {cell.count}; route boss {cell.route_boss or 'n/a'}")
                self._style_item(item, cell.count, gold=(cinder, milestone) in hi)
                table.setItem(r, c, item)
        table.finalize_default_order()

    def _check_updates(self):
        def done(info, err):
            if info:
                QTimer.singleShot(0, lambda: self._offer_update(info))
        check_async(done)

    def _offer_update(self, info):
        box = QMessageBox(self); box.setWindowTitle("Update available"); box.setText(f"Tiny Rogues Tracker {info.latest_version} is available.")
        box.setInformativeText(info.html_url); box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if box.exec() == QMessageBox.Yes:
            try: download_and_launch_installer(info); QApplication.quit()
            except Exception as exc: QMessageBox.warning(self, "Update failed", str(exc))


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    app = QApplication(argv)
    win = TrackerApp()
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
