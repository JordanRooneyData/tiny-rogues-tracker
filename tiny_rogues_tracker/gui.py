from __future__ import annotations

import sys
from pathlib import Path

from . import APP_NAME, __version__
from .core import (
    CinderSelection,
    analyze_save,
    choose_default_save,
    discover_save_files,
    export_csv,
    format_cinder,
    format_rate,
    load_ids,
    view3_frontier_highlights,
)
from .updater import check_async, download_and_launch_installer

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
        QScrollArea, QFrame
    )
except Exception:  # pragma: no cover - Linux CI can validate source without PySide6 installed
    Qt = QTimer = QAction = QColor = QApplication = QFileDialog = QHBoxLayout = QHeaderView = QLabel = QMainWindow = QMenu = QMessageBox = QPushButton = QStackedWidget = QTableWidget = QTableWidgetItem = QVBoxLayout = QWidget = QComboBox = QButtonGroup = QScrollArea = QFrame = None

class SortableTable(QTableWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.default_rows: list[list[QTableWidgetItem]] = []
        self.sort_column = None
        self.sort_direction = 0
        self.sfm_state = 0
        self.setSortingEnabled(False)
        self.horizontalHeader().sectionClicked.connect(self._cycle_sort)
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._header_menu)
        self.verticalHeader().setVisible(True)
        self.setSelectionMode(QTableWidget.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)

    def _numeric(self, item):
        value = item.data(Qt.UserRole)
        if value is not None:
            return value
        text = item.text().replace("≥", "").replace("%", "").replace("—", "-1")
        try:
            return float(text)
        except Exception:
            return item.text().lower()

    def _cycle_sort(self, column: int):
        if self.sort_column != column:
            self.sort_column = column
            self.sort_direction = 1
        else:
            self.sort_direction = (self.sort_direction + 1) % 3
        self.apply_sort()

    def _header_menu(self, pos):
        col = self.horizontalHeader().logicalIndexAt(pos)
        menu = QMenu(self)
        for label, direction in [("Sort ascending", 1), ("Sort descending", 2), ("Restore default order", 0)]:
            action = QAction(label, self)
            action.triggered.connect(lambda _=False, d=direction: self._explicit_sort(col, d))
            menu.addAction(action)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    def _explicit_sort(self, col, direction):
        self.sort_column = col
        self.sort_direction = direction
        self.apply_sort()

    def apply_sort(self):
        if self.sort_direction == 0 or self.sort_column is None:
            self.sortItems(0, Qt.AscendingOrder)
            return
        self.sortItems(self.sort_column, Qt.AscendingOrder if self.sort_direction == 1 else Qt.DescendingOrder)
        header = self.horizontalHeaderItem(self.sort_column)
        if header:
            base = header.text().replace(" ▲", "").replace(" ▼", "")
            header.setText(base + (" ▲" if self.sort_direction == 1 else " ▼"))

    def toggle_sfm(self):
        self.sfm_state = (self.sfm_state + 1) % 3
        if self.sfm_state == 1:
            self.setSelectionMode(QTableWidget.MultiSelection)
            QMessageBox.information(self, "SFM selection", "Select rows/columns for the screenshot mini-table, then press SFM again.")
        elif self.sfm_state == 2:
            rows = sorted({i.row() for i in self.selectedIndexes()})
            cols = sorted({i.column() for i in self.selectedIndexes()})
            if not rows or not cols:
                QMessageBox.information(self, "SFM", "Nothing selected. Keeping the full table; select cells, rows, or columns and press SFM again.")
                self.sfm_state = 1
                return
            self._collapse(rows, cols)
        else:
            QMessageBox.information(self, "SFM", "Reload the view to restore the full table, or use Home/Back and reopen it.")

    def _collapse(self, rows, cols):
        data = [[self.item(r, c).clone() if self.item(r, c) else QTableWidgetItem("") for c in cols] for r in rows]
        headers = [self.horizontalHeaderItem(c).text() for c in cols]
        self.clear()
        self.setRowCount(len(data))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        for r, row in enumerate(data):
            for c, item in enumerate(row):
                self.setItem(r, c, item)

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
        for label, fn in [("Character Records", self.show_records), ("Completion Counts and Rates", self.show_counts), ("Character Run Matrix", self.show_matrix_picker)]:
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
        top = QHBoxLayout(); sfm = QPushButton("SFM"); top.addStretch(1); top.addWidget(sfm); layout.addLayout(top)
        table = SortableTable(title); sfm.clicked.connect(table.toggle_sfm); layout.addWidget(table)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)
        return table

    def show_records(self):
        if not self.model: return
        table = self._table_page("Character Records")
        headers = ["Character", "Death", "Win+", "Eden", "Amon", "Primal Death", "Runs", "Top Floor Beaten"]
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(self.model.records))
        gold = self.model.character_record_highlights()
        cols = [None, "best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "observed_runs", "top_floor_rank"]
        for r, rec in enumerate(self.model.records):
            vals = [rec.character, format_cinder(rec.best_death), format_cinder(rec.best_win_plus), format_cinder(rec.best_eden), format_cinder(rec.best_amon), format_cinder(rec.best_primal_death), rec.runs_display, rec.top_floor_label]
            raw = [rec.character, rec.best_death or -1, rec.best_win_plus or -1, rec.best_eden or -1, rec.best_amon or -1, rec.best_primal_death or -1, rec.observed_runs, rec.top_floor_rank]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(str(val)); item.setData(Qt.UserRole, raw[c]); item.setToolTip(rec.runs_tooltip if c == 6 else rec.sources.get(cols[c] or "", "RunRecords / CinderStreakHistory"))
                if val in ("0", "—") or val == "≥1": item.setForeground(QColor(PALETTE['zero']))
                if cols[c] and (rec.character, cols[c]) in gold and val not in ("0", "—"):
                    item.setForeground(QColor(PALETTE['rare_gold']))
                if cols[c] == "best_eden": item.setToolTip("Heaven/Eden-specific metric")
                if cols[c] == "best_amon": item.setToolTip("Hell/Amon-specific metric")
                table.setItem(r, c, item)

    def show_counts(self):
        if not self.model: return
        table = self._table_page("Completion Counts and Rates")
        # Compact cinder selector; Shift-click range is implemented by combo range entries for reliability in v0.4.0.
        table.setToolTip("Cinder selector supports ALL, single C1-C16, and inclusive Cx-Cy ranges in the model; GUI defaults to ALL.")
        rows = self.model.completion_rows(self.current_selection).rows
        headers = ["Character", "Cx runs", "Death", "Death rate", "Win+", "Win+ rate", "Eden", "Amon", "Primal Death"]
        table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(rows))
        hi = self.model.completion_highlights(self.current_selection)
        fields = [None, "cx_runs", "death_clears", "death_rate", "win_plus_clears", "win_plus_rate", "eden_clears", "amon_clears", "primal_death_clears"]
        for r, row in enumerate(rows):
            vals = [row.character, row.cx_runs, row.death_clears, format_rate(row.death_rate), row.win_plus_clears, format_rate(row.win_plus_rate), row.eden_clears, row.amon_clears, row.primal_death_clears]
            raws = [row.character, row.cx_runs, row.death_clears, row.death_rate or -1, row.win_plus_clears, row.win_plus_rate or -1, row.eden_clears, row.amon_clears, row.primal_death_clears]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(str(val)); item.setData(Qt.UserRole, raws[c])
                if val in (0, "—"): item.setForeground(QColor(PALETTE['zero']))
                if fields[c] and (row.character, fields[c]) in hi and val not in (0, "—"):
                    item.setForeground(QColor(PALETTE['rare_gold']))
                table.setItem(r, c, item)

    def show_matrix_picker(self):
        if not self.model: return
        w, layout = self._page("Character Run Matrix")
        combo = QComboBox(); [combo.addItem(r.character, r.character_id) for r in self.model.records]
        btn = QPushButton("Open Matrix")
        btn.clicked.connect(lambda: self.show_matrix(combo.currentData()))
        layout.addWidget(QLabel("Choose a character:")); layout.addWidget(combo); layout.addWidget(btn)
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)

    def show_matrix(self, cid):
        matrix = self.model.matrix_for_character(int(cid))
        table = self._table_page(f"Character Run Matrix — {matrix.character}")
        table.setColumnCount(len(matrix.cinders)); table.setHorizontalHeaderLabels([f"C{c}" for c in matrix.cinders])
        table.setRowCount(len(matrix.milestones)); table.setVerticalHeaderLabels(matrix.milestones)
        hi = view3_frontier_highlights(matrix)
        for r, milestone in enumerate(matrix.milestones):
            for c, cinder in enumerate(matrix.cinders):
                cell = matrix.cells[(cinder, milestone)]
                item = QTableWidgetItem(str(cell.count)); item.setData(Qt.UserRole, cell.count)
                item.setToolTip(f"{matrix.character}; Cinder {cinder}; {milestone}; count {cell.count}; route boss {cell.route_boss or 'n/a'}")
                if cell.count == 0: item.setForeground(QColor(PALETTE['zero']))
                if (cinder, milestone) in hi: item.setForeground(QColor(PALETTE['rare_gold']))
                table.setItem(r, c, item)

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
