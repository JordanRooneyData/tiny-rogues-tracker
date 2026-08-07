from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import __version__

DEATH_ID = 18
EDEN_ID = 23
AMON_ID = 24
PRIMAL_DEATH_ID = 19
ROUTE_FINAL_IDS = {EDEN_ID: "Eden", AMON_ID: "Amon", PRIMAL_DEATH_ID: "Primal Death"}
ROUTE_DRAGON_IDS = {20, 21, 22}
VERSION = __version__

@dataclass(frozen=True)
class TopFloor:
    rank: int
    label: str
    display_floor_entered: int | None = None

@dataclass(frozen=True)
class CinderSelection:
    low: int | None = None
    high: int | None = None

    @classmethod
    def all(cls) -> "CinderSelection":
        return cls(None, None)

    @classmethod
    def single(cls, value: int) -> "CinderSelection":
        return cls(value, value)

    @classmethod
    def range(cls, a: int, b: int) -> "CinderSelection":
        low, high = sorted((a, b))
        return cls(low, high)

    @property
    def label(self) -> str:
        if self.low is None or self.high is None:
            return "ALL"
        if self.low == self.high:
            return f"C{self.low}"
        return f"C{self.low}–C{self.high}"

    def contains(self, cinder: int) -> bool:
        if self.low is None or self.high is None:
            return True
        return self.low <= cinder <= self.high

def cinder_selection_from_click(current: CinderSelection, clicked: int | str, shift: bool = False, anchor: int | None = None) -> tuple[CinderSelection, int | None]:
    """Model the GUI cinder selector: ALL, single click, and shift-click ranges."""
    if clicked == "ALL":
        return CinderSelection.all(), None
    value = int(clicked)
    if not shift:
        return CinderSelection.single(value), value
    low_anchor = 1 if anchor is None or current.low is None else anchor
    return CinderSelection.range(low_anchor, value), low_anchor

@dataclass
class CharacterRecord:
    character_id: int
    character: str
    best_death: int | None = None
    best_win_plus: int | None = None
    best_eden: int | None = None
    best_amon: int | None = None
    best_primal_death: int | None = None
    observed_runs: int = 0
    minimum_runs: int = 0
    top_floor_rank: int = 0
    top_floor_label: str = "0"
    sources: dict[str, str] = field(default_factory=dict)

    @property
    def runs_display(self) -> str:
        if self.observed_runs:
            return str(self.observed_runs)
        if self.minimum_runs:
            return "≥1"
        return "0"

    @property
    def runs_tooltip(self) -> str:
        if self.observed_runs:
            return f"Exact retained RunRecords count: {self.observed_runs}."
        if self.minimum_runs:
            return "Historical clear exists in CinderStreakHistory, but detailed retained RunRecords do not contain the run; exact run count is unknown."
        return "No retained runs or historical clears found in this save."

@dataclass
class CompletionRow:
    character: str
    character_id: int
    cx_runs: int = 0
    death_clears: int = 0
    win_plus_clears: int = 0
    eden_clears: int = 0
    amon_clears: int = 0
    primal_death_clears: int = 0

    @property
    def death_rate(self) -> float | None:
        return None if self.cx_runs == 0 else self.death_clears / self.cx_runs

    @property
    def win_plus_rate(self) -> float | None:
        return None if self.cx_runs == 0 else self.win_plus_clears / self.cx_runs

@dataclass
class CompletionTable:
    label: str
    rows: list[CompletionRow]

    @property
    def by_name(self) -> dict[str, CompletionRow]:
        return {r.character: r for r in self.rows}

@dataclass
class RunMetric:
    character_id: int
    cinder: int
    bosses: set[int]
    stored_floor: int | None
    top_floor: TopFloor

    @property
    def is_death(self) -> bool:
        return DEATH_ID in self.bosses

    @property
    def route_boss(self) -> str | None:
        for bid, name in ROUTE_FINAL_IDS.items():
            if bid in self.bosses:
                return name
        return None

    @property
    def is_win_plus(self) -> bool:
        return self.route_boss is not None

