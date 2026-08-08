import json
import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SAVE = ROOT / "fixtures" / "sample_save.json"
EXE = ROOT / "build" / "TinyRoguesTracker-linux"


pytestmark = pytest.mark.skipif(
    not EXE.exists(),
    reason=(
        "Legacy C++ console integration tests require the prebuilt "
        "build/TinyRoguesTracker-linux binary; v0.4.0 Windows CI builds and "
        "tests the PySide6 tracker package instead."
    ),
)


def run_tracker(*extra, save=SAMPLE_SAVE, out=None, csv=None, character="21"):
    out = out or (ROOT / "build" / "pytest-report.txt")
    csv = csv or (ROOT / "build" / "pytest-report.csv")
    cmd = [str(EXE), "--save", str(save), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--csv", str(csv), "--no-pause"]
    if character is not None:
        cmd += ["--character", str(character)]
    cmd += list(extra)
    return subprocess.run(cmd, text=True, capture_output=True, check=True)


def test_ids_json_has_required_sections_and_enriched_names():
    ids = json.loads((ROOT / "ids.json").read_text(encoding="utf-8"))
    for key in ["characters", "bosses", "routes", "cinder_modifiers", "gifts", "objectives", "teleports", "meta_perks"]:
        assert key in ids
    assert ids["characters"]["21"]["name"] == "Druid"
    assert ids["bosses"]["18"]["name"] == "Death"
    assert ids["bosses"]["23"]["name"] == "Eden"
    assert ids["bosses"]["24"]["name"] == "Amon"
    assert ids["bosses"]["19"]["name"] == "Primal Death"
    assert ids["bosses"]["20"]["name"] == "Tiamat"
    assert ids["bosses"]["21"]["name"] == "Bahamut"
    assert ids["bosses"]["22"]["name"] == "Geryon"
    assert ids["cinder_modifiers"]["8"]["name"] == "Archnemesis"
    assert ids["routes"]["heaven"]["completion_boss_ids"] == [23]


def test_parser_generates_three_views_csv_and_does_not_modify_save():
    before = SAMPLE_SAVE.read_bytes()
    out = ROOT / "build" / "pytest-report.txt"
    csv = ROOT / "build" / "pytest-report.csv"
    result = run_tracker(out=out, csv=csv)
    assert "Tiny Rogues Tracker v2" in result.stdout
    assert "View 1 — Best records by character" in result.stdout
    assert "View 2 — Cinder 16 clear counts by character" in result.stdout
    assert "View 3 — Character floor x cinder matrix: Druid" in result.stdout
    assert "Best Floor" in result.stdout
    assert "Wrote" in result.stdout
    assert out.exists() and csv.exists()
    assert "Run records: 3" in out.read_text(encoding="utf-8")
    assert "best,21,\"Druid\",12,12,12,—,—,1,12" in csv.read_text(encoding="utf-8")
    assert SAMPLE_SAVE.read_bytes() == before


def test_route_classification_contracts():
    out = ROOT / "build" / "pytest-report.txt"
    run_tracker(out=out)
    text = out.read_text(encoding="utf-8")
    assert "Druid" in text and "12" in text
    assert "Ninja" in text and "16" in text
    assert "Alchemist" in text and "14" in text
    assert "reaching Bahamut/Tiamat/Geryon or their floor alone is not Win+" in text
    assert "Eden: completion boss IDs Eden (23)" in text
    assert "Amon: completion boss IDs Amon (24)" in text
    assert "Primal Death: completion boss IDs Primal Death (19)" in text
    assert "FloorReached is zero-based" in text


def test_route_floor_without_final_boss_is_not_win_plus_and_matrix_uses_floor_plus_one(tmp_path):
    payload = json.loads(SAMPLE_SAVE.read_text(encoding="utf-8"))
    payload["RunRecords"].append({"PlayedClass": 21, "CinderLevel": 16, "FloorReached": 11, "bossesKilled": [18, 21]})
    save = tmp_path / "Public_Slot1_Save1.json"
    save.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "report.txt"
    csv = tmp_path / "report.csv"
    run_tracker(save=save, out=out, csv=csv)
    text = out.read_text(encoding="utf-8")
    floor12 = next(line for line in text.splitlines() if line.startswith("Floor 12"))
    cells = floor12.split()
    assert cells[0:2] == ["Floor", "12"]
    assert cells[-1] == "1"  # cinder 16 lands on displayed Floor 12, not Win+
    win = next(line for line in text.splitlines() if line.startswith("Win+"))
    assert win.split()[-1] == "0"
    assert "cinder16_counts,21,\"Druid\",1,0,0,0,0" in csv.read_text(encoding="utf-8")


def test_cinder16_counts_are_counts_not_flags(tmp_path):
    payload = json.loads(SAMPLE_SAVE.read_text(encoding="utf-8"))
    payload["RunRecords"].append({"PlayedClass": 23, "CinderLevel": 16, "FloorReached": 11, "bossesKilled": [18, 22, 24]})
    save = tmp_path / "Public_Slot1_Save1.json"
    save.write_text(json.dumps(payload), encoding="utf-8")
    csv = tmp_path / "report.csv"
    run_tracker("--character", "23", save=save, out=tmp_path / "report.txt", csv=csv, character=None)
    assert "cinder16_counts,23,\"Ninja\",2,2,0,2,0" in csv.read_text(encoding="utf-8")


def test_cinder_zero_clear_is_not_dash(tmp_path):
    payload = json.loads(SAMPLE_SAVE.read_text(encoding="utf-8"))
    payload["RunRecords"].append({"PlayedClass": 1, "CinderLevel": 0, "FloorReached": 10, "bossesKilled": [18]})
    save = tmp_path / "Public_Slot1_Save1.json"
    save.write_text(json.dumps(payload), encoding="utf-8")
    csv = tmp_path / "report.csv"
    run_tracker(save=save, out=tmp_path / "report.txt", csv=csv, character="1")
    assert "best,1,\"Knight\",0,—,—,—,—,1,11" in csv.read_text(encoding="utf-8")


def test_zero_run_and_unresolved_characters_still_appear():
    out = ROOT / "build" / "pytest-report.txt"
    run_tracker(out=out)
    text = out.read_text(encoding="utf-8")
    assert "TheHero" in text
    assert "Chaos" in text and "Santa" in text
    assert "Class ID 35" not in text
    assert "Unresolved character mappings" not in text


def test_blank_save_filtering_and_single_non_blank_auto_selection(tmp_path):
    blank = {"TimeOfSave": "blank", "RunRecords": [], "CinderStreakHistory": []}
    (tmp_path / "Public_Slot1_Save1.json").write_text(json.dumps(blank), encoding="utf-8")
    save = tmp_path / "Public_Slot1_Save2.json"
    save.write_text(SAMPLE_SAVE.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "report.txt"
    csv = tmp_path / "report.csv"
    result = subprocess.run(
        [str(EXE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--csv", str(csv), "--character", "21", "--no-pause"],
        cwd=tmp_path,
        env={"HOME": str(tmp_path)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert str(save) in result.stdout
    assert "Tiny Rogues Tracker" in out.read_text(encoding="utf-8")


def test_multiple_iterations_for_same_slot_default_to_newest_save_file(tmp_path):
    old_payload = json.loads(SAMPLE_SAVE.read_text(encoding="utf-8"))
    new_payload = json.loads(SAMPLE_SAVE.read_text(encoding="utf-8"))
    old_payload["TimeOfSave"] = "old-iteration"
    new_payload["TimeOfSave"] = "new-iteration"
    old_save = tmp_path / "Public_Slot1_Save1.json"
    new_save = tmp_path / "Public_Slot1_Save3.json"
    old_save.write_text(json.dumps(old_payload), encoding="utf-8")
    new_save.write_text(json.dumps(new_payload), encoding="utf-8")
    now = time.time()
    os.utime(old_save, (now - 100, now - 100))
    os.utime(new_save, (now, now))
    out = tmp_path / "report.txt"
    csv = tmp_path / "report.csv"
    result = subprocess.run(
        [str(EXE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--csv", str(csv), "--character", "21", "--no-pause"],
        cwd=tmp_path,
        env={"HOME": str(tmp_path)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert str(new_save) in result.stdout
    assert str(old_save) not in result.stdout
    assert "Save time: new-iteration" in out.read_text(encoding="utf-8")


def test_auto_locator_accepts_real_saves_even_when_run_records_are_after_4kb(tmp_path):
    save = tmp_path / "Public_Slot1_Save1.json"
    payload = json.loads(SAMPLE_SAVE.read_text(encoding="utf-8"))
    payload = {"TimeOfSave": payload["TimeOfSave"], "PaddingBeforeRunRecords": "x" * 6000, **payload}
    save.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "report.txt"
    csv = tmp_path / "report.csv"
    result = subprocess.run(
        [str(EXE), "--ids", str(ROOT / "ids.json"), "--report", str(out), "--csv", str(csv), "--character", "21", "--no-pause"],
        cwd=tmp_path,
        env={"HOME": str(tmp_path)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert str(save) in result.stdout
    assert "Tiny Rogues Tracker" in out.read_text(encoding="utf-8")


def test_mode_picker_does_not_ask_for_character_until_mode3():
    result = subprocess.run(
        [str(EXE), "--save", str(SAMPLE_SAVE), "--ids", str(ROOT / "ids.json"), "--report", str(ROOT / "build" / "interactive-report.txt"), "--csv", str(ROOT / "build" / "interactive-report.csv")],
        input="1\nQ\nQ\n",
        text=True,
        capture_output=True,
        check=True,
    )
    before_view1 = result.stdout.split("View 1 — Best records by character", 1)[0]
    assert "Pick one character" not in before_view1
    assert "mode picker" in result.stdout


def test_windows_auto_locator_and_controls_are_present_static():
    source = (ROOT / "src" / "main.cpp").read_text(encoding="utf-8")
    assert 'fs::path("C:/Users")' in source or 'fs::path("C:\\\\Users")' in source
    assert '"AppData") / "LocalLow" / "RubyDev" / "Tiny Rogues"' in source
    assert "Multiple non-blank Tiny Rogues saves were found" in source
    assert "B back" in source and "M main menu" in source and "Q exit" in source
    assert "save_has_meaningful_data" in source
    assert "newest_save_per_slot" in source
    assert "slot_key_for_save_name" in source
