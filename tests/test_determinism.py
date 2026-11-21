import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from keystone.input import ActionState
from play import game_spec
from verify_gameplay import full_state, verify_gameplay


class DeterminismTests(unittest.TestCase):
    def test_full_state_includes_hidden_fields(self):
        state = full_state(RaceStub())
        self.assertIn("current_trace", state)
        self.assertIn("current_splits", state)
        self.assertIn("near_indices", state)
        self.assertIn("hit_indices", state)
        self.assertIn("best_times", state)

    def test_identical_scripted_runs_match(self):
        result = verify_gameplay(frames=120, sprint=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["runs"], 2)
        self.assertEqual(len(result["hash"]), 32)

    def test_divergence_in_hidden_state_is_detected(self):
        # Two states that share a public snapshot but differ in hidden state.
        a = RaceStub()
        b = RaceStub()
        b.current_trace = [(0.0, 0.0, 0.0)]
        self.assertNotEqual(full_state(a), full_state(b))

    def test_verify_gameplay_drives_the_car(self):
        result = verify_gameplay(frames=120, sprint=True)
        self.assertGreater(result["distance"], 0)
        self.assertEqual(result["state"], "racing")

    def test_verify_gameplay_flag_is_an_offline_spec(self):
        self.assertEqual(game_spec(["--verify-gameplay", "--frames", "120"]), "beaconfall:Game")

    def test_hidden_state_beyond_the_snapshot_is_compared(self):
        # current_trace is absent from snapshot() but present in full_state().
        state = full_state(RaceStub())
        self.assertNotIn("current_trace", RaceStub().snapshot())
        self.assertIn("current_trace", state)


class RaceStub:
    """Minimal stand-in exposing the fields full_state reads."""

    def __init__(self):
        self.current_trace = []
        self.current_splits = {}
        self.near_indices = set()
        self.hit_indices = set()
        self.best_times = {}
        self.near_misses = 0
        self.near_streak = 0
        self.best_near_streak = 0
        self.distance = 0.0

    def snapshot(self):
        return {"state": "ready", "distance": 0.0}


if __name__ == "__main__":
    unittest.main()
