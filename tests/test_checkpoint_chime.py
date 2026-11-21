import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from keystone.audio import Mixer
from keystone.input import ActionState
from live_game import LiveGame
from records import RecordStore


class CheckpointChimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = LiveGame(RecordStore(Path(temp.name) / "records.json"))
        self.game.update(0, ActionState(pressed={"start"}))
        self.game.skip_countdown()

    def cross_checkpoint(self, number):
        self.game.distance = number * 100.0 - 0.1
        self.game.speed = 10.0
        self.game.update(0.1, ActionState())

    def test_checkpoint_plays_a_chime(self):
        self.assertEqual(self.game.mixer.voice_count(), 0)
        self.cross_checkpoint(1)
        self.assertEqual(self.game.checkpoint, 1)
        self.assertEqual(self.game.mixer.voice_count(), 1)
        self.assertIsNotNone(self.game.last_chime_clip)

    def test_each_gate_has_a_distinct_rising_pitch(self):
        self.cross_checkpoint(1)
        first = self.game.last_chime_clip
        self.cross_checkpoint(2)
        second = self.game.last_chime_clip
        self.cross_checkpoint(3)
        third = self.game.last_chime_clip
        pitches = self.game.chime_frequencies()
        self.assertEqual(len(set(pitches)), 3)
        self.assertEqual(list(pitches), sorted(pitches))

    def test_chime_is_one_shot_per_crossing(self):
        self.cross_checkpoint(1)
        self.assertEqual(self.game.mixer.voice_count(), 1)
        self.game.update(1 / 60, ActionState())
        self.assertEqual(self.game.mixer.voice_count(), 1)

    def test_restart_clears_chimes(self):
        self.cross_checkpoint(1)
        self.game.update(0, ActionState(pressed={"restart"}))
        self.game.skip_countdown()
        self.assertEqual(self.game.mixer.voice_count(), 0)
        self.assertIsNone(self.game.last_chime_clip)

    def test_mixer_still_works_after_chime(self):
        self.assertIsInstance(self.game.mixer, Mixer)
        self.cross_checkpoint(1)
        self.assertGreater(self.game.mixer.voice_count(), 0)


if __name__ == "__main__":
    unittest.main()
