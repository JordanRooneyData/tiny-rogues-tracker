from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import cmp_to_key
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

VIEW_CINDER_HIGHSCORES = "Cinder Highscores"
VIEW_KILL_COUNTS = "Kill Counts"
VIEW_SURVIVAL_BREAKDOWN = "Survival Breakdown"

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
        return f"C{self.low}–{self.high}"

    @property
    def display_text(self) -> str:
        return f"Cinder filter: {self.label}"

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
class SfmTableState:
    """Pure state model for Screenshot Friendly Mode's three-step workflow."""
    state: str = "normal"
    selected_rows: set[int] = field(default_factory=set)
    selected_cols: set[int] = field(default_factory=set)
    row_anchor: int | None = None
    col_anchor: int | None = None
    message: str = "SFM inactive. Press SFM to choose rows and columns for a compact screenshot table."

    def press(self, auto_select_first_col: bool = True) -> "SfmTableState":
        if self.state == "normal":
            self.state = "selection"
            if auto_select_first_col:
                self.selected_cols.add(0)
                self.col_anchor = 0
            self.message = "SFM SELECTION HAS BEEN ACTIVATED. Click row and column headers; selected intersections will be highlighted."
        elif self.state == "selection":
            if not self.selected_rows or not self.selected_cols:
                self.message = "SFM SELECTION HAS BEEN ACTIVATED. Select at least one row and one column to create a compact table."
            else:
                self.state = "compact"
                self.message = "Compact screenshot mode is active. Press SFM again to restore the full table."
        else:
            self.exit_to_normal()
        return self

    def exit_to_normal(self) -> "SfmTableState":
        self.state = "normal"
        self.selected_rows.clear()
        self.selected_cols.clear()
        self.row_anchor = None
        self.col_anchor = None
        self.message = "SFM inactive. Press SFM to choose rows and columns for a compact screenshot table."
        return self

    def _toggle_or_range(self, selected: set[int], value: int, anchor: int | None, shift: bool) -> int:
        if shift and anchor is not None:
            lo, hi = sorted((anchor, value))
            header_range = set(range(lo, hi + 1))
            if anchor in selected:
                selected.update(header_range)
            else:
                selected.difference_update(header_range)
            return anchor
        if value in selected:
            selected.remove(value)
        else:
            selected.add(value)
        return value

    def toggle_row(self, row: int, shift: bool = False) -> None:
        if self.state != "selection":
            return
        self.row_anchor = self._toggle_or_range(self.selected_rows, row, self.row_anchor, shift)

    def toggle_col(self, col: int, shift: bool = False) -> None:
        if self.state != "selection":
            return
        self.col_anchor = self._toggle_or_range(self.selected_cols, col, self.col_anchor, shift)

    def highlighted_cells(self) -> set[tuple[int, int]]:
        if self.state != "selection":
            return set()
        return {(r, c) for r in self.selected_rows for c in self.selected_cols}

    def compact_shape(self, rows: list[Any], cols: list[Any], values: list[list[Any]]) -> tuple[list[Any], list[Any], list[list[Any]]] | None:
        if self.state != "compact" or not self.selected_rows or not self.selected_cols:
            return None
        rs = sorted(self.selected_rows)
        cs = sorted(self.selected_cols)
        return [rows[r] for r in rs], [cols[c] for c in cs], [[values[r][c] for c in cs] for r in rs]

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
            return str(max(self.observed_runs, self.minimum_runs)) if self.minimum_runs > self.observed_runs else str(self.observed_runs)
        if self.minimum_runs:
            return "≥1"
        return "0"

    @property
    def runs_tooltip(self) -> str:
        if self.minimum_runs > self.observed_runs:
            return "Retained RunRecords plus at least one historical Death clear from CinderStreakHistory; exact historical run count may be higher."
        if self.observed_runs:
            return f"Exact retained RunRecords count: {self.observed_runs}."
        if self.minimum_runs:
            return "Historical Death clear exists in CinderStreakHistory, but detailed retained RunRecords do not contain the run; exact run count is unknown."
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
    inferred_historical_death_runs: int = 0

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

@dataclass(frozen=True)
class CinderHistoryClassification:
    history_length: int
    variation_count: int
    core_slots: set[int]
    quarantined_slots: set[int]
    warnings: list[str]