@dataclass
class MatrixCell:
    cinder: int
    milestone: str
    count: int = 0
    route_boss: str | None = None

@dataclass
class MatrixModel:
    character: str
    milestones: list[str]
    cinders: list[int]
    cells: dict[tuple[int, str], MatrixCell]

@dataclass
class TrackerModel:
    ids: dict[str, Any]
    save: dict[str, Any]
    runs: list[RunMetric]
    records: list[CharacterRecord]

    @property
    def character_records_by_name(self) -> dict[str, CharacterRecord]:
        return {r.character: r for r in self.records}

    def completion_rows(self, selection: CinderSelection) -> CompletionTable:
        rows = [CompletionRow(r.character, r.character_id) for r in self.records]
        by_id = {r.character_id: r for r in rows}
        for run in self.runs:
            if not selection.contains(run.cinder):
                continue
            row = by_id.setdefault(run.character_id, CompletionRow(character_name(self.ids, run.character_id), run.character_id))
            row.cx_runs += 1
            if run.is_death:
                row.death_clears += 1
            if run.is_win_plus:
                row.win_plus_clears += 1
                if run.route_boss == "Eden":
                    row.eden_clears += 1
                elif run.route_boss == "Amon":
                    row.amon_clears += 1
                elif run.route_boss == "Primal Death":
                    row.primal_death_clears += 1
        return CompletionTable(selection.label, rows)

    def character_record_highlights(self) -> set[tuple[str, str]]:
        columns = ["best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "observed_runs", "top_floor_rank"]
        highlights: set[tuple[str, str]] = set()
        for col in columns:
            values = [getattr(r, col) for r in self.records]
            numeric = [v for v in values if isinstance(v, int) and v > 0]
            if not numeric:
                continue
            best = max(numeric)
            for r in self.records:
                if getattr(r, col) == best:
                    highlights.add((r.character, col))
        return highlights

    def completion_highlights(self, selection: CinderSelection) -> set[tuple[str, str]]:
        table = self.completion_rows(selection)
        cols = ["cx_runs", "death_clears", "win_plus_clears", "eden_clears", "amon_clears", "primal_death_clears"]
        out: set[tuple[str, str]] = set()
        for col in cols:
            vals = [getattr(r, col) for r in table.rows if getattr(r, col) > 0]
            if not vals:
                continue
            best = max(vals)
            for r in table.rows:
                if getattr(r, col) == best:
                    out.add((r.character, col))
        for col in ["death_rate", "win_plus_rate"]:
            vals = [getattr(r, col) for r in table.rows if getattr(r, col) not in (None, 0)]
            if not vals:
                continue
            best = max(vals)
            for r in table.rows:
                if getattr(r, col) == best:
                    out.add((r.character, col))
        return out

    def matrix_for_character(self, character: str | int) -> MatrixModel:
        if isinstance(character, str) and not character.isdigit():
            cid = next((r.character_id for r in self.records if r.character == character), None)
            if cid is None:
                raise KeyError(character)
        else:
            cid = int(character)
        name = character_name(self.ids, cid)
        milestones = ["0"] + [str(i) for i in range(1, 10)] + ["10 (Death)", "11 (Dragon)", "12 (Win+)"]
        cinders = list(range(17))
        cells = {(c, m): MatrixCell(c, m) for c in cinders for m in milestones}
        for run in self.runs:
            if run.character_id != cid or run.cinder not in cinders:
                continue
            label = run.top_floor.label
            cells[(run.cinder, label)].count += 1
            cells[(run.cinder, label)].route_boss = run.route_boss
        return MatrixModel(name, milestones, cinders, cells)

class SortState:
    def __init__(self) -> None:
        self.column: str | None = None
        self.direction = 0

    def click(self, rows: list[dict[str, Any]], column: str) -> list[dict[str, Any]]:
        if self.column != column:
            self.column = column
            self.direction = 1
        else:
            self.direction = (self.direction + 1) % 3
        if self.direction == 0:
            return sorted(rows, key=lambda r: r.get("_order", 0))
        reverse = self.direction == 2
        ordered = sorted(enumerate(rows), key=lambda ir: (sort_key(ir[1].get(column)), ir[0]), reverse=reverse)
        return [r for _, r in ordered]

def sort_key(v: Any) -> Any:
    if v in (None, "—"):
        return -1
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).strip("%≥+"))
    except Exception:
        return str(v).lower()

