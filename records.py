"""Crash-safe, per-course records for interactive Beaconfall runs."""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

COURSES = ("classic", "mirror", "canyon")
MIN_FREE = 10 * 1024 * 1024
MEDALS = ("GOLD", "SILVER", "BRONZE")
MEDAL_RANK = {"BRONZE": 1, "SILVER": 2, "GOLD": 3}


def _valid_medal(value: object) -> bool:
    return value == "" or value in MEDALS
LAST_FIELDS = ("time", "medal", "hits", "near_misses", "streak")
TOTAL_FIELDS = ("finishes", "golds")
TRACE_MAX = 600
HISTORY_MAX = 5
HISTORY_FIELDS = ("course", "elapsed", "medal")


def _valid_history(value: object) -> bool:
    if not isinstance(value, list) or len(value) > HISTORY_MAX:
        return False
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != set(HISTORY_FIELDS):
            return False
        course, elapsed, medal = entry["course"], entry["elapsed"], entry["medal"]
        if course not in COURSES or medal not in MEDALS:
            return False
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
            return False
        number = float(elapsed)
        if not math.isfinite(number) or number <= 0:
            return False
    return True


def _valid_trace(value: object) -> bool:
    if not isinstance(value, list) or len(value) > TRACE_MAX:
        return False
    for sample in value:
        if (not isinstance(sample, (list, tuple)) or len(sample) != 3
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in sample)
                or any(not math.isfinite(float(v)) for v in sample)):
            return False
    return True


