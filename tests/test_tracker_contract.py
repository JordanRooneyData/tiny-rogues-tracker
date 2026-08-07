import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SAVE = ROOT / "fixtures" / "sample_save.json"
EXE = ROOT / "build" / "TinyRoguesTracker-linux"


def test_ids_json_has_required_sections():
    ids = json.loads((ROOT / "ids.json").read_text(encoding="utf-8"))
    for key in ["characters", "bosses", "routes", "cinder_modifiers", "gifts", "objectives", "teleports", "meta_perks"]:
        assert key in ids


def test_parser_generates_report_without_modifying_save():
    before = SAMPLE_SAVE.read_bytes()
    out = ROOT / "build" / "pytest-report.txt"
    result = subprocess.run([str(EXE), "--save", str(SAMPLE_SAVE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--no-pause"], text=True, capture_output=True, check=True)
    assert "Tiny Rogues Tracker" in result.stdout
    assert "Class ID 23" in result.stdout
    assert "Death Max" in result.stdout
    assert out.exists()
    assert "Run records: 3" in out.read_text(encoding="utf-8")
    assert SAMPLE_SAVE.read_bytes() == before


def test_report_contains_verified_sample_values():
    out = ROOT / "build" / "pytest-report.txt"
    if not out.exists():
        subprocess.run([str(EXE), "--save", str(SAMPLE_SAVE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--no-pause"], check=True)
    text = out.read_text(encoding="utf-8")
    assert "Class ID 21" in text and "12" in text
    assert "Class ID 23" in text and "16" in text
    assert "Class ID 32" in text and "14" in text
