import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from keystone.audio import Mixer, sine, write_wav
from keystone.input import ActionState
from live_game import LiveGame
from records import RecordStore


class AudioCueTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.game = LiveGame(RecordStore(Path(temp.name) / "records.json"))

    def start_racing(self):
        self.game.update(0, ActionState(pressed={"start"}))
        self.game.skip_countdown()

    def test_game_exposes_a_mixer(self):
        self.assertIsInstance(self.game.mixer, Mixer)

    def test_low_time_fires_one_voice(self):
        self.start_racing()
        self.game.remaining = 9.0
        self.game.update(1 / 60, ActionState())
        self.assertEqual(self.game.mixer.voice_count(), 1)

    def test_beep_is_one_shot_until_time_recovers(self):
        self.start_racing()
        self.game.remaining = 9.0
        self.game.update(1 / 60, ActionState())
        self.game.update(1 / 60, ActionState())
        self.assertEqual(self.game.mixer.voice_count(), 1)
        # A checkpoint bonus lifts time above the threshold, then it drops again.
        self.game.remaining = 20.0
        self.game.update(1 / 60, ActionState())
        self.game.remaining = 9.0
        self.game.update(1 / 60, ActionState())
        self.assertEqual(self.game.mixer.voice_count(), 2)

    def test_beep_clip_is_deterministic_wav(self):
        self.start_racing()
        self.game.remaining = 9.0
        self.game.update(1 / 60, ActionState())
        self.assertIsNotNone(self.game.last_beep_clip)
        rendered = self.game.mixer.render()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "beep.wav"
            write_wav(path, rendered)
            data = path.read_bytes()
        self.assertTrue(data.startswith(b"RIFF"))
        self.assertEqual(data[:4], b"RIFF")

    def test_restart_clears_the_cue(self):
        self.start_racing()
        self.game.remaining = 9.0
        self.game.update(1 / 60, ActionState())
        self.game.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(self.game.mixer.voice_count(), 0)
        self.assertFalse(self.game.low_time_cued)


if __name__ == "__main__":
    unittest.main()
