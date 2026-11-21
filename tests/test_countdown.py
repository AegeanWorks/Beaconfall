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


class CountdownTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = LiveGame(RecordStore(Path(temp.name) / "records.json"))

    def test_start_begins_a_countdown(self):
        self.game.update(0, ActionState(pressed={"start"}))
        self.assertEqual(self.game.countdown, 3.0)
        self.assertEqual(self.game.state, "racing")

    def test_car_is_held_still_during_countdown(self):
        self.game.update(0, ActionState(pressed={"start"}))
        for _ in range(10):
            self.game.update(1 / 60, ActionState(forward=1))
        self.assertEqual(self.game.distance, 0.0)
        self.assertEqual(self.game.speed, 0.0)

    def test_countdown_releases_the_car(self):
        self.game.update(0, ActionState(pressed={"start"}))
        for _ in range(180):  # 3 seconds at 60 fps
            self.game.update(1 / 60, ActionState(forward=1))
        self.assertEqual(self.game.countdown, 0.0)
        for _ in range(10):
            self.game.update(1 / 60, ActionState(forward=1))
        self.assertGreater(self.game.distance, 0.0)

    def test_countdown_shows_3_2_1_then_go(self):
        class Size:
            width = 960
            height = 540

        self.game.update(0, ActionState(pressed={"start"}))
        canvas = Canvas()
        self.game.draw_ui(canvas, Size())
        self.assertTrue(any("3" in label for label in canvas.labels))

        for _ in range(180):
            self.game.update(1 / 60, ActionState(forward=1))
        canvas = Canvas()
        self.game.draw_ui(canvas, Size())
        self.assertTrue(any("GO" in label for label in canvas.labels))

    def test_restart_clears_the_countdown(self):
        self.game.update(0, ActionState(pressed={"start"}))
        self.game.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(self.game.countdown, 0.0)
        self.assertEqual(self.game.state, "ready")


if __name__ == "__main__":
    unittest.main()
