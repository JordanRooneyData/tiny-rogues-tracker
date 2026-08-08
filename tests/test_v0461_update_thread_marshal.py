from pathlib import Path

from tiny_rogues_tracker import __version__

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "tiny_rogues_tracker" / "gui.py"


def test_version_is_0461_hotfix():
    assert __version__ == "0.4.6.2"


def test_startup_update_result_is_marshalled_back_to_gui_thread():
    gui = GUI.read_text(encoding="utf-8")
    init = gui.split("def __init__", 1)[1].split("def _apply_style", 1)[0]
    assert "self.pending_update_result" in init
    assert "self.update_result_timer = QTimer(self)" in init
    assert "self.update_result_timer.timeout.connect(self._drain_update_result)" in init
    check = gui.split("def _check_updates", 1)[1].split("def manual_check_for_updates", 1)[0]
    assert "self.update_result_timer.start()" in check
    assert "self.pending_update_result = (info, err)" in check
    assert "Worker-thread callback: store only" in check
    assert "Context-free QTimer.singleShot" in check
    assert "QTimer.singleShot(0, lambda: self._offer_update" not in check
    assert "def _drain_update_result" in check
    assert "self._offer_update(info, manual=False)" in check


def test_manual_update_path_remains_synchronous_and_user_visible():
    gui = GUI.read_text(encoding="utf-8")
    manual = gui.split("def manual_check_for_updates", 1)[1].split("def _offer_update", 1)[0]
    assert "check_latest_release()" in manual
    assert "Tiny Rogues Tracker is up to date" in manual
    assert "QMessageBox.information" in manual
