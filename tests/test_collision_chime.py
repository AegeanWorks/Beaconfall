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


class CollisionChimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = LiveGame(RecordStore(Path(temp.name) / "records.json"))
        self.game.update(0, ActionState(pressed={"start"}))
        self.game.skip_countdown()

    def collide(self):
        # Boulder at 50 m, x=-2. Car at x=-1.5 is within the 1.15 m hit radius.
        self.game.distance = 49.9
        self.game.speed = 20.0
        self.game.x = -1.5
        self.game.update(0.5, ActionState())

    def test_collision_plays_one_voice(self):
        before = self.game.mixer.voice_count()
        self.collide()
        self.assertEqual(self.game.hits, 1)
        self.assertEqual(self.game.mixer.voice_count(), before + 1)
        self.assertIsNotNone(self.game.last_collision_clip)

    def test_no_replay_without_a_new_hit(self):
        self.collide()
        count = self.game.mixer.voice_count()
        self.game.update(1 / 60, ActionState())
        self.assertEqual(self.game.mixer.voice_count(), count)

    def test_restart_clears_collision_chime(self):
        self.collide()
        self.game.update(0, ActionState(pressed={"restart"}))
        self.game.skip_countdown()
        self.assertEqual(self.game.mixer.voice_count(), 0)
        self.assertIsNone(self.game.last_collision_clip)


if __name__ == "__main__":
    unittest.main()