def completion_totals(rows: list[CompletionRow]) -> CompletionRow:
    total = CompletionRow("TOTALS", -1)
    for row in rows:
        total.cx_runs += row.cx_runs
        total.death_clears += row.death_clears
        total.win_plus_clears += row.win_plus_clears
        total.eden_clears += row.eden_clears
        total.amon_clears += row.amon_clears
        total.primal_death_clears += row.primal_death_clears
        total.inferred_historical_death_runs += row.inferred_historical_death_runs
    return total

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
    mode: str = "Deaths"

@dataclass
class MatrixPresentation:
    headers: list[str]
    row_labels: list[str]
    values: list[list[int | str]]
    fixed_bottom_rows: int = 2

DEATHS_MODE = "Deaths"
FLOORS_COMPLETED_MODE = "Floors Completed"
DEATHS_MILESTONES = [str(i) for i in range(1, 10)] + ["10 (Death's Castle)", "11 (Dragon Floor)", "12 (Deity Floor)", "Win+"]
FLOORS_COMPLETED_MILESTONES = DEATHS_MILESTONES[:-1]

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
        recorded_death_by_class_cinder: set[tuple[int, int]] = set()
        for run in self.runs:
            if run.is_death:
                recorded_death_by_class_cinder.add((run.character_id, run.cinder))
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
        # Merge only verified minimum historical Death-clear evidence absent from retained RunRecords.
        # History slots never create rows; only RunRecords may create unknown-ID diagnostics.
        for cid, cinder in historical_death_cinders(self.save, self.ids):
            if cid not in by_id or not selection.contains(cinder) or (cid, cinder) in recorded_death_by_class_cinder:
                continue
            row = by_id[cid]
            row.cx_runs += 1
            row.death_clears += 1
            row.inferred_historical_death_runs += 1
        return CompletionTable(selection.label, rows)

    def character_record_highlights(self) -> set[tuple[str, str]]:
        columns = ["best_death", "best_win_plus", "best_eden", "best_amon", "best_primal_death", "top_floor_rank"]
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

    def matrix_for_character(self, character: str | int, mode: str = DEATHS_MODE) -> MatrixModel:
        aggregate = isinstance(character, str) and character.upper() == "ALL"
        if aggregate:
            cid = None
            name = "ALL"
        elif isinstance(character, str) and not character.isdigit():
            cid = next((r.character_id for r in self.records if r.character == character), None)
            if cid is None:
                raise KeyError(character)
            name = character_name(self.ids, cid)
        else:
            cid = int(character)
            name = character_name(self.ids, cid)
        mode = FLOORS_COMPLETED_MODE if mode == FLOORS_COMPLETED_MODE else DEATHS_MODE
        milestones = FLOORS_COMPLETED_MILESTONES if mode == FLOORS_COMPLETED_MODE else DEATHS_MILESTONES
        cinders = list(range(17))
        cells = {(c, m): MatrixCell(c, m) for c in cinders for m in milestones}
        for run in self.runs:
            if (not aggregate and run.character_id != cid) or run.cinder not in cinders:
                continue
            if mode == DEATHS_MODE:
                label = death_mode_label(run)
                cells[(run.cinder, label)].count += 1
                cells[(run.cinder, label)].route_boss = run.route_boss
            else:
                for label in completed_floor_labels(run):
                    cells[(run.cinder, label)].count += 1
                    cells[(run.cinder, label)].route_boss = run.route_boss
        return MatrixModel(name, milestones, cinders, cells, mode)

def matrix_format_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "—"
    return f"{(numerator / denominator) * 100:.1f}%"