def _valid_totals(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != set(TOTAL_FIELDS):
        return False
    return all(not isinstance(value[field], bool) and isinstance(value[field], int)
               and 0 <= value[field] <= 1000000000 for field in TOTAL_FIELDS)


def _valid_last(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != set(LAST_FIELDS):
        return False
    time = value["time"]
    if isinstance(time, bool) or not isinstance(time, (int, float)) or not math.isfinite(float(time)) or float(time) <= 0:
        return False
    if value["medal"] not in MEDALS:
        return False
    for field in ("hits", "near_misses", "streak"):
        count = value[field]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 or count > 100000:
            return False
    return True


@dataclass(frozen=True)
class RunResult:
    """Everything a completed run contributes to the persistent records."""

    course: str
    elapsed: float
    near_misses: int
    best_streak: int
    splits: dict[int, float]
    last: dict[str, object]
    medal: str
    trace: list[tuple[float, float, float]] | None = None
    distance: float = 0.0
    clean: bool = False


@dataclass(frozen=True)
class Records:
    """All persisted bests: times, near-miss counts, streak peaks and checkpoint splits."""

    times: dict[str, float | None]
    near: dict[str, int]
    streak: dict[str, int]
    splits: dict[str, dict[int, float]]
    last: dict[str, dict[str, object]]
    totals: dict[str, dict[str, int]]
    traces: dict[str, list[tuple[float, float, float]]]
    distance: dict[str, float]
    medals: dict[str, str]
    clean: dict[str, int]
    history: list[dict[str, object]]

    @classmethod
    def empty(cls) -> Records:
        empty_counts = {course: {"finishes": 0, "golds": 0} for course in COURSES}
        return cls(dict.fromkeys(COURSES), dict.fromkeys(COURSES, 0),
                   dict.fromkeys(COURSES, 0), {course: {} for course in COURSES},
                   {course: {} for course in COURSES}, empty_counts,
                   {course: [] for course in COURSES}, dict.fromkeys(COURSES, 0.0),
                   dict.fromkeys(COURSES, ""), dict.fromkeys(COURSES, 0), [])


class RecordError(Exception):
    """Records could not be safely read or updated."""


class _Unsupported(RecordError):
    pass


def _replace(source: Path, target: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.01 * (2 ** attempt))


def _sync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_bytes(path: Path, data: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".records_", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:  # hygiene: allow binary serialized state
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    token = uuid.uuid4().hex
    deadline = time.monotonic() + 3.0
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            try:
                stale = time.time() - lock.stat().st_mtime > 30.0
            except FileNotFoundError:
                continue
            if stale:
                retired = lock.with_name(lock.name + ".stale_" + uuid.uuid4().hex)
                try:
                    os.replace(lock, retired)
                    retired.unlink(missing_ok=True)
                except FileNotFoundError:
                    continue
                continue
            if time.monotonic() >= deadline:
                raise RecordError(f"record lock timed out: {lock}")
            time.sleep(0.05)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(token)
        yield
    finally:
        try:
            if lock.read_text(encoding="utf-8") == token:
                lock.unlink(missing_ok=True)
        except (FileNotFoundError, UnicodeDecodeError):
            print(f"Warning: record lock {lock} disappeared before release.", file=sys.stderr)


def _decode(path: Path) -> Records:
    try:
        if path.stat().st_size > 65536:
            raise ValueError("record file exceeds 64 KiB")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("schema"), int) or isinstance(data["schema"], bool):
        raise ValueError("invalid record envelope")
    if data["schema"] != 1:
        raise _Unsupported(f"unsupported record schema in {path}")
    values = data.get("data")
    if not isinstance(values, dict):
        raise ValueError("invalid record data")
    cleaned = {}
    for course in COURSES:
        value = values.get(course)
        if value is None:
            cleaned[course] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid course record")
        try:
            number = float(value)
        except OverflowError as exc:
            raise ValueError("invalid course record") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError("invalid course record")
        cleaned[course] = number
    near_values = data.get("near", {})
    if not isinstance(near_values, dict):
        raise ValueError("invalid near data")
    near = {}
    for course in COURSES:
        value = near_values.get(course, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 100000:
            raise ValueError("invalid near record")
        near[course] = value
    streak_values = data.get("streak", {})
    if not isinstance(streak_values, dict):
        raise ValueError("invalid streak data")
    streak = {}
    for course in COURSES:
        value = streak_values.get(course, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 100000:
            raise ValueError("invalid streak record")
        streak[course] = value
    splits_values = data.get("splits", {})
    if not isinstance(splits_values, dict):
        raise ValueError("invalid splits data")
    splits = {}
    for course in COURSES:
        raw = splits_values.get(course, {})
        if not isinstance(raw, dict):
            raise ValueError("invalid splits for course")
        cleaned_splits = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not key.isdigit() or not 1 <= int(key) <= 3:
                raise ValueError("invalid split checkpoint")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("invalid split time")
            try:
                number = float(value)
            except OverflowError as exc:
                raise ValueError("invalid split time") from exc
            if not math.isfinite(number) or number <= 0:
                raise ValueError("invalid split time")
            cleaned_splits[int(key)] = number
        splits[course] = cleaned_splits
    last_values = data.get("last", {})
    if not isinstance(last_values, dict):
        raise ValueError("invalid last data")
    last = {}
    for course in COURSES:
        value = last_values.get(course, {})
        if value and not _valid_last(value):
            raise ValueError("invalid last session")
        last[course] = dict(value) if value else {}
    totals_values = data.get("totals", {})
    if not isinstance(totals_values, dict):
        raise ValueError("invalid totals data")
    totals = {}
    for course in COURSES:
        value = totals_values.get(course, {"finishes": 0, "golds": 0})
        if not _valid_totals(value):
            raise ValueError("invalid totals")
        totals[course] = dict(value)
    traces_values = data.get("traces", {})
    if not isinstance(traces_values, dict):
        raise ValueError("invalid traces data")
    traces = {}
    for course in COURSES:
        value = traces_values.get(course, [])
        if not _valid_trace(value):
            raise ValueError("invalid trace")
        traces[course] = [tuple(float(v) for v in sample) for sample in value]
    distance_values = data.get("distance", {})
    if not isinstance(distance_values, dict):
        raise ValueError("invalid distance data")
    distance = {}
    for course in COURSES:
        value = distance_values.get(course, 0.0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid distance record")
        number = float(value)
        if not math.isfinite(number) or number < 0:
            raise ValueError("invalid distance record")
        distance[course] = number
    medals_values = data.get("medals", {})
    if not isinstance(medals_values, dict):
        raise ValueError("invalid medals data")
    medals = {}
    for course in COURSES:
        value = medals_values.get(course, "")
        if not _valid_medal(value):
            raise ValueError("invalid medal record")
        medals[course] = value
    clean_values = data.get("clean", {})
    if not isinstance(clean_values, dict):
        raise ValueError("invalid clean data")
    clean = {}
    for course in COURSES:
        value = clean_values.get(course, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid clean record")
        clean[course] = value
    history = data.get("history", [])
    if not _valid_history(history):
        raise ValueError("invalid history")
    return Records(cleaned, near, streak, splits, last, totals, traces, distance, medals, clean,
                   [dict(entry) for entry in history])


def _read(path: Path) -> Records:
    primary_missing = False
    try:
        return _decode(path)
    except FileNotFoundError:
        primary_missing = True
    except ValueError:
        quarantined = path.with_name(path.name + f".corrupt_{time.time_ns()}")
        _replace(path, quarantined)
        print(f"Warning: invalid records moved to {quarantined}; trying backup.", file=sys.stderr)
    backup = path.with_name(path.name + ".bak")
    try:
        result = _decode(backup)
        if primary_missing:
            print(f"Warning: {path} is missing; using {backup}.", file=sys.stderr)
        return result
    except FileNotFoundError:
        return Records.empty()
    except ValueError:
        quarantined = backup.with_name(backup.name + f".corrupt_{time.time_ns()}")
        _replace(backup, quarantined)
        print(f"Warning: invalid record backup moved to {quarantined}.", file=sys.stderr)
    return Records.empty()


class RecordStore:
    """Read and merge best times under one cross-process lock."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, float | None]:
        try:
            with _locked(self.path):
                return _read(self.path).times
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_near(self) -> dict[str, int]:
        try:
            with _locked(self.path):
                return _read(self.path).near
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_streak(self) -> dict[str, int]:
        try:
            with _locked(self.path):
                return _read(self.path).streak
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_splits(self) -> dict[str, dict[int, float]]:
        try:
            with _locked(self.path):
                return _read(self.path).splits
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_last(self) -> dict[str, dict[str, object]]:
        try:
            with _locked(self.path):
                return _read(self.path).last
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_history(self) -> list[dict[str, object]]:
        try:
            with _locked(self.path):
                return _read(self.path).history
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_clean(self) -> dict[str, int]:
        try:
            with _locked(self.path):
                return _read(self.path).clean
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_medals(self) -> dict[str, str]:
        try:
            with _locked(self.path):
                return _read(self.path).medals
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_distance(self) -> dict[str, float]:
        try:
            with _locked(self.path):
                return _read(self.path).distance
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_traces(self) -> dict[str, list[tuple[float, float, float]]]:
        try:
            with _locked(self.path):
                return _read(self.path).traces
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def load_totals(self) -> dict[str, dict[str, int]]:
        try:
            with _locked(self.path):
                return _read(self.path).totals
        except OSError as exc:
            raise RecordError(f"cannot read records at {self.path}: {exc}") from exc

    def _commit(self, saved: Records) -> None:
        """Encode, back up and atomically write a Records object."""
        if self.path.exists():
            _atomic_bytes(self.path.with_name(self.path.name + ".bak"), self.path.read_bytes())
        encoded_splits = {name: {str(key): value for key, value in value.items()}
                          for name, value in saved.splits.items()}
        encoded_traces = {course: [[round(v, 3) for v in sample] for sample in value]
                          for course, value in saved.traces.items()}
        payload = json.dumps({"schema": 1, "data": saved.times, "near": saved.near,
                              "streak": saved.streak, "splits": encoded_splits,
                              "last": saved.last, "totals": saved.totals, "traces": encoded_traces,
                              "distance": saved.distance, "medals": saved.medals,
                              "clean": saved.clean, "history": saved.history},
                             sort_keys=True, allow_nan=False)
        _atomic_bytes(self.path, (payload + "\n").encode("utf-8"))

    def finish_run(self, result: RunResult) -> Records:
        """Update every best and increment lifetime totals in one atomic write."""
        course, elapsed = result.course, result.elapsed
        near_misses, best_streak = result.near_misses, result.best_streak
        splits, last, medal = result.splits, result.last, result.medal
        trace, distance, clean = result.trace, result.distance, result.clean
        if course not in COURSES or isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
            raise ValueError("invalid course or time")
        if not _valid_last(last) or medal not in MEDALS:
            raise ValueError("invalid last session or medal")
        if trace is not None and not _valid_trace(trace):
            raise ValueError("invalid trace")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise ValueError("invalid distance")
        distance_value = float(distance)
        if not math.isfinite(distance_value) or distance_value < 0:
            raise ValueError("invalid distance")
        try:
            number = float(elapsed)
        except OverflowError as exc:
            raise ValueError("record time must be finite and positive") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError("record time must be finite and positive")
        if shutil.disk_usage(self.path.parent).free < MIN_FREE:
            raise RecordError(f"not enough free space for records at {self.path}")
        try:
            with _locked(self.path):
                saved = _read(self.path)
                if saved.times[course] is None or saved.times[course] > number:
                    saved.times[course] = number
                    if splits:
                        saved.splits[course] = dict(splits)
                    if trace is not None:
                        saved.traces[course] = [tuple(float(v) for v in sample) for sample in trace]
                if near_misses > saved.near[course]:
                    saved.near[course] = near_misses
                if best_streak > saved.streak[course]:
                    saved.streak[course] = best_streak
                saved.last[course] = dict(last)
                saved.totals[course]["finishes"] += 1
                if medal == "GOLD":
                    saved.totals[course]["golds"] += 1
                if clean:
                    saved.clean[course] += 1
                saved.history.append({"course": course, "elapsed": number, "medal": medal})
                if len(saved.history) > HISTORY_MAX:
                    del saved.history[:-HISTORY_MAX]
                saved.distance[course] += distance_value
                if MEDAL_RANK[medal] > MEDAL_RANK.get(saved.medals[course], 0):
                    saved.medals[course] = medal
                self._commit(saved)
                return saved
        except OSError as exc:
            raise RecordError(f"cannot save records at {self.path}: {exc}") from exc

    def record(self, course: str, elapsed: float, near_misses: int | None = None,
               best_streak: int | None = None, splits: dict[int, float] | None = None,
               last: dict[str, object] | None = None, totals: dict[str, int] | None = None) -> dict[str, float | None]:
        new_splits = splits
        if last is not None and not _valid_last(last):
            raise ValueError("invalid last session")
        if totals is not None and not _valid_totals(totals):
            raise ValueError("invalid totals")
        if course not in COURSES or isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
            raise ValueError("invalid course or time")
        if near_misses is not None and (isinstance(near_misses, bool) or not isinstance(near_misses, int)
                                       or near_misses < 0 or near_misses > 100000):
            raise ValueError("invalid near-miss count")
        if best_streak is not None and (isinstance(best_streak, bool) or not isinstance(best_streak, int)
                                       or best_streak < 0 or best_streak > 100000):
            raise ValueError("invalid streak")
        if splits is not None and (not isinstance(splits, dict)
                                   or any(not isinstance(k, int) or not 1 <= k <= 3
                                          or isinstance(v, bool) or not isinstance(v, (int, float))
                                          or not math.isfinite(float(v)) or float(v) <= 0
                                          for k, v in splits.items())):
            raise ValueError("invalid splits")
        try:
            number = float(elapsed)
        except OverflowError as exc:
            raise ValueError("record time must be finite and positive") from exc
        if not math.isfinite(number) or number <= 0:
            raise ValueError("record time must be finite and positive")
        try:
            with _locked(self.path):
                saved = _read(self.path)
                records, near = saved.times, saved.near
                streak, splits = saved.streak, saved.splits
                time_improved = records[course] is None or records[course] > number
                near_improved = near_misses is not None and near_misses > near[course]
                streak_improved = best_streak is not None and best_streak > streak[course]
                if not (time_improved or near_improved or streak_improved or last is not None
                        or totals is not None):
                    return records
                if shutil.disk_usage(self.path.parent).free < MIN_FREE:
                    raise RecordError(f"not enough free space for records at {self.path}")
                if time_improved:
                    records[course] = number
                    if new_splits:
                        splits[course] = dict(new_splits)
                if near_improved:
                    near[course] = near_misses
                if streak_improved:
                    streak[course] = best_streak
                if last is not None:
                    saved.last[course] = dict(last)
                if totals is not None:
                    saved.totals[course] = dict(totals)
                self._commit(saved)
                return records
        except OSError as exc:
            raise RecordError(f"cannot save records at {self.path}: {exc}") from exc
