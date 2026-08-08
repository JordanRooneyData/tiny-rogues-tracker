from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gui_source_uses_pyside6_and_required_views():
    source = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    assert "PySide6" in source
    assert "Cinder Highscores" in source
    assert "Kill Counts" in source
    assert "Survival Breakdown" in source
    assert "SFM" in source
    assert "Back" in source and "Home" in source
    assert "#E52A24" in source and "#F26A16" in source
    assert "#20DCEB" in source and "#BDEBF4" in source
    assert "#F0D52C" in source


def test_build_release_update_contract_files():
    workflow = ROOT / ".github" / "workflows" / "windows-release.yml"
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "windows-latest" in text
    assert "PySide6" in text
    assert "pyinstaller" in text.lower()
    assert "Inno Setup" in text or "iscc" in text.lower()
    assert "softprops/action-gh-release" in text
    ps1 = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "PyInstaller" in ps1 and "TinyRoguesTracker-v0.4.7" in ps1
    iss = (ROOT / "installer" / "TinyRoguesTracker.iss").read_text(encoding="utf-8")
    assert "AppVersion=0.4.7" in iss
    updater = (ROOT / "tiny_rogues_tracker" / "updater.py").read_text(encoding="utf-8")
    assert "api.github.com/repos" in updater
    assert "releases/latest" in updater
    assert "GITHUB_REPO" in updater