def matrix_presentation(matrix: MatrixModel, columns_reversed: bool = False, rows_reversed: bool = False) -> MatrixPresentation:
    cinders = list(matrix.cinders)
    if columns_reversed:
        cinders = list(reversed(cinders))
    body_labels = list(matrix.milestones)
    if rows_reversed:
        body_labels = list(reversed(body_labels))
    headers = [f"C{c}" for c in cinders] + ["Totals"]
    values: list[list[int | str]] = []
    for label in body_labels:
        counts = [matrix.cells[(c, label)].count for c in cinders]
        values.append(counts + [sum(counts)])
    if matrix.mode != DEATHS_MODE:
        return MatrixPresentation(headers, body_labels, values, fixed_bottom_rows=0)
    death_rate_labels = ["11 (Dragon Floor)", "12 (Deity Floor)", "Win+"]
    death_rates: list[int | str] = []
    win_rates: list[int | str] = []
    for c in cinders:
        attempts = sum(matrix.cells[(c, label)].count for label in matrix.milestones)
        ended_after_death = sum(matrix.cells[(c, label)].count for label in death_rate_labels if label in matrix.milestones)
        win_plus = matrix.cells[(c, "Win+")].count if "Win+" in matrix.milestones else 0
        death_rates.append(matrix_format_rate(ended_after_death, attempts))
        win_rates.append(matrix_format_rate(win_plus, attempts))
    total_attempts = sum(sum(matrix.cells[(c, label)].count for label in matrix.milestones) for c in cinders)
    total_after_death = sum(matrix.cells[(c, label)].count for c in cinders for label in death_rate_labels if label in matrix.milestones)
    total_win = sum(matrix.cells[(c, "Win+")].count for c in cinders) if "Win+" in matrix.milestones else 0
    row_labels = body_labels + ["Death Kill Rate", "Win+ Rate"]
    values.extend([death_rates + [matrix_format_rate(total_after_death, total_attempts)], win_rates + [matrix_format_rate(total_win, total_attempts)]])
    return MatrixPresentation(headers, row_labels, values, fixed_bottom_rows=2)

