from pathlib import Path

from tiny_rogues_tracker import __version__

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"


def test_version_is_044():
    assert __version__ == "0.5.0"


def test_main_menu_has_primary_and_utility_action_sections_with_lower_priority_utility_style():
    gui = GUI.read_text(encoding="utf-8")
    assert '"Primary Actions"' in gui
    assert '"Utility Actions"' in gui
    assert '"PrimaryAction"' in gui
    assert '"UtilityAction"' in gui
    assert "QPushButton#PrimaryAction" in gui
    assert "QPushButton#UtilityAction" in gui
    assert "PALETTE['midnight_navy']" in gui.split("QPushButton#UtilityAction", 1)[1].split("QPushButton#ClassGridButton", 1)[0]
    assert "PALETTE['zero']" in gui.split("QPushButton#UtilityAction", 1)[1].split("QPushButton#ClassGridButton", 1)[0]
    assert "layout.addSpacing(28)" in gui
    primary_pos = gui.index('"Primary Actions"')
    utility_pos = gui.index('"Utility Actions"')
    assert primary_pos < utility_pos


def test_main_menu_places_core_views_in_primary_grid_and_utilities_in_bottom_grid():
    gui = GUI.read_text(encoding="utf-8")
    home = gui.split("def _build_home", 1)[1].split("def _browse_save", 1)[0]
    assert "primary_grid" in home and "utility_grid" in home
    assert "VIEW_CINDER_HIGHSCORES" in home
    assert "VIEW_KILL_COUNTS" in home
    assert "VIEW_SURVIVAL_BREAKDOWN" in home
    assert "Browse / Reload Save" in home
    assert "Check for Updates" in home
    assert "Export CSV" in home
    assert home.index("primary_grid") < home.index("utility_grid")


def test_class_breakdown_uses_responsive_alphabetical_button_grid_without_dropdown_or_open_button():
    gui = GUI.read_text(encoding="utf-8")
    picker = gui.split("def show_matrix_picker", 1)[1].split("def show_matrix", 1)[0]
    assert "QGridLayout" in picker
    assert "records = sorted(self.model.records, key=lambda r: r.character.lower())" in picker
    assert "columns = self._class_grid_columns()" in picker
    assert "grid.addWidget(button, index // columns, index % columns)" in picker
    assert "setMinimumSize(150, 52)" in picker
    assert 'setObjectName("ClassGridButton")' in picker
    assert "button.clicked.connect(lambda checked=False, cid=record.character_id: self.show_matrix(cid, self.survival_mode))" in picker
    assert "QComboBox(); [combo.addItem" not in picker
    assert "Open Survival Breakdown" not in picker
    assert "btn = QPushButton" not in picker


def test_class_grid_keeps_sprite_ready_placeholder():
    gui = GUI.read_text(encoding="utf-8")
    assert 'QPushButton(f"□  {record.character}")' in gui
    assert "QPushButton#ClassGridButton" in gui
