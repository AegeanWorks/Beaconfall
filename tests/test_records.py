import json
import io
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from records import RecordError, RecordStore, RunResult
from live_game import LiveGame
from keystone.input import ActionState
from play import engine_root, game_spec


class RecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "records.json"
        self.store = RecordStore(self.path)

    def test_records_merge_across_instances_and_keep_fastest_per_course(self):
        first = RecordStore(self.path)
        second = RecordStore(self.path)
        self.assertEqual(first.load(), {"classic": None, "mirror": None, "canyon": None})
        first.record("classic", 20.0)
        second.record("mirror", 18.0)
        first.record("classic", 22.0)
        self.assertEqual(second.load(), {"classic": 20.0, "mirror": 18.0, "canyon": None})

    def test_canyon_record_round_trips_with_an_older_two_course_file(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None}}), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": 20.0, "mirror": None, "canyon": None})
        self.store.record("canyon", 17.5)
        self.assertEqual(self.store.load()["canyon"], 17.5)

    def test_near_miss_bests_round_trip_and_old_files_load(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_near(), {"classic": 0, "mirror": 0, "canyon": 0})
        self.store.record("classic", 20.0, near_misses=3)
        self.assertEqual(self.store.load_near(), {"classic": 3, "mirror": 0, "canyon": 0})
        self.store.record("classic", 25.0, near_misses=5)
        self.assertEqual(self.store.load()["classic"], 20.0)
        self.assertEqual(self.store.load_near()["classic"], 5)
        self.store.record("classic", 19.0, near_misses=1)
        self.assertEqual(self.store.load_near()["classic"], 5)

    def test_invalid_near_miss_value_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "near": {"classic": -2}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_persists_near_miss_bests(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.near_misses = 4
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
        game.update(0.1, ActionState())
        self.assertEqual(self.store.load_near()["classic"], 4)
        self.assertEqual(LiveGame(self.store).best_nears["classic"], 4)

    def test_both_primary_and_backup_corrupt_yields_empty_records(self):
        self.path.write_bytes(b"not json")
        self.path.with_name(self.path.name + ".bak").write_bytes(b"also not json")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(self.store.load_near(), {"classic": 0, "mirror": 0, "canyon": 0})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)
        self.assertEqual(len(list(self.path.parent.glob("records.json.bak.corrupt_*"))), 1)

    def test_run_history_defaults_is_bounded_and_ordered(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_history(), [])
        summary = {"time": 20.0, "medal": "SILVER", "hits": 0, "near_misses": 0, "streak": 0}
        for elapsed in (20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0):
            self.store.finish_run(RunResult("classic", elapsed, 0, 0, {}, summary, "SILVER"))
        history = self.store.load_history()
        self.assertEqual(len(history), 5)
        self.assertEqual([entry["elapsed"] for entry in history],
                         [18.0, 17.0, 16.0, 15.0, 14.0])

    def test_invalid_history_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "history": [{"course": "bogus", "elapsed": 1.0, "medal": "GOLD"}]}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_run_history_shown_on_ready_screen(self):
        from keystone.input import ActionState as _AS
        game = LiveGame(self.store)
        game.run_history = [{"course": "classic", "elapsed": 17.5, "medal": "GOLD"}]
        class Canvas:
            def __init__(self):
                self.labels = []
            def text(self, x, y, text, color, scale):
                self.labels.append(text)
        canvas = Canvas()
        game.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("LAST CLASSIC 17.5s GOLD" in label for label in canvas.labels))

    def test_live_game_restores_run_history(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 17.0, 3
        game.update(0.1, ActionState())
        self.assertEqual(len(LiveGame(self.store).run_history), 1)
        self.assertEqual(LiveGame(self.store).run_history[0]["course"], "classic")

    def test_clean_finishes_default_and_accumulate(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_clean(), {"classic": 0, "mirror": 0, "canyon": 0})
        summary = {"time": 20.0, "medal": "SILVER", "hits": 0, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 20.0, 0, 0, {}, summary, "SILVER", clean=True))
        self.assertEqual(self.store.load_clean()["classic"], 1)
        dirty = {"time": 22.0, "medal": "BRONZE", "hits": 2, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 22.0, 0, 0, {}, dirty, "BRONZE", clean=False))
        self.assertEqual(self.store.load_clean()["classic"], 1)
        self.assertEqual(self.store.load_clean()["mirror"], 0)

    def test_invalid_clean_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "clean": {"classic": -1}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_persists_clean_finishes(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 17.0, 3
        game.update(0.1, ActionState())
        self.assertEqual(self.store.load_clean()["classic"], 1)
        self.assertEqual(LiveGame(self.store).clean_finishes["classic"], 1)

    def test_best_medal_defaults_and_improves_only(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_medals(), {"classic": "", "mirror": "", "canyon": ""})
        summary = {"time": 20.0, "medal": "SILVER", "hits": 0, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 20.0, 0, 0, {}, summary, "SILVER"))
        self.assertEqual(self.store.load_medals()["classic"], "SILVER")
        gold = {"time": 17.0, "medal": "GOLD", "hits": 0, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 17.0, 0, 0, {}, gold, "GOLD"))
        self.assertEqual(self.store.load_medals()["classic"], "GOLD")
        bronze = {"time": 25.0, "medal": "BRONZE", "hits": 5, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 25.0, 0, 0, {}, bronze, "BRONZE"))
        self.assertEqual(self.store.load_medals()["classic"], "GOLD")
        self.assertEqual(self.store.load_medals()["mirror"], "")

    def test_invalid_medal_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "medals": {"classic": "PLATINUM"}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_restores_best_medal(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 17.0, 3
        game.update(0.1, ActionState())
        self.assertEqual(self.store.load_medals()["classic"], "GOLD")
        self.assertEqual(LiveGame(self.store).best_medals["classic"], "GOLD")

    def test_finish_run_accepts_a_run_result(self):
        result = RunResult(
            course="classic", elapsed=19.0, near_misses=4, best_streak=3,
            splits={1: 4.0, 2: 8.0, 3: 12.0},
            last={"time": 19.0, "medal": "GOLD", "hits": 0, "near_misses": 4, "streak": 3},
            medal="GOLD", trace=[(0.0, 0.0, 0.0), (1.0, 2.0, 10.0)], distance=400.0)
        self.store.finish_run(result)
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["data"]["classic"], 19.0)
        self.assertEqual(saved["totals"]["classic"], {"finishes": 1, "golds": 1})
        self.assertEqual(saved["distance"]["classic"], 400.0)

    def test_lifetime_distance_defaults_and_accumulates(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_distance(), {"classic": 0.0, "mirror": 0.0, "canyon": 0.0})
        summary = {"time": 20.0, "medal": "SILVER", "hits": 0, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 20.0, 0, 0, {}, summary, "SILVER",
                                        distance=400.0))
        self.store.finish_run(RunResult("classic", 22.0, 0, 0, {}, summary, "SILVER",
                                        distance=150.0))
        self.assertEqual(self.store.load_distance(), {"classic": 550.0, "mirror": 0.0, "canyon": 0.0})

    def test_invalid_distance_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "distance": {"classic": -1}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_accumulates_distance(self):
        for elapsed in (20.0, 19.0):
            game = LiveGame(self.store)
            game.update(0, ActionState(pressed={"start"}))
            game.skip_countdown()
            game.distance = 200.0
            game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, elapsed, 3
            game.update(0.1, ActionState())
        self.assertAlmostEqual(LiveGame(self.store).lifetime_distance["classic"], 800.0, places=0)

    def test_ghost_trace_round_trips_and_old_files_load(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_traces(), {"classic": [], "mirror": [], "canyon": []})
        trace = [(0.0, 0.0, 0.0), (1.0, 2.0, 10.0), (2.0, 4.0, 20.0)]
        summary = {"time": 20.0, "medal": "SILVER", "hits": 0, "near_misses": 0, "streak": 0}
        self.store.finish_run(RunResult("classic", 19.0, 0, 0,
                                        {1: 5.0, 2: 9.0, 3: 13.0}, summary, "SILVER", trace))
        self.assertEqual(self.store.load_traces()["classic"], trace)

    def test_ghost_trace_is_capped_and_invalid_values_quarantine(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "traces": {"classic": [[0.0, 0.0]]}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        # A single incomplete sample is invalid.
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_restores_the_ghost_trace(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        trace = [(0.0, 0.0, 0.0), (1.0, 2.0, 10.0)]
        game.current_trace = trace
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
        game.update(0.1, ActionState())
        self.assertEqual(LiveGame(self.store).best_traces["classic"], trace)

    def test_lifetime_totals_round_trip_and_old_files_load(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_totals(), {"classic": {"finishes": 0, "golds": 0},
                                                    "mirror": {"finishes": 0, "golds": 0},
                                                    "canyon": {"finishes": 0, "golds": 0}})
        self.store.record("classic", 20.0, totals={"finishes": 5, "golds": 2})
        self.assertEqual(self.store.load_totals()["classic"], {"finishes": 5, "golds": 2})

    def test_invalid_totals_are_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "totals": {"classic": {"finishes": -1, "golds": 0}}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_accumulates_lifetime_totals(self):
        for _ in range(2):
            game = LiveGame(self.store)
            game.update(0, ActionState(pressed={"start"}))
            game.skip_countdown()
            game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 17.5, 3
            game.update(0.1, ActionState())
        totals = self.store.load_totals()["classic"]
        self.assertEqual(totals["finishes"], 2)
        self.assertEqual(totals["golds"], 2)
        self.assertEqual(LiveGame(self.store).lifetime_totals["classic"], totals)

    def test_both_write_paths_produce_the_same_json_shape(self):
        import json as _json
        self.store.record("classic", 20.0, near_misses=3, best_streak=2,
                          splits={1: 5.0, 2: 9.0, 3: 13.0},
                          last={"time": 20.0, "medal": "SILVER", "hits": 1,
                                "near_misses": 3, "streak": 2},
                          totals={"finishes": 1, "golds": 0})
        record_keys = set(_json.loads(self.path.read_text(encoding="utf-8")))
        summary = {"time": 19.0, "medal": "GOLD", "hits": 0, "near_misses": 4, "streak": 3}
        self.store.finish_run(RunResult("classic", 19.0, 4, 3,
                                        {1: 4.0, 2: 8.0, 3: 12.0}, summary, "GOLD"))
        finish_keys = set(_json.loads(self.path.read_text(encoding="utf-8")))
        expected = {"clean", "data", "distance", "history", "last", "medals", "near", "schema", "splits", "streak", "totals", "traces"}
        self.assertEqual(record_keys, expected)
        self.assertEqual(finish_keys, expected)

    def test_last_session_round_trips_and_old_files_load(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_last(), {"classic": {}, "mirror": {}, "canyon": {}})
        summary = {"time": 18.5, "medal": "GOLD", "hits": 0, "near_misses": 3, "streak": 2}
        self.store.record("classic", 18.5, last=summary)
        self.assertEqual(self.store.load_last()["classic"], summary)

    def test_invalid_last_session_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "last": {"classic": {"medal": "PLATINUM"}}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_persists_and_restores_last_session(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.near_misses = 2
        game.best_near_streak = 3
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 17.5, 3
        game.update(0.1, ActionState())
        last = self.store.load_last()["classic"]
        self.assertEqual(last["medal"], "GOLD")
        self.assertEqual(last["near_misses"], 2)
        self.assertEqual(last["streak"], 3)
        self.assertEqual(LiveGame(self.store).last_sessions["classic"], last)

    def test_best_splits_round_trip_with_string_keys(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_splits(), {"classic": {}, "mirror": {}, "canyon": {}})
        self.store.record("classic", 19.0, splits={1: 5.0, 2: 9.0, 3: 13.0})
        self.assertEqual(self.store.load_splits()["classic"], {1: 5.0, 2: 9.0, 3: 13.0})

    def test_invalid_split_value_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "splits": {"classic": {"1": -1}}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_restores_persisted_splits(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
        game.current_splits = {1: 5.0, 2: 9.0, 3: 13.0}
        game.update(0.1, ActionState())
        self.assertEqual(self.store.load_splits()["classic"], {1: 5.0, 2: 9.0, 3: 13.0})
        reloaded = LiveGame(self.store)
        self.assertEqual(reloaded.best_splits["classic"], {1: 5.0, 2: 9.0, 3: 13.0})

    def test_best_near_streak_round_trips_and_old_files_load(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 20.0, "mirror": None, "canyon": None}}), encoding="utf-8")
        self.assertEqual(self.store.load_streak(), {"classic": 0, "mirror": 0, "canyon": 0})
        self.store.record("classic", 20.0, best_streak=4)
        self.assertEqual(self.store.load_streak(), {"classic": 4, "mirror": 0, "canyon": 0})
        self.store.record("classic", 25.0, best_streak=2)
        self.assertEqual(self.store.load_streak()["classic"], 4)
        self.store.record("classic", 19.0, best_streak=6)
        self.assertEqual(self.store.load_streak()["classic"], 6)

    def test_invalid_streak_value_is_treated_as_corrupt(self):
        payload = {"schema": 1, "data": {"classic": None, "mirror": None, "canyon": None},
                   "streak": {"classic": -1}}
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_live_game_persists_the_best_streak(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.best_near_streak = 5
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
        game.update(0.1, ActionState())
        self.assertEqual(self.store.load_streak()["classic"], 5)
        self.assertEqual(LiveGame(self.store).best_streak_bests["classic"], 5)

    def test_corrupt_primary_recovers_backup_and_is_quarantined(self):
        self.store.record("classic", 20.0)
        self.store.record("classic", 18.0)
        self.path.write_bytes(b"not json")
        self.assertEqual(self.store.load()["classic"], 20.0)
        self.assertEqual(self.store.load()["classic"], 20.0)
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_empty_file_is_quarantined(self):
        self.path.write_bytes(b"")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_huge_numeric_value_is_treated_as_corrupt(self):
        self.path.write_text(json.dumps({"schema": 1, "data": {"classic": 10 ** 500}}), encoding="utf-8")
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertEqual(len(list(self.path.parent.glob("records.json.corrupt_*"))), 1)

    def test_newer_schema_is_never_overwritten(self):
        payload = json.dumps({"schema": 99, "data": {}}).encode("utf-8")
        self.path.write_bytes(payload)
        with self.assertRaises(RecordError):
            self.store.record("classic", 10.0)
        self.assertEqual(self.path.read_bytes(), payload)

    def test_low_disk_space_does_not_write_record(self):
        with patch("records.shutil.disk_usage", return_value=SimpleNamespace(free=1)):
            with self.assertRaises(RecordError):
                self.store.record("classic", 10.0)
        self.assertFalse(self.path.exists())

    def test_unreadable_record_is_not_quarantined_or_overwritten(self):
        payload = b"important existing data"
        self.path.write_bytes(payload)
        with patch("records._decode", side_effect=PermissionError("denied")):
            with self.assertRaises(RecordError):
                self.store.record("classic", 10.0)
        self.assertEqual(self.path.read_bytes(), payload)
        self.assertEqual(list(self.path.parent.glob("records.json.corrupt_*")), [])

    def test_stale_lock_is_reclaimed(self):
        lock = self.path.with_name(self.path.name + ".lock")
        lock.write_text("old", encoding="utf-8")
        old = time.time() - 31
        os.utime(lock, (old, old))
        self.assertEqual(self.store.load(), {"classic": None, "mirror": None, "canyon": None})
        self.assertFalse(lock.exists())

    def test_live_lock_timeout_does_not_remove_another_writer_lock(self):
        lock = self.path.with_name(self.path.name + ".lock")
        lock.write_text("other", encoding="utf-8")
        with patch("records.time.monotonic", side_effect=[0, 4]):
            with self.assertRaises(RecordError):
                self.store.record("classic", 10)
        self.assertEqual(lock.read_text(encoding="utf-8"), "other")
        self.assertFalse(self.path.exists())

    def test_live_game_survives_home_directory_failure(self):
        with patch("live_game.Path.home", side_effect=RuntimeError("no home")):
            with redirect_stderr(io.StringIO()) as output:
                game = LiveGame()
        self.assertTrue(game.records_warning)
        self.assertEqual(game.state, "ready")
        self.assertIn("Fix:", output.getvalue())

    def test_live_game_persists_and_loads_a_completed_run(self):
        game = LiveGame(self.store)
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
        game.update(0.1, ActionState())
        self.assertEqual(game.state, "finished")
        self.assertAlmostEqual(LiveGame(RecordStore(self.path)).best_time, game.best_time)

    def test_default_live_record_path_is_under_home(self):
        with patch("live_game.Path.home", return_value=self.path.parent):
            game = LiveGame()
            game.update(0, ActionState(pressed={"start"}))
            game.skip_countdown()
            game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
            game.update(0.1, ActionState())
            self.assertTrue((self.path.parent / ".beaconfall" / "records.json").is_file())
            self.assertAlmostEqual(LiveGame().best_time, game.best_time)

    def test_save_failure_keeps_the_game_playable_and_warns(self):
        class BrokenStore:
            def load(self):
                return {"classic": None, "mirror": None, "canyon": None}

            def load_near(self):
                return {"classic": 0, "mirror": 0, "canyon": 0}

            def load_streak(self):
                return {"classic": 0, "mirror": 0, "canyon": 0}

            def load_splits(self):
                return {"classic": {}, "mirror": {}, "canyon": {}}

            def load_traces(self):
                return {"classic": [], "mirror": [], "canyon": []}

            def load_distance(self):
                return {"classic": 0.0, "mirror": 0.0, "canyon": 0.0}

            def load_medals(self):
                return {"classic": "", "mirror": "", "canyon": ""}

            def load_clean(self):
                return {"classic": 0, "mirror": 0, "canyon": 0}

            def load_history(self):
                return []

            def load_last(self):
                return {"classic": {}, "mirror": {}, "canyon": {}}

            def load_totals(self):
                return {course: {"finishes": 0, "golds": 0} for course in ("classic", "mirror", "canyon")}

            def record(self, course, elapsed, near_misses=None, best_streak=None, splits=None,
                       last=None, totals=None):
                raise RecordError("read-only location")

            def finish_run(self, result):
                raise RecordError("read-only location")

        game = LiveGame(BrokenStore())
        game.update(0, ActionState(pressed={"start"}))
        game.skip_countdown()
        game.distance, game.speed, game.elapsed, game.checkpoint = 399.9, 10, 20, 3
        with redirect_stderr(io.StringIO()) as output:
            game.update(0.1, ActionState())
        self.assertEqual(game.state, "finished")
        self.assertIsNotNone(game.best_time)
        self.assertIn("Why:", output.getvalue())
        self.assertIn("Fix:", output.getvalue())
        self.assertTrue(game.records_warning)

    def test_headless_modes_do_not_load_live_records(self):
        self.assertEqual(game_spec([]), "live_game:LiveGame")
        self.assertEqual(game_spec(["--simulate", "--frames", "10"]), "beaconfall:Game")
        self.assertEqual(game_spec(["--verify-determinism"]), "beaconfall:Game")

    def test_launcher_finds_a_vendored_engine_in_an_export(self):
        bundle = self.path.parent / "bundle"
        main = bundle / "vendor" / "keystone" / "__main__.py"
        main.parent.mkdir(parents=True)
        main.write_text("", encoding="utf-8")
        self.assertEqual(engine_root(bundle), bundle / "vendor")