def load_ids(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def character_name(ids: dict[str, Any], cid: int) -> str:
    return ids.get("characters", {}).get(str(cid), {}).get("name", f"Class ID {cid}")

def all_character_ids(ids: dict[str, Any], save: dict[str, Any]) -> list[int]:
    out = {int(k) for k in ids.get("characters", {}).keys() if str(k).lstrip("-").isdigit()}
    out.update(range(len(save.get("CinderStreakHistory", []))))
    for r in save.get("RunRecords", []):
        if "PlayedClass" in r:
            out.add(int(r["PlayedClass"]))
    return sorted(out)

def bosses_from(run: dict[str, Any]) -> set[int]:
    return {int(b) for b in run.get("bossesKilled", []) if isinstance(b, int)}

def top_floor_beaten(run: dict[str, Any]) -> TopFloor:
    bosses = bosses_from(run)
    stored = run.get("FloorReached")
    display_entered = stored + 1 if isinstance(stored, int) else None
    if bosses & set(ROUTE_FINAL_IDS):
        return TopFloor(12, "12 (Win+)", display_entered)
    if bosses & ROUTE_DRAGON_IDS:
        return TopFloor(11, "11 (Dragon)", display_entered)
    if DEATH_ID in bosses:
        return TopFloor(10, "10 (Death)", display_entered)
    regular = len([b for b in bosses if 0 <= b <= 17])
    rank = max(0, min(9, regular))
    return TopFloor(rank, str(rank), display_entered)

def parse_run(run: dict[str, Any]) -> RunMetric:
    tf = top_floor_beaten(run)
    return RunMetric(
        character_id=int(run.get("PlayedClass", -1)),
        cinder=int(run.get("CinderLevel", 0)),
        bosses=bosses_from(run),
        stored_floor=run.get("FloorReached") if isinstance(run.get("FloorReached"), int) else None,
        top_floor=tf,
    )

def is_blank_save(save: dict[str, Any]) -> bool:
    if not save.get("RunRecords"):
        for streak in save.get("CinderStreakHistory", []):
            if isinstance(streak, dict) and (streak.get("deathKills", 0) or streak.get("megaDeathKills", 0) or streak.get("highestUsedCinderThisRun", 0)):
                return False
        return True
    return False

def _read_candidate(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or "RunRecords" not in data or "CinderStreakHistory" not in data:
        return None
    return data

def choose_default_save(paths: Iterable[Path], ids: dict[str, Any] | None = None) -> Path | None:
    valid: list[Path] = []
    for p in paths:
        data = _read_candidate(Path(p))
        if data is not None and not is_blank_save(data):
            valid.append(Path(p))
    if not valid:
        return None
    # newest per slot, then newest overall as default
    valid.sort(key=lambda p: (slot_key(p), p.stat().st_mtime), reverse=True)
    return max(valid, key=lambda p: p.stat().st_mtime)

def slot_key(path: Path) -> str:
    m = re.search(r"Public_Slot(\d+)_Save\d+\.json", path.name)
    return m.group(1) if m else path.stem

def discover_save_dirs() -> list[Path]:
    suffix = Path("AppData") / "LocalLow" / "RubyDev" / "Tiny Rogues"
    dirs: list[Path] = []
    if os.name == "nt":
        user = os.environ.get("USERPROFILE")
        if user:
            dirs.append(Path(user) / suffix)
        root = Path("C:/Users")
        if root.exists():
            dirs.extend(p / suffix for p in root.iterdir() if p.is_dir())
    else:
        home = os.environ.get("HOME")
        if home:
            dirs.append(Path(home))
    dirs.append(Path.cwd())
    return dirs

def discover_save_files() -> list[Path]:
    files: list[Path] = []
    for d in discover_save_dirs():
        if d.exists():
            files.extend(sorted(d.glob("Public_Slot*_Save*.json")))
    return files

def analyze_save(save: dict[str, Any], ids: dict[str, Any]) -> TrackerModel:
    runs = [parse_run(r) for r in save.get("RunRecords", []) if isinstance(r, dict) and "PlayedClass" in r]
    cids = all_character_ids(ids, save)
    records: list[CharacterRecord] = []
    streaks = save.get("CinderStreakHistory", [])
    for cid in cids:
        name = character_name(ids, cid)
        rec = CharacterRecord(cid, name)
        rec.sources["runs"] = "RunRecords observed detailed run history"
        class_runs = [r for r in runs if r.character_id == cid]
        rec.observed_runs = len(class_runs)
        for run in class_runs:
            rec.top_floor_rank = max(rec.top_floor_rank, run.top_floor.rank)
            if rec.top_floor_rank == run.top_floor.rank:
                rec.top_floor_label = run.top_floor.label
            if run.is_death:
                rec.best_death = max_optional(rec.best_death, run.cinder)
            if run.is_win_plus:
                rec.best_win_plus = max_optional(rec.best_win_plus, run.cinder)
                if run.route_boss == "Eden":
                    rec.best_eden = max_optional(rec.best_eden, run.cinder)
                elif run.route_boss == "Amon":
                    rec.best_amon = max_optional(rec.best_amon, run.cinder)
                elif run.route_boss == "Primal Death":
                    rec.best_primal_death = max_optional(rec.best_primal_death, run.cinder)
        if cid < len(streaks) and isinstance(streaks[cid], dict):
            st = streaks[cid]
            if st.get("deathKills", 0) > 0:
                rec.best_death = max_optional(rec.best_death, int(st.get("highestUsedCinderThisRun", 0)))
                rec.minimum_runs = max(rec.minimum_runs, 1)
                rec.sources["best_death"] = "CinderStreakHistory historical Death clear plus retained RunRecords when present"
        if rec.observed_runs:
            rec.minimum_runs = max(rec.minimum_runs, rec.observed_runs)
        records.append(rec)
    return TrackerModel(ids, save, runs, records)

def max_optional(a: int | None, b: int) -> int:
    return b if a is None else max(a, b)

def format_cinder(v: int | None) -> str:
    return "—" if v is None else str(v)

def format_rate(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{round(v * 100):.0f}%"

def view3_frontier_highlights(matrix: MatrixModel) -> set[tuple[int, str]]:
    nonzero = [(c, m, cell.count) for (c, m), cell in matrix.cells.items() if cell.count > 0]
    if not nonzero:
        return set()
    rank = {m: i for i, m in enumerate(matrix.milestones)}
    highlights: set[tuple[int, str]] = set()
    max_c = max(c for c, _, _ in nonzero)
    best_m_in_c = max((m for c, m, _ in nonzero if c == max_c), key=lambda m: rank[m])
    highlights.add((max_c, best_m_in_c))
    max_m = max((m for _, m, _ in nonzero), key=lambda m: rank[m])
    best_c_in_m = max(c for c, m, _ in nonzero if m == max_m)
    highlights.add((best_c_in_m, max_m))
    return highlights

def export_csv(model: TrackerModel, path: str | Path, selection: CinderSelection | None = None) -> None:
    selection = selection or CinderSelection.all()
    table = model.completion_rows(selection)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        f.write("view,character_id,character,death,win_plus,eden,amon,primal_death,runs,top_floor\n")
        for r in model.records:
            f.write(f"records,{r.character_id},\"{r.character}\",{format_cinder(r.best_death)},{format_cinder(r.best_win_plus)},{format_cinder(r.best_eden)},{format_cinder(r.best_amon)},{format_cinder(r.best_primal_death)},{r.runs_display},{r.top_floor_label}\n")
        for r in table.rows:
            f.write(f"{table.label},{r.character_id},\"{r.character}\",{r.death_clears},{r.win_plus_clears},{r.eden_clears},{r.amon_clears},{r.primal_death_clears},{r.cx_runs},\n")
