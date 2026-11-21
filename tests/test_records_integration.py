"""Integration check for overlapping record writers."""
import sys
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from records import RecordStore


class RecordConcurrencyTests(unittest.TestCase):
    def test_simultaneous_processes_preserve_both_course_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            start = threading.Barrier(2, timeout=5)

            def write(course, elapsed):
                start.wait()
                code = ("import sys; from records import RecordStore; "
                        "RecordStore(sys.argv[1]).record(sys.argv[2], float(sys.argv[3]))")
                return subprocess.run([sys.executable, "-c", code, str(path), course, str(elapsed)],
                                      cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                                      check=True, timeout=10)

            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(write, "classic", 20)
                second = pool.submit(write, "mirror", 18)
                first.result(timeout=5)
                second.result(timeout=5)
            self.assertEqual(RecordStore(path).load(), {"classic": 20.0, "mirror": 18.0, "canyon": None})

    def test_concurrent_finishes_both_count_toward_lifetime_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            start = threading.Barrier(2, timeout=5)

            def finish(elapsed):
                start.wait()
                code = ("import sys; from records import RecordStore, RunResult; "
                        "RecordStore(sys.argv[1]).finish_run(RunResult("
                        "'classic', float(sys.argv[2]), 0, 0, {}, "
                        "{'time': float(sys.argv[2]), 'medal': 'GOLD', 'hits': 0, "
                        "'near_misses': 0, 'streak': 0}, 'GOLD'))")
                return subprocess.run([sys.executable, "-c", code, str(path), str(elapsed)],
                                      cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                                      check=True, timeout=10)

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = [pool.submit(finish, t) for t in (18.0, 19.0)]
                for result in results:
                    result.result(timeout=5)
            totals = RecordStore(path).load_totals()["classic"]
            self.assertEqual(totals["finishes"], 2)
            self.assertEqual(totals["golds"], 2)

    def test_record_is_visible_to_a_new_game_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "records.json")
            setup = ("import sys; from pathlib import Path; "
                     "sys.path.insert(0,str(Path.cwd().parent/'keystone')); "
                     "from live_game import LiveGame; from records import RecordStore; "
                     "from keystone.input import ActionState; g=LiveGame(RecordStore(sys.argv[1])); ")
            write = (setup + "g.update(0,ActionState(pressed={'start'})); g.skip_countdown(); "
                     "g.distance,g.speed,g.elapsed,g.checkpoint=399.9,10,20,3; "
                     "g.update(0.1,ActionState()); print(g.best_time)")
            read = setup + "print(g.best_time)"
            first = subprocess.run([sys.executable, "-c", write, path], cwd=ROOT,
                                   capture_output=True, text=True, encoding="utf-8", check=True, timeout=10)
            second = subprocess.run([sys.executable, "-c", read, path], cwd=ROOT,
                                    capture_output=True, text=True, encoding="utf-8", check=True, timeout=10)
            self.assertEqual(first.stdout.strip(), second.stdout.strip())
            self.assertNotEqual(second.stdout.strip(), "None")