class SortState:
    """Stable table sorting: descending -> ascending -> default."""
    def __init__(self) -> None:
        self.column: str | None = None
        self.direction = 0  # 0 default, 1 descending, 2 ascending

    @property
    def indicator(self) -> str:
        return "" if self.direction == 0 else ("▼" if self.direction == 1 else "▲")

    def click(self, rows: list[dict[str, Any]], column: str) -> list[dict[str, Any]]:
        if self.column != column:
            self.column = column
            self.direction = 1
        else:
            self.direction = {1: 2, 2: 0, 0: 1}[self.direction]
        return self.apply(rows)

    def apply(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.direction == 0 or self.column is None:
            return sorted(rows, key=lambda r: r.get("_order", 0))
        reverse_primary = self.direction == 1
        col = self.column
        def cmp(a: dict[str, Any], b: dict[str, Any]) -> int:
            ak, bk = sort_key(a.get(col)), sort_key(b.get(col))
            if ak < bk:
                primary = -1
            elif ak > bk:
                primary = 1
            else:
                primary = 0
            if reverse_primary:
                primary = -primary
            if primary:
                return primary
            return (a.get("_order", 0) > b.get("_order", 0)) - (a.get("_order", 0) < b.get("_order", 0))
        return sorted(rows, key=cmp_to_key(cmp))

def sort_key(v: Any) -> tuple[int, Any]:
    if v in (None, "—"):
        return (0, -1)
    if isinstance(v, (int, float)):
        return (1, v)
    text = str(v).strip().replace("≥", "").replace("+", "")
    if text.endswith("%"):
        text = text[:-1]
    m = re.match(r"^-?\d+(?:\.\d+)?", text)
    if m:
        return (1, float(m.group(0)))
    return (2, text.lower())

def load_ids(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def character_name(ids: dict[str, Any], cid: int) -> str:
    meta = ids.get("characters", {}).get(str(cid), {})
    if isinstance(meta, dict) and meta.get("name"):
        return str(meta["name"])
    return f"Unknown PlayedClass ID {cid}"

def canonical_character_ids(ids: dict[str, Any]) -> set[int]:
    roster = ids.get("character_roster")
    if isinstance(roster, list):
        return {cid for raw in roster if (cid := _int_or_none(raw)) is not None}
    chars = ids.get("characters", {})
    if isinstance(chars, dict):
        return {cid for raw in chars.keys() if (cid := _int_or_none(raw)) is not None}
    return set()

def cinder_history_slot_map(ids: dict[str, Any]) -> dict[int, int]:
    raw = ids.get("cinder_history_slots")
    out: dict[int, int] = {}
    if isinstance(raw, dict):
        for cid_raw, slot_raw in raw.items():
            cid = _int_or_none(cid_raw)
            slot = _int_or_none(slot_raw)
            if cid is not None and slot is not None and slot >= 0:
                out[cid] = slot
        return out
    chars = ids.get("characters", {})
    if isinstance(chars, dict):
        for cid_raw, meta in chars.items():
            if not isinstance(meta, dict):
                continue
            cid = _int_or_none(cid_raw)
            slot = _int_or_none(meta.get("cinder_history_slot"))
            if cid is not None and slot is not None and slot >= 0:
                out[cid] = slot
    return out

def mapping_adapter_used(ids: dict[str, Any]) -> str:
    adapters = ids.get("class_mapping_adapters")
    if isinstance(adapters, list) and adapters and isinstance(adapters[0], dict):
        return str(adapters[0].get("adapter_id") or adapters[0].get("build_id") or "bundled")
    return "bundled ids.json"

def all_character_ids(ids: dict[str, Any], save: dict[str, Any]) -> list[int]:
    out = set(canonical_character_ids(ids))
    for r in save.get("RunRecords", []):
        if not isinstance(r, dict) or "PlayedClass" not in r:
            continue
        cid = _int_or_none(r.get("PlayedClass"))
        if cid is not None:
            out.add(cid)
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

def death_floor_number(run: RunMetric) -> int:
    """Adjusted recorded run-ending floor, independent of ordinary boss kills."""
    if run.stored_floor is None:
        return 1
    floor = max(1, min(12, int(run.stored_floor) + 1))
    if floor == 10 and run.is_death and not run.is_win_plus:
        # Tiny Rogues can store a Death kill as an end on Death's Castle when the
        # next-floor progression gate has not yet opened; display that as the run
        # ending after floor 10 rather than as an ordinary floor-10 death.
        return 11
    return floor

def floor_label(floor: int) -> str:
    if floor == 10:
        return "10 (Death's Castle)"
    if floor == 11:
        return "11 (Dragon Floor)"
    if floor == 12:
        return "12 (Deity Floor)"
    return str(floor)

def death_mode_label(run: RunMetric) -> str:
    if run.is_win_plus:
        return "Win+"
    return floor_label(death_floor_number(run))

def completed_floor_labels(run: RunMetric) -> list[str]:
    if run.is_win_plus:
        return list(FLOORS_COMPLETED_MILESTONES)
    end_floor = death_floor_number(run)
    return [floor_label(f) for f in range(1, end_floor)]

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

def classify_cinder_history_slots(save: dict[str, Any], ids: dict[str, Any]) -> CinderHistoryClassification:
    streaks = save.get("CinderStreakHistory", [])
    history_length = len(streaks) if isinstance(streaks, list) else 0
    variations = save.get("DoppelgangerVariationWins", [])
    variation_count = len(variations) if isinstance(variations, list) else 0
    mapped_slots = {slot for slot in cinder_history_slot_map(ids).values() if 0 <= slot < history_length}
    all_slots = set(range(history_length))
    warnings: list[str] = []
    if not cinder_history_slot_map(ids):
        warnings.append("CinderStreakHistory slot mapping is not verified; historical Death augmentation disabled.")
    quarantined = all_slots - mapped_slots
    if quarantined:
        warnings.append(f"{len(quarantined)} CinderStreakHistory slots are variation/reserved/unmapped and were quarantined from the normal roster.")
    expected = len(mapped_slots) + variation_count
    if variation_count and history_length != expected:
        warnings.append(f"CinderStreakHistory length {history_length} does not equal mapped core slots {len(mapped_slots)} plus DoppelgangerVariationWins {variation_count}; tail ordering was not assumed.")
    return CinderHistoryClassification(history_length, variation_count, mapped_slots, quarantined, warnings)

def historical_death_cinders(save: dict[str, Any], ids: dict[str, Any]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    streaks = save.get("CinderStreakHistory", [])
    if not isinstance(streaks, list):
        return out
    for cid, slot in sorted(cinder_history_slot_map(ids).items()):
        if slot >= len(streaks):
            continue
        st = streaks[slot]
        if not isinstance(st, dict) or st.get("deathKills", 0) <= 0:
            continue
        cinder = _int_or_none(st.get("highestUsedCinderThisRun", 0))
        if cinder is not None:
            out.append((cid, cinder))
    return out

def build_mapping_diagnostics(save: dict[str, Any], ids: dict[str, Any], game_assembly_sha256: str | None = None, global_metadata_sha256: str | None = None) -> dict[str, Any]:
    runs = [r for r in save.get("RunRecords", []) if isinstance(r, dict) and "PlayedClass" in r]
    played_ids = sorted({cid for r in runs if (cid := _int_or_none(r.get("PlayedClass"))) is not None})
    canonical = canonical_character_ids(ids)
    classification = classify_cinder_history_slots(save, ids)
    warnings = list(classification.warnings)
    unknown = [cid for cid in played_ids if cid not in canonical]
    if unknown:
        warnings.append(f"Unknown PlayedClass IDs in RunRecords: {', '.join(map(str, unknown))}.")
    return {
        "app_version": VERSION,
        "save_schema_summary": "RunRecords authoritative; CinderStreakHistory augments only verified core slots; Doppelganger/reserved history slots quarantined.",
        "run_records": len(runs),
        "distinct_played_class_ids": played_ids,
        "cinder_streak_history_length": classification.history_length,
        "doppelganger_variation_wins_length": classification.variation_count,
        "detected_core_history_length": len(classification.core_slots) if classification.core_slots else None,
        "quarantined_history_slots_count": len(classification.quarantined_slots),
        "build_hashes": {"game_assembly_sha256": game_assembly_sha256, "global_metadata_sha256": global_metadata_sha256},
        "mapping_adapter_used": mapping_adapter_used(ids),
        "unknown_run_ids": unknown,
        "mapping_warnings": warnings,
    }

def format_mapping_diagnostics(report: dict[str, Any]) -> str:
    lines = [
        f"Tiny Rogues Tracker v{report.get('app_version', VERSION)} diagnostics",
        f"RunRecords: {report.get('run_records', 0)}",
        f"PlayedClass IDs: {report.get('distinct_played_class_ids', [])}",
        f"CinderStreakHistory length: {report.get('cinder_streak_history_length', 0)}",
        f"DoppelgangerVariationWins length: {report.get('doppelganger_variation_wins_length', 0)}",
        f"Detected core history slots: {report.get('detected_core_history_length')}",
        f"Quarantined history slots: {report.get('quarantined_history_slots_count', 0)}",
        f"Mapping adapter: {report.get('mapping_adapter_used', 'unknown')}",
        f"Unknown run IDs: {report.get('unknown_run_ids', [])}",
    ]
    hashes = report.get("build_hashes") or {}
    if hashes.get("game_assembly_sha256") or hashes.get("global_metadata_sha256"):
        lines.append(f"GameAssembly SHA256: {hashes.get('game_assembly_sha256') or 'unavailable'}")
        lines.append(f"global-metadata SHA256: {hashes.get('global_metadata_sha256') or 'unavailable'}")
    warnings = report.get("mapping_warnings") or []
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {w}" for w in warnings)
    return "\n".join(lines)

def analyze_save(save: dict[str, Any], ids: dict[str, Any]) -> TrackerModel:
    runs = [parse_run(r) for r in save.get("RunRecords", []) if isinstance(r, dict) and "PlayedClass" in r]
    cids = all_character_ids(ids, save)
    records: list[CharacterRecord] = []
    streaks = save.get("CinderStreakHistory", [])
    history_slots = cinder_history_slot_map(ids)
    for cid in cids:
        name = character_name(ids, cid)
        rec = CharacterRecord(cid, name)
        rec.sources["runs"] = "Recorded Runs are detailed retained RunRecords; CinderStreakHistory may add minimum historical Death clears."
        class_runs = [r for r in runs if r.character_id == cid]
        rec.observed_runs = len(class_runs)
        for run in class_runs:
            if run.top_floor.rank > rec.top_floor_rank:
                rec.top_floor_rank = run.top_floor.rank
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
        slot = history_slots.get(cid)
        if isinstance(streaks, list) and slot is not None and slot < len(streaks) and isinstance(streaks[slot], dict):
            st = streaks[slot]
            if st.get("deathKills", 0) > 0:
                rec.best_death = max_optional(rec.best_death, int(st.get("highestUsedCinderThisRun", 0)))
                rec.minimum_runs = max(rec.minimum_runs, rec.observed_runs + (0 if any(r.is_death and r.cinder == int(st.get("highestUsedCinderThisRun", 0)) for r in class_runs) else 1))
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
        f.write("view,character_id,character,death,win_plus,eden,amon,primal_death,top_floor_beaten\n")
        for r in model.records:
            f.write(f"cinder_highscores,{r.character_id},\"{r.character}\",{format_cinder(r.best_death)},{format_cinder(r.best_win_plus)},{format_cinder(r.best_eden)},{format_cinder(r.best_amon)},{format_cinder(r.best_primal_death)},{r.top_floor_label}\n")
        f.write(f"view,filter,character_id,character,death_kills,win_plus_kills,eden_kills,amon_kills,primal_death_kills\n")
        for r in table.rows:
            f.write(f"kill_counts,{table.label},{r.character_id},\"{r.character}\",{r.death_clears},{r.win_plus_clears},{r.eden_clears},{r.amon_clears},{r.primal_death_clears}\n")
