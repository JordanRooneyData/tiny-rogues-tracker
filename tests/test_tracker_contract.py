import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SAVE = ROOT / "fixtures" / "sample_save.json"
EXE = ROOT / "build" / "TinyRoguesTracker-linux"


def test_ids_json_has_required_sections_and_enriched_names():
    ids = json.loads((ROOT / "ids.json").read_text(encoding="utf-8"))
    for key in ["characters", "bosses", "routes", "cinder_modifiers", "gifts", "objectives", "teleports", "meta_perks"]:
        assert key in ids
    assert ids["characters"]["21"]["name"] == "Druid"
    assert ids["bosses"]["18"]["name"] == "Death"
    assert ids["cinder_modifiers"]["8"]["name"] == "Archnemesis"
    assert ids["routes"]["heaven"]["completion_boss_ids"] == [23]


def test_parser_generates_report_without_modifying_save():
    before = SAMPLE_SAVE.read_bytes()
    out = ROOT / "build" / "pytest-report.txt"
    result = subprocess.run([str(EXE), "--save", str(SAMPLE_SAVE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--no-pause"], text=True, capture_output=True, check=True)
    assert "Tiny Rogues Tracker v2" in result.stdout
    assert "Druid" in result.stdout
    assert "Death" in result.stdout and "Heaven" in result.stdout and "Hell" in result.stdout and "Law" in result.stdout
    assert out.exists()
    assert "Run records: 3" in out.read_text(encoding="utf-8")
    assert SAMPLE_SAVE.read_bytes() == before


def test_report_contains_verified_sample_route_values():
    out = ROOT / "build" / "pytest-report.txt"
    subprocess.run([str(EXE), "--save", str(SAMPLE_SAVE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--no-pause"], check=True)
    text = out.read_text(encoding="utf-8")
    assert "Druid" in text and "12" in text
    assert "Ninja" in text and "16" in text
    assert "Alchemist" in text and "14" in text
    assert "completion boss IDs" in text


def test_windows_auto_locator_scans_all_user_profiles_and_has_multi_save_picker():
    source = (ROOT / "src" / "main.cpp").read_text(encoding="utf-8")
    assert 'fs::path("C:/Users")' in source or 'fs::path("C:\\\\Users")' in source
    assert '"AppData") / "LocalLow" / "RubyDev" / "Tiny Rogues"' in source
    assert "select_save_from_candidates" in source
    assert "Multiple Tiny Rogues save folders were found" in source
