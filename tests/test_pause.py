import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from keystone.input import ActionState, InputMap
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


class PauseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = LiveGame(RecordStore(Path(temp.name) / "records.json"))
        self.game.update(0, ActionState(pressed={"start"}))
        self.game.skip_countdown()

    def test_p_toggles_pause(self):
        self.assertFalse(self.game.paused)
        self.game.update(0, ActionState(pressed={"pause"}))
        self.assertTrue(self.game.paused)
        self.game.update(0, ActionState(pressed={"pause"}))
        self.assertFalse(self.game.paused)

    def test_pause_freezes_the_car(self):
        self.game.update(1 / 60, ActionState(forward=1))
        moving = self.game.distance
        self.game.update(0, ActionState(pressed={"pause"}))
        for _ in range(10):
            self.game.update(1 / 60, ActionState(forward=1))
        self.assertEqual(self.game.distance, moving)

    def test_pause_binding_works_through_a_real_keyboard(self):
        class Keyboard:
            keys = set()

            def key_down(self, name):
                return name in self.keys

            def mouse_down(self, name):
                return False

            def cursor_position(self):
                return (0, 0)

        keyboard = Keyboard()
        mapping = InputMap()
        self.game.bind_input(mapping)
        keyboard.keys = {"p"}
        self.game.update(0, mapping.sample(keyboard))
        self.assertTrue(self.game.paused)

    def test_pause_shows_a_hud_label(self):
        self.game.update(0, ActionState(pressed={"pause"}))
        canvas = Canvas()
        self.game.draw_ui(canvas, Size())
        self.assertTrue(any("PAUSED" in label for label in canvas.labels))

    def test_restart_clears_pause(self):
        self.game.update(0, ActionState(pressed={"pause"}))
        self.game.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(self.game.paused)


if __name__ == "__main__":
    unittest.main()
