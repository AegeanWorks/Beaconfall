import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from keystone.input import ActionState
from live_game import LiveGame
from records import RecordStore


class Canvas:
    def __init__(self):
        self.labels = []

    def text(self, x, y, text, color, scale):
        self.labels.append(text)


class Size:
    width = 960
    height = 540


class GradeIndicatorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = LiveGame(RecordStore(Path(temp.name) / "records.json"))

    def start(self):
        self.game.update(0, ActionState(pressed={"start"}))
        self.game.skip_countdown()

    def finish(self, elapsed, hits=0):
        self.game.distance = 399.9
        self.game.speed = 10.0
        self.game.elapsed = elapsed
        self.game.hits = hits
        self.game.checkpoint = 3
        self.game.update(0.1, ActionState())

    def test_gold_after_silver_sets_grade_improved(self):
        self.game.best_medals["classic"] = "SILVER"
        self.start()
        self.finish(17.0)
        self.assertEqual(self.game.medal(), "GOLD")
        self.assertTrue(self.game.grade_improved)
        canvas = Canvas()
        self.game.draw_ui(canvas, Size())
        self.assertTrue(any("BEST GRADE" in label for label in canvas.labels))

    def test_no_improvement_does_not_set_the_flag(self):
        self.game.best_medals["classic"] = "GOLD"
        self.start()
        self.finish(17.0)
        self.assertFalse(self.game.grade_improved)

    def test_first_finish_sets_the_flag(self):
        self.start()
        self.finish(20.0)
        self.assertEqual(self.game.medal(), "SILVER")
        self.assertTrue(self.game.grade_improved)

    def test_restart_clears_the_flag(self):
        self.start()
        self.finish(17.0)
        self.assertTrue(self.game.grade_improved)
        self.game.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(self.game.grade_improved)


if __name__ == "__main__":
    unittest.main()
