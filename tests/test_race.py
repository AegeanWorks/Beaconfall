import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "keystone"))

from beaconfall import (BRONZE_TIME, BURST_LENGTH, CANYON_ROCKS, CHECKPOINT_BONUS,
                        CLEARED_GATE_MATERIAL, COURSES, GATE_MATERIAL, GHOST_AHEAD_MATERIAL,
                        GHOST_BEHIND_MATERIAL, GHOST_MATERIAL, GOLD_HITS, GOLD_TIME,
                        MINIMAP_ROWS, PICKUP_DISTANCE, PICKUP_STATIONS, PICKUP_X, ROCKS,
                        SILVER_HITS, SILVER_TIME, SKID_LENGTH, START_TIME, TRAIL_LENGTH, Race)
from demo import steer_around
from keystone.input import ActionState, InputMap


def running_race():
    race = Race()
    race.update(0, ActionState(pressed=frozenset({"start"})))
    return race


class RaceTests(unittest.TestCase):
    def test_course_can_be_mirrored_before_start_but_not_mid_race(self):
        race = Race()
        race.build_scene()
        original = race.course_rocks
        self.assertEqual(race.course, "classic")
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "mirror")
        self.assertEqual(race.course_rocks, tuple((z, -x) for z, x in original))
        self.assertAlmostEqual(race.rocks[0].transform.position.x, -original[0][1])
        race.update(0, ActionState(pressed={"start"}))
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "mirror")

    def test_each_course_keeps_its_own_session_best(self):
        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        classic_best = race.best_time
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"course"}))
        self.assertIsNone(race.best_time)
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 18, 3
        race.update(0.1, ActionState())
        self.assertLess(race.best_time, classic_best)
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.best_time, classic_best)

    def test_keyboard_bindings_drive_start_boost_and_restart(self):
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
        race = Race()
        race.bind_input(mapping)
        keyboard.keys = {"f"}
        race.update(0, mapping.sample(keyboard))
        self.assertEqual(race.course, "mirror")
        keyboard.keys = {"space"}
        race.update(0.1, mapping.sample(keyboard))
        self.assertEqual(race.state, "racing")
        keyboard.keys = {"up", "right", "left_shift"}
        race.update(1, mapping.sample(keyboard))
        self.assertGreater(race.x, 0)
        self.assertGreater(race.speed, 0)
        self.assertLess(race.boost, 3)
        old_x, old_speed = race.x, race.speed
        keyboard.keys = {"down", "left"}
        race.update(0.5, mapping.sample(keyboard))
        self.assertLess(race.x, old_x)
        self.assertLess(race.speed, old_speed)
        keyboard.keys = {"r"}
        race.update(0, mapping.sample(keyboard))
        self.assertEqual(race.state, "ready")
        self.assertEqual(race.distance, 0)

    def test_session_best_survives_restarts_and_ignores_slower_runs(self):
        race = running_race()
        self.assertIsNone(race.best_time)
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        self.assertAlmostEqual(race.best_time, 20 + 0.1 / 9.98)
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 25, 3
        race.update(0.1, ActionState())
        self.assertAlmostEqual(race.best_time, 20 + 0.1 / 9.98)
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 18, 3
        race.update(0.1, ActionState())
        self.assertAlmostEqual(race.best_time, 18 + 0.1 / 9.98)
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"start"}))
        race.remaining = 0.01
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "failed")
        self.assertAlmostEqual(race.best_time, 18 + 0.1 / 9.98)

    def test_ready_screen_shows_session_best(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"restart"}))
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertIn("SESSION BEST 20.0 SEC", canvas.labels)

    def test_medals_require_a_finish_and_respect_time_and_hits(self):
        race = running_race()
        self.assertEqual(race.medal(), "")
        race.state, race.elapsed, race.hits = "finished", 17.9, 0
        self.assertEqual(race.medal(), "GOLD")
        race.hits = 1
        self.assertEqual(race.medal(), "SILVER")
        race.elapsed = 25
        self.assertEqual(race.medal(), "BRONZE")
        race.elapsed, race.hits = 20, 3
        self.assertEqual(race.medal(), "BRONZE")
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.medal(), "")

    def test_no_stationary_lane_avoids_every_obstacle(self):
        for step in range(-38, 39):
            x = step / 10
            self.assertTrue(any(abs(x - rock_x) < 1.15 for _, rock_x in ROCKS), x)

    def test_waits_for_start_without_consuming_time(self):
        race = Race()
        race.update(5, ActionState())
        self.assertEqual(race.state, "ready")
        self.assertEqual(race.remaining, 45)
        self.assertEqual(race.distance, 0)
        race.update(0, ActionState(pressed=frozenset({"start"})))
        self.assertEqual(race.state, "racing")

    def test_acceleration_steering_and_braking(self):
        race = running_race()
        race.update(1.0, ActionState(forward=1, right=1))
        self.assertGreater(race.speed, 0)
        self.assertGreater(race.x, 0)
        before = race.speed
        race.update(0.5, ActionState(forward=-1))
        self.assertLess(race.speed, before)

    def test_boost_increases_speed_drains_and_recharges(self):
        boosted = running_race()
        normal = running_race()
        boosted.update(1, ActionState(forward=1, held=frozenset({"sprint"})))
        normal.update(1, ActionState(forward=1))
        self.assertGreater(boosted.speed, normal.speed)
        self.assertLess(boosted.boost, 3)
        spent = boosted.boost
        boosted.update(1, ActionState(forward=1))
        self.assertGreater(boosted.boost, spent)
        boosted.update(10, ActionState(forward=1, held=frozenset({"sprint"})))
        self.assertEqual(boosted.boost, 0)
        boosted.update(0.1, ActionState(forward=1, held=frozenset({"sprint"})))
        self.assertEqual(boosted.boost, 0)
        boosted.update(0, ActionState(pressed=frozenset({"restart"})))
        self.assertEqual(boosted.boost, 3)

    def test_checkpoint_and_finish(self):
        race = running_race()
        race.distance = 99.9
        race.speed = 10
        race.update(0.1, ActionState())
        self.assertEqual(race.checkpoint, 1)
        race.distance = 399.9
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")

    def test_timeout_and_restart(self):
        race = running_race()
        race.remaining = 0.1
        race.update(0.2, ActionState())
        self.assertEqual(race.state, "failed")
        race.update(0.1, ActionState(pressed=frozenset({"restart"})))
        self.assertEqual(race.state, "ready")
        self.assertEqual(race.distance, 0)

    def test_timeout_before_checkpoint_cannot_grant_bonus(self):
        race = running_race()
        race.distance = 99.9
        race.speed = 10
        race.remaining = 0.001
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "failed")
        self.assertEqual(race.checkpoint, 0)

    def test_checkpoint_bonus_preserves_the_rest_of_the_frame(self):
        race = running_race()
        race.distance, race.speed, race.remaining = 99.9, 10, 0.05
        race.update(0.1, ActionState(forward=1, held={"sprint"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.checkpoint, 1)
        self.assertAlmostEqual(race.elapsed, 0.1)
        self.assertAlmostEqual(race.remaining, 11.95)
        self.assertAlmostEqual(race.boost, 2.9)

    def test_timeout_before_finish_is_not_a_win(self):
        race = running_race()
        race.distance = 399.9
        race.speed = 10
        race.remaining = 0.001
        race.checkpoint = 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "failed")

    def test_finish_before_deadline_wins_even_if_frame_extends_past_it(self):
        race = running_race()
        race.distance, race.speed, race.remaining, race.checkpoint = 399.9, 10, 0.05, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertGreater(race.remaining, 0)

    def test_collisions_only_apply_once(self):
        race = running_race()
        race.distance = 49.5
        race.x = -2
        race.speed = 12
        race.update(0.1, ActionState())
        self.assertEqual(race.hits, 1)
        race.update(0.01, ActionState())
        self.assertEqual(race.hits, 1)

    def test_fatal_collision_does_not_award_a_later_checkpoint(self):
        race = running_race()
        race.distance, race.speed, race.x, race.remaining = 98.9, 10, 0, 1
        with patch("beaconfall.ROCKS", ((99.0, 0.0),)):
            race.update(0.2, ActionState())
        self.assertEqual(race.state, "failed")
        self.assertEqual(race.remaining, 0)
        self.assertEqual(race.checkpoint, 0)
        self.assertLess(race.distance, 100)

    def test_collision_uses_steering_position_at_crossing(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -3
        race.update(0.5, ActionState(right=1))
        self.assertEqual(race.hits, 1)

    def test_steering_toward_boulder_after_crossing_is_not_a_hit(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -3.8
        race.update(0.5, ActionState(right=1))
        self.assertEqual(race.hits, 0)

    def test_fatal_impact_stops_at_the_crossing_position(self):
        race = running_race()
        race.distance, race.speed, race.x, race.remaining = 49.9, 20, -3, 1
        race.update(0.5, ActionState(right=1))
        self.assertEqual(race.state, "failed")
        self.assertAlmostEqual(race.distance, 50)
        self.assertLess(race.x, -2.9)

    def test_finish_stops_lateral_motion_at_the_finish_line(self):
        race = running_race()
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.5, ActionState(right=1))
        self.assertEqual(race.state, "finished")
        self.assertLess(race.x, 0.1)

    def test_checkpoint_before_collision_awards_time_first(self):
        race = running_race()
        race.distance, race.speed, race.x, race.remaining = 99.8, 10, 0, 1.5
        with patch("beaconfall.ROCKS", ((100.2, 0.0),)):
            race.update(0.1, ActionState())
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.checkpoint, 1)
        self.assertEqual(race.hits, 1)
        self.assertGreater(race.remaining, 10)

    def test_race_feedback_expires_and_restart_clears_it(self):
        race = running_race()
        race.distance = 49.5
        race.x = -2
        race.speed = 12
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "COLLISION -2 SEC")
        race.update(2.1, ActionState())
        self.assertEqual(race.message, "")
        race.distance = 99.9
        race.speed = 10
        race.x = 0
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "CHECKPOINT +12 SEC")
        race.update(0, ActionState(pressed=frozenset({"restart"})))
        self.assertEqual(race.message, "")

    def test_collision_feedback_is_drawn(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance, race.x, race.speed = 49.5, -2, 12
        race.update(0.1, ActionState())
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertIn("COLLISION -2 SEC", canvas.labels)

    def test_scene_and_snapshot(self):
        race = running_race()
        self.assertIsNotNone(race.build_scene())
        race.update(0.1, ActionState(forward=1))
        self.assertGreater(race.snapshot()["distance"], 0)

    def test_road_markings_move_with_the_car(self):
        race = running_race()
        race.build_scene()
        before = race.markings[0].transform.position.z
        race.speed = 10
        race.update(0.1, ActionState())
        self.assertNotEqual(before, race.markings[0].transform.position.z)

    def test_car_faces_steering_direction_and_centers_on_release(self):
        race = running_race()
        race.build_scene()
        race.update(0.1, ActionState(forward=1, right=1))
        self.assertLess(race.car.transform.rotation.y, 0)
        race.update(0.1, ActionState(forward=1))
        self.assertAlmostEqual(race.car.transform.rotation.y, 0)
        race.update(0.1, ActionState(forward=1, right=-1))
        self.assertGreater(race.car.transform.rotation.y, 0)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertAlmostEqual(race.car.transform.rotation.y, 0)

    def test_full_course_is_winnable(self):
        race = running_race()
        for _ in range(6000):
            race.update(1 / 60, ActionState(forward=1, right=steer_around(race)))
            if race.state != "racing":
                break
        self.assertEqual(race.state, "finished")
        self.assertEqual(race.hits, 0)
        self.assertEqual(race.checkpoint, 3)

    def test_gold_is_attainable_with_boost_and_clean_driving(self):
        race = running_race()
        for _ in range(6000):
            race.update(1 / 60, ActionState(forward=1, right=steer_around(race), held={"sprint"}))
            if race.state != "racing":
                break
        self.assertEqual(race.medal(), "GOLD")

    def test_mirrored_course_has_a_collision_free_route(self):
        race = Race()
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"start"}))
        for _ in range(6000):
            race.update(1 / 60, ActionState(forward=1, right=steer_around(race)))
            if race.state != "racing":
                break
        self.assertEqual(race.state, "finished")
        self.assertEqual(race.hits, 0)
        self.assertEqual(race.checkpoint, 3)


    def test_space_retries_immediately_after_finish(self):
        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        best = race.best_time
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.distance, 0)
        self.assertEqual(race.elapsed, 0)
        self.assertEqual(race.hits, 0)
        self.assertEqual(race.course, "classic")
        self.assertEqual(race.best_time, best)

    def test_space_retries_after_timeout(self):
        race = running_race()
        race.remaining = 0.01
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "failed")
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.remaining, 45)
        self.assertEqual(race.checkpoint, 0)
        self.assertEqual(race.distance, 0)

    def test_space_retry_keeps_the_selected_course(self):
        race = Race()
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"start"}))
        race.remaining = 0.01
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.course, "mirror")

    def test_r_still_returns_to_ready_from_the_end_screen(self):
        race = running_race()
        race.remaining = 0.01
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.state, "ready")
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.distance, 0)

    def test_start_does_not_interrupt_a_live_race(self):
        race = running_race()
        race.update(1.0, ActionState(forward=1))
        distance = race.distance
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.distance, distance)

    def test_end_screen_shows_space_retry_prompt(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.remaining = 0.01
        race.update(0.1, ActionState())
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("SPACE RETRY" in label for label in canvas.labels))


    def test_best_splits_are_saved_with_a_new_best(self):
        race = running_race()
        race.distance, race.speed, race.elapsed = 99.9, 10, 20
        race.update(0.1, ActionState())
        self.assertEqual(race.checkpoint, 1)
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertIn(1, race.best_splits["classic"])
        self.assertAlmostEqual(race.best_splits["classic"][1], 20.01, places=2)
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertAlmostEqual(race.best_splits["classic"][1], 20.01, places=2)

    def test_checkpoint_message_compares_with_the_best_split(self):
        race = running_race()
        race.distance, race.speed, race.elapsed = 99.9, 10, 20
        race.update(0.1, ActionState())
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed = 99.9, 10, 21
        race.update(0.1, ActionState())
        self.assertIn("+1.0s", race.message)
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed = 99.9, 10, 19
        race.update(0.1, ActionState())
        self.assertIn("-1.0s", race.message)

    def test_splits_are_separate_per_course(self):
        race = Race()
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed = 99.9, 10, 20
        race.update(0.1, ActionState())
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.best_splits["mirror"], {})
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed = 99.9, 10, 21
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "CHECKPOINT +12 SEC")

    def test_current_splits_clear_on_restart(self):
        race = running_race()
        race.distance, race.speed, race.elapsed = 99.9, 10, 20
        race.update(0.1, ActionState())
        self.assertIn(1, race.current_splits)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.current_splits, {})

    def test_slower_finish_keeps_the_best_splits(self):
        race = running_race()
        race.distance, race.speed, race.elapsed = 99.9, 10, 20
        race.update(0.1, ActionState())
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        best_time = race.best_time
        best_splits = dict(race.best_splits["classic"])
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 30, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.best_time, best_time)
        self.assertEqual(race.best_splits["classic"], best_splits)


    def test_trace_is_captured_and_kept_only_with_the_best_run(self):
        race = running_race()
        for _ in range(120):
            race.update(1 / 60, ActionState(forward=1, right=steer_around(race)))
        self.assertGreater(len(race.current_trace), 5)
        self.assertEqual(race.best_traces["classic"], [])
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertGreater(len(race.best_traces["classic"]), 5)
        best_trace = list(race.best_traces["classic"])
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.current_trace, [])
        self.assertEqual(race.best_traces["classic"], best_trace)

    def test_ghost_interpolates_between_trace_samples(self):
        race = running_race()
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (1.0, 2.0, 10.0), (2.0, 4.0, 20.0)]
        race.elapsed = 0.5
        self.assertEqual(race.ghost_state(), (1.0, 5.0))
        race.elapsed = 1.5
        self.assertEqual(race.ghost_state(), (3.0, 15.0))
        race.elapsed = 9.0
        self.assertEqual(race.ghost_state(), (4.0, 20.0))

    def test_ghost_is_absent_without_a_best_run(self):
        race = running_race()
        self.assertIsNone(race.ghost_state())
        race.build_scene()
        self.assertFalse(race.ghost.visible)

    def test_ghost_scene_node_follows_the_trace(self):
        race = running_race()
        race.build_scene()
        race.best_traces["classic"] = [(0.0, -2.0, 0.0), (1.0, 2.0, 10.0)]
        race.distance = 5.0
        race.elapsed = 0.5
        race.update(0, ActionState())
        self.assertTrue(race.ghost.visible)
        self.assertAlmostEqual(race.ghost.transform.position.x, 0.0)
        self.assertAlmostEqual(race.ghost.transform.position.z, 3.0)

    def test_ghost_hides_outside_a_race(self):
        race = running_race()
        race.build_scene()
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (1.0, 1.0, 10.0)]
        race.elapsed = 0.5
        race.update(0, ActionState())
        self.assertTrue(race.ghost.visible)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.ghost.visible)

    def test_slower_run_keeps_the_ghost_trace(self):
        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        best_trace = list(race.best_traces["classic"])
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 30, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.best_traces["classic"], best_trace)


    def test_new_best_banner_appears_and_clears_on_restart(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertTrue(race.new_best)
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("NEW BEST!" in label for label in canvas.labels))
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.new_best)

    def test_slower_finish_does_not_claim_a_new_best(self):
        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 30, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertFalse(race.new_best)

    def test_next_marker_tracks_checkpoints_and_finish(self):
        race = running_race()
        self.assertAlmostEqual(race.next_marker(), 100.0)
        race.distance, race.checkpoint = 150.0, 1
        self.assertAlmostEqual(race.next_marker(), 50.0)
        race.distance, race.checkpoint = 250.0, 2
        self.assertAlmostEqual(race.next_marker(), 50.0)
        race.distance, race.checkpoint = 350.0, 3
        self.assertAlmostEqual(race.next_marker(), 50.0)
        race.distance = 400.0
        self.assertAlmostEqual(race.next_marker(), 0.0)

    def test_hud_shows_the_next_marker(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("NEXT 100 M" in label for label in canvas.labels))
        race.distance, race.checkpoint = 350.0, 3
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("NEXT FINISH 50 M" in label for label in canvas.labels))


    def test_collision_flashes_the_car_and_restores_it_when_the_message_expires(self):
        race = running_race()
        race.build_scene()
        base = [node.material for node in race.car.children]
        race.distance, race.x, race.speed = 49.5, -2, 12
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "COLLISION -2 SEC")
        self.assertNotEqual([node.material for node in race.car.children], base)
        race.message_time = 0
        race.update(0, ActionState())
        self.assertEqual([node.material for node in race.car.children], base)

    def test_checkpoint_and_finish_messages_do_not_flash_the_car(self):
        race = running_race()
        race.build_scene()
        base = [node.material for node in race.car.children]
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "CHECKPOINT +12 SEC")
        self.assertEqual([node.material for node in race.car.children], base)
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertEqual([node.material for node in race.car.children], base)

    def test_restart_clears_a_collision_flash(self):
        race = running_race()
        race.build_scene()
        base = [node.material for node in race.car.children]
        race.distance, race.x, race.speed = 49.5, -2, 12
        race.update(0.1, ActionState())
        self.assertNotEqual([node.material for node in race.car.children], base)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual([node.material for node in race.car.children], base)


    def test_course_cycles_through_all_three_layouts(self):
        race = Race()
        self.assertEqual(race.course, "classic")
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "mirror")
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "canyon")
        self.assertEqual(race.course_rocks, CANYON_ROCKS)
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "classic")

    def test_no_stationary_lane_avoids_the_canyon_obstacles(self):
        for step in range(-38, 39):
            x = step / 10
            self.assertTrue(any(abs(x - rock_x) < 1.15 for _, rock_x in CANYON_ROCKS), x)

    def test_canyon_has_a_collision_free_route(self):
        race = Race()
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "canyon")
        race.update(0, ActionState(pressed={"start"}))
        for _ in range(6000):
            race.update(1 / 60, ActionState(forward=1, right=steer_around(race)))
            if race.state != "racing":
                break
        self.assertEqual(race.state, "finished")
        self.assertEqual(race.hits, 0)
        self.assertEqual(race.checkpoint, 3)

    def test_records_schema_covers_all_three_courses(self):
        from records import COURSES as RECORD_COURSES
        race = Race()
        self.assertEqual(COURSES, ("classic", "mirror", "canyon"))
        self.assertEqual(set(race.best_times), set(RECORD_COURSES))
        self.assertEqual(set(race.best_splits), set(RECORD_COURSES))
        self.assertEqual(set(race.best_traces), set(RECORD_COURSES))

    def test_canyon_best_splits_and_ghost_do_not_leak_to_classic(self):
        race = Race()
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed = 99.9, 10, 20
        race.update(0.1, ActionState())
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        self.assertIn(1, race.best_splits["canyon"])
        self.assertTrue(race.best_traces["canyon"])
        race.update(0, ActionState(pressed={"restart"}))
        race.update(0, ActionState(pressed={"course"}))
        self.assertEqual(race.course, "classic")
        self.assertEqual(race.best_splits["classic"], {})
        self.assertEqual(race.best_traces["classic"], [])

    def test_one_key_retry_keeps_canyon(self):
        race = Race()
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"course"}))
        race.update(0, ActionState(pressed={"start"}))
        race.remaining = 0.01
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "failed")
        race.update(0, ActionState(pressed={"start"}))
        self.assertEqual(race.state, "racing")
        self.assertEqual(race.course, "canyon")


    def test_boost_creates_a_trail_that_fades_after_release(self):
        race = running_race()
        race.build_scene()
        for _ in range(30):
            race.update(1 / 60, ActionState(forward=1, held={"sprint"}))
        self.assertTrue(race.boosting)
        self.assertGreater(len(race.trail), 0)
        self.assertTrue(any(node.visible for node in race.trail_nodes))
        for _ in range(60):
            race.update(1 / 60, ActionState(forward=1))
        self.assertFalse(race.boosting)
        self.assertEqual(race.trail, [])
        self.assertFalse(any(node.visible for node in race.trail_nodes))

    def test_trail_is_bounded_by_the_node_pool(self):
        race = running_race()
        for _ in range(600):
            race.update(1 / 60, ActionState(forward=1, held={"sprint"}))
        self.assertLessEqual(len(race.trail), TRAIL_LENGTH)

    def test_no_trail_without_boost(self):
        race = running_race()
        race.build_scene()
        for _ in range(30):
            race.update(1 / 60, ActionState(forward=1))
        self.assertEqual(race.trail, [])
        self.assertFalse(any(node.visible for node in race.trail_nodes))

    def test_trail_clears_on_restart(self):
        race = running_race()
        race.build_scene()
        race.update(1 / 60, ActionState(forward=1, held={"sprint"}))
        self.assertTrue(race.trail)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.trail, [])
        self.assertFalse(any(node.visible for node in race.trail_nodes))

    def test_trail_nodes_follow_recorded_positions(self):
        race = running_race()
        race.build_scene()
        race.distance = 20.0
        race.trail = [(1.5, 18.0, 1.0), (-2.0, 16.0, 0.5)]
        race.update(0, ActionState())
        visible = [node for node in race.trail_nodes if node.visible]
        self.assertEqual(len(visible), 2)
        self.assertAlmostEqual(visible[0].transform.position.x, 1.5)
        self.assertAlmostEqual(visible[0].transform.position.z, 6.0)
        self.assertAlmostEqual(visible[1].transform.position.z, 8.0)


    def test_camera_pulls_back_and_widens_with_speed(self):
        race = running_race()
        race.build_scene()
        race.update(0, ActionState())
        self.assertAlmostEqual(race.scene.camera.position.y, 9.0)
        self.assertAlmostEqual(race.scene.camera.position.z, 14.0)
        self.assertAlmostEqual(race.scene.camera.fov_y, 60.0)
        race.speed = 30.0
        race.update(0, ActionState())
        self.assertAlmostEqual(race.scene.camera.position.y, 11.0)
        self.assertAlmostEqual(race.scene.camera.position.z, 19.0)
        self.assertAlmostEqual(race.scene.camera.fov_y, 70.0)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertAlmostEqual(race.scene.camera.position.y, 9.0)
        self.assertAlmostEqual(race.scene.camera.position.z, 14.0)
        self.assertAlmostEqual(race.scene.camera.fov_y, 60.0)

    def test_camera_response_is_bounded(self):
        race = running_race()
        race.build_scene()
        race.speed = 1000.0
        race.update(0, ActionState())
        self.assertAlmostEqual(race.scene.camera.position.z, 19.0)
        self.assertAlmostEqual(race.scene.camera.fov_y, 70.0)

    def test_camera_still_aims_at_the_track_when_pulled_back(self):
        race = running_race()
        race.build_scene()
        race.speed = 30.0
        race.update(0, ActionState())
        camera = race.scene.camera
        direction = (race.camera_target - camera.position).normalized()
        forward = camera.forward()
        alignment = (forward.x * direction.x + forward.y * direction.y + forward.z * direction.z)
        self.assertAlmostEqual(alignment, 1.0, places=5)


    def test_gate_posts_turn_green_as_checkpoints_clear(self):
        race = running_race()
        race.build_scene()
        self.assertTrue(all(node.material == GATE_MATERIAL for pair in race.gates for node in pair))
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertTrue(all(node.material == CLEARED_GATE_MATERIAL for node in race.gates[0]))
        self.assertTrue(all(node.material == GATE_MATERIAL
                            for pair in race.gates[1:] for node in pair))
        race.distance, race.speed, race.checkpoint = 199.9, 10, 1
        race.update(0.1, ActionState())
        self.assertTrue(all(node.material == CLEARED_GATE_MATERIAL
                            for pair in race.gates[:2] for node in pair))

    def test_finish_gate_turns_green_only_on_a_finish(self):
        race = running_race()
        race.build_scene()
        race.distance, race.speed, race.checkpoint = 399.9, 10, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertTrue(all(node.material == CLEARED_GATE_MATERIAL for pair in race.gates for node in pair))

    def test_gate_colours_revert_on_restart(self):
        race = running_race()
        race.build_scene()
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertTrue(all(node.material == CLEARED_GATE_MATERIAL for node in race.gates[0]))
        race.update(0, ActionState(pressed={"restart"}))
        self.assertTrue(all(node.material == GATE_MATERIAL for pair in race.gates for node in pair))


    def test_close_clean_pass_counts_as_a_near_miss(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -0.6
        race.update(0.5, ActionState())
        self.assertEqual(race.hits, 0)
        self.assertEqual(race.near_misses, 1)
        self.assertEqual(race.message, "NEAR MISS")
        self.assertEqual(race.snapshot()["near_misses"], 1)

    def test_wide_pass_is_not_a_near_miss(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, 0.5
        race.update(0.5, ActionState())
        self.assertEqual(race.hits, 0)
        self.assertEqual(race.near_misses, 0)

    def test_collision_is_not_also_a_near_miss(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -2
        race.update(0.5, ActionState())
        self.assertEqual(race.hits, 1)
        self.assertEqual(race.near_misses, 0)
        self.assertEqual(race.message, "COLLISION -2 SEC")

    def test_near_miss_counts_once_and_resets_on_restart(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -0.6
        race.update(0.5, ActionState())
        race.update(0.1, ActionState())
        self.assertEqual(race.near_misses, 1)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.near_misses, 0)

    def test_near_miss_message_does_not_flash_the_car(self):
        race = running_race()
        race.build_scene()
        base = [node.material for node in race.car.children]
        race.distance, race.speed, race.x = 49.9, 20, -0.6
        race.update(0.5, ActionState())
        self.assertEqual(race.message, "NEAR MISS")
        self.assertEqual([node.material for node in race.car.children], base)


    def test_ready_screen_lists_all_course_records(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = Race()
        race.best_times.update({"classic": 20.0, "mirror": None, "canyon": 17.25})
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("CLASSIC" in label and "20.0" in label for label in canvas.labels))
        self.assertTrue(any("MIRROR" in label and "--" in label for label in canvas.labels))
        self.assertTrue(any("CANYON" in label and "17.2" in label for label in canvas.labels))
        self.assertTrue(any(label.startswith("> CLASSIC") for label in canvas.labels))

    def test_record_panel_marker_follows_the_selected_course(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = Race()
        race.update(0, ActionState(pressed={"course"}))
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any(label.startswith("> MIRROR") for label in canvas.labels))
        self.assertFalse(any(label.startswith("> CLASSIC") for label in canvas.labels))


    def test_finish_banner_tracks_the_finish_line(self):
        race = running_race()
        race.build_scene()
        self.assertGreater(len(race.finish_nodes), 5)
        race.distance = 380.0
        race.update(0, ActionState())
        self.assertTrue(all(node.visible for node, _, _, _ in race.finish_nodes))
        self.assertAlmostEqual(race.finish_nodes[0][0].transform.position.z, -17.0)
        race.distance = 399.9
        race.update(0, ActionState())
        self.assertAlmostEqual(race.finish_nodes[0][0].transform.position.z, 2.9)
        self.assertGreaterEqual(len({node.material for node, _, _, _ in race.finish_nodes}), 2)

    def test_finish_banner_is_hidden_at_the_start_and_after_restart(self):
        race = running_race()
        race.build_scene()
        race.update(0, ActionState())
        self.assertFalse(any(node.visible for node, _, _, _ in race.finish_nodes))
        race.distance = 380.0
        race.update(0, ActionState())
        self.assertTrue(all(node.visible for node, _, _, _ in race.finish_nodes))
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(any(node.visible for node, _, _, _ in race.finish_nodes))


    def test_first_finish_has_no_delta_and_later_runs_compare_with_the_best(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        self.assertIsNone(race.finish_delta)
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 23, 3
        race.update(0.1, ActionState())
        self.assertGreater(race.finish_delta, 0)
        self.assertEqual(race.snapshot()["finish_delta"], round(race.finish_delta, 3))
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("SLOWER THAN BEST" in label for label in canvas.labels))
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 18, 3
        race.update(0.1, ActionState())
        self.assertLess(race.finish_delta, 0)
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("FASTER THAN BEST" in label for label in canvas.labels))

    def test_finish_delta_clears_on_restart(self):
        race = running_race()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"start"}))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 22, 3
        race.update(0.1, ActionState())
        self.assertIsNotNone(race.finish_delta)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertIsNone(race.finish_delta)
        self.assertIsNone(race.snapshot()["finish_delta"])


    def test_pace_delta_interpolates_the_best_trace_by_distance(self):
        race = running_race()
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (1.0, 0.0, 10.0), (2.0, 0.0, 20.0)]
        race.distance, race.elapsed = 15.0, 1.5
        self.assertAlmostEqual(race.pace_delta(), 0.0)
        race.elapsed = 2.0
        self.assertAlmostEqual(race.pace_delta(), 0.5)
        race.distance, race.elapsed = 5.0, 1.0
        self.assertAlmostEqual(race.pace_delta(), 0.5)

    def test_pace_delta_is_clamped_and_absent_without_a_trace(self):
        race = running_race()
        self.assertIsNone(race.pace_delta())
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (2.0, 0.0, 20.0)]
        race.distance, race.elapsed = 100.0, 3.0
        self.assertAlmostEqual(race.pace_delta(), 1.0)

    def test_hud_shows_pace_only_when_a_best_trace_exists(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertFalse(any("PACE" in label for label in canvas.labels))
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (2.0, 0.0, 20.0)]
        race.distance, race.elapsed = 10.0, 2.0
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("PACE +1.0s VS BEST" in label for label in canvas.labels))


    def test_progress_bar_marks_checkpoints_and_fills_with_distance(self):
        race = running_race()
        race.distance = 0.0
        self.assertEqual(race.progress_bar(), "[-----|----|----|----]")
        race.distance = 200.0
        self.assertEqual(race.progress_bar(), "[##########|----|----]")
        race.distance = 400.0
        self.assertEqual(race.progress_bar(), "[####################]")

    def test_hud_shows_the_progress_bar(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance = 100.0
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("[#####" in label for label in canvas.labels))


    def test_collision_shakes_the_camera_then_settles(self):
        race = running_race()
        race.build_scene()
        race.distance, race.x, race.speed = 49.5, -2, 12
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "COLLISION -2 SEC")
        self.assertNotAlmostEqual(race.scene.camera.position.x, 0.0)
        self.assertLessEqual(abs(race.scene.camera.position.x), 0.25)
        race.message_time = 0
        race.update(0, ActionState())
        self.assertAlmostEqual(race.scene.camera.position.x, 0.0)

    def test_checkpoint_messages_do_not_shake_the_camera(self):
        race = running_race()
        race.build_scene()
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertEqual(race.message, "CHECKPOINT +12 SEC")
        self.assertAlmostEqual(race.scene.camera.position.x, 0.0)
        self.assertAlmostEqual(race.scene.camera.position.y,
                               9.0 + min(1.0, race.speed / 30.0) * 2.0)


    def test_low_time_warning_predicate(self):
        race = running_race()
        self.assertFalse(race.low_time())
        race.remaining = 10.01
        self.assertFalse(race.low_time())
        race.remaining = 10.0
        self.assertTrue(race.low_time())
        race.remaining = 0.0
        self.assertTrue(race.low_time())

    def test_low_time_warning_is_racing_only_and_clears_on_restart(self):
        race = running_race()
        race.remaining = 5.0
        race.state = "finished"
        self.assertFalse(race.low_time())
        race.state = "racing"
        self.assertTrue(race.low_time())
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.low_time())

    def test_hud_shows_time_low_with_warning_colour(self):
        class Canvas:
            def __init__(self):
                self.labels = []
                self.colours = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)
                self.colours.append(color)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        race.remaining = 5.0
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("TIME LOW" in label for label in canvas.labels))
        timer_index = next(i for i, label in enumerate(canvas.labels) if label.startswith("TIME "))
        self.assertEqual(canvas.colours[timer_index][0], 1.0)
        race.remaining = 40.0
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertFalse(any("TIME LOW" in label for label in canvas.labels))


    def test_braking_at_speed_leaves_skid_marks_that_fade(self):
        race = running_race()
        race.build_scene()
        race.speed = 20.0
        for _ in range(20):
            race.update(1 / 60, ActionState(forward=-1))
        self.assertGreater(len(race.skids), 0)
        self.assertTrue(any(node.visible for node in race.skid_nodes))
        for _ in range(60):
            race.update(1 / 60, ActionState(forward=1))
        self.assertEqual(race.skids, [])
        self.assertFalse(any(node.visible for node in race.skid_nodes))

    def test_no_skids_without_braking_or_at_low_speed(self):
        race = running_race()
        race.build_scene()
        race.speed = 20.0
        for _ in range(20):
            race.update(1 / 60, ActionState(forward=1))
        self.assertEqual(race.skids, [])
        race.speed = 1.0
        for _ in range(20):
            race.update(1 / 60, ActionState(forward=-1))
        self.assertEqual(race.skids, [])

    def test_skid_pool_is_bounded_and_clears_on_restart(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(len(race.skid_nodes), SKID_LENGTH)
        race.speed = 30.0
        for _ in range(600):
            race.update(1 / 60, ActionState(forward=-1))
            race.speed = 30.0
        self.assertLessEqual(len(race.skids), SKID_LENGTH)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.skids, [])
        self.assertFalse(any(node.visible for node in race.skid_nodes))


    def test_near_miss_streak_grows_and_shows_a_combo(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -0.6
        race.update(0.5, ActionState())
        self.assertEqual(race.near_streak, 1)
        self.assertEqual(race.message, "NEAR MISS")
        race.distance, race.speed, race.x = 69.9, 20, 0.6
        race.update(0.5, ActionState())
        self.assertEqual(race.near_streak, 2)
        self.assertEqual(race.message, "2x NEAR MISS STREAK")
        self.assertEqual(race.snapshot()["best_near_streak"], 2)

    def test_collision_breaks_the_streak(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -0.6
        race.update(0.5, ActionState())
        self.assertEqual(race.near_streak, 1)
        race.distance, race.speed, race.x = 69.9, 20, 2.0
        race.update(0.5, ActionState())
        self.assertEqual(race.hits, 1)
        self.assertEqual(race.near_streak, 0)
        self.assertEqual(race.snapshot()["best_near_streak"], 1)

    def test_streak_resets_on_restart(self):
        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -0.6
        race.update(0.5, ActionState())
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.near_streak, 0)
        self.assertEqual(race.snapshot()["best_near_streak"], 0)


    def test_wheels_roll_with_distance_and_reset(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(len(race.wheel_nodes), 4)
        base = race.wheel_nodes[0].transform.rotation
        race.distance = 10.0
        race.update(0, ActionState())
        at_ten = race.wheel_nodes[0].transform.rotation
        self.assertNotEqual(at_ten, base)
        race.distance = 20.0
        race.update(0, ActionState())
        self.assertNotEqual(race.wheel_nodes[0].transform.rotation, at_ten)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.wheel_nodes[0].transform.rotation, base)

    def test_wheel_spin_is_shared_across_all_four_wheels(self):
        race = running_race()
        race.build_scene()
        race.distance = 5.0
        race.update(0, ActionState())
        turns = [node.transform.rotation for node in race.wheel_nodes]
        self.assertTrue(all(t == turns[0] for t in turns))


    def test_checkpoint_triggers_a_burst_that_decays(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(len(race.burst_nodes), BURST_LENGTH)
        self.assertIsNone(race.burst)
        self.assertFalse(any(node.visible for node in race.burst_nodes))
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertEqual(race.checkpoint, 1)
        self.assertIsNotNone(race.burst)
        self.assertTrue(any(node.visible for node in race.burst_nodes))
        for _ in range(20):
            race.update(0.1, ActionState())
        self.assertIsNone(race.burst)
        self.assertFalse(any(node.visible for node in race.burst_nodes))

    def test_burst_only_triggers_on_checkpoints_not_collisions(self):
        race = running_race()
        race.build_scene()
        race.distance, race.x, race.speed = 49.5, -2, 12
        race.update(0.1, ActionState())
        self.assertGreater(race.hits, 0)
        self.assertIsNone(race.burst)

    def test_burst_clears_on_restart(self):
        race = running_race()
        race.build_scene()
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertIsNotNone(race.burst)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertIsNone(race.burst)
        self.assertFalse(any(node.visible for node in race.burst_nodes))


    def test_split_summary_lists_each_checkpoint_with_delta(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.best_splits["classic"] = {1: 5.0, 2: 9.0, 3: 13.0}
        race.current_splits = {1: 5.5, 2: 8.8, 3: 13.4}
        race.best_times["classic"] = 13.4
        lines = race.split_summary()
        self.assertEqual(len(lines), 3)
        self.assertTrue(any("5.5" in line and "+0.5" in line for line in lines))
        self.assertTrue(any("8.8" in line and "-0.2" in line for line in lines))
        self.assertTrue(any("13.4" in line and "+0.4" in line for line in lines))
        race.state = "finished"
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("CP1" in label for label in canvas.labels))
        self.assertTrue(any("CP3" in label for label in canvas.labels))

    def test_split_summary_omits_delta_without_a_reference(self):
        race = running_race()
        race.current_splits = {1: 5.5, 2: 8.8, 3: 13.4}
        lines = race.split_summary()
        self.assertTrue(all("CP" in line for line in lines))
        self.assertTrue(all("VS BEST" not in line for line in lines))

    def test_split_summary_is_empty_with_no_checkpoints(self):
        race = running_race()
        self.assertEqual(race.split_summary(), [])


    def test_boost_pickup_refills_boost_and_hides_after_collection(self):
        race = running_race()
        race.build_scene()
        race.boost = 0.0
        race.distance, race.speed, race.x = PICKUP_DISTANCE - 0.1, 10, PICKUP_X
        race.update(0.1, ActionState())
        self.assertTrue(race.pickup_collected)
        self.assertEqual(race.boost, 3.0)
        self.assertFalse(race.pickup.visible)
        self.assertEqual(race.snapshot()["pickup_collected"], True)

    def test_pickup_is_collected_only_once(self):
        race = running_race()
        race.build_scene()
        race.boost = 0.0
        race.distance, race.speed, race.x = PICKUP_DISTANCE - 0.1, 10, PICKUP_X
        race.update(0.1, ActionState())
        race.boost = 0.0
        race.distance = PICKUP_DISTANCE + 1.0
        race.update(0.1, ActionState())
        self.assertLess(race.boost, 0.1)

    def test_missing_the_pickup_does_not_refill_boost(self):
        race = running_race()
        race.build_scene()
        race.boost = 0.0
        race.distance, race.speed, race.x = PICKUP_DISTANCE - 0.1, 10, 0.0
        race.update(0.1, ActionState())
        self.assertFalse(race.pickup_collected)
        self.assertLess(race.boost, 0.1)

    def test_pickup_resets_on_restart(self):
        race = running_race()
        race.build_scene()
        race.boost = 0.0
        race.distance, race.speed, race.x = PICKUP_DISTANCE - 0.1, 10, PICKUP_X
        race.update(0.1, ActionState())
        self.assertTrue(race.pickup_collected)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.pickup_collected)
        race.update(0, ActionState(pressed={"start"}))
        race.distance = PICKUP_DISTANCE - 5.0
        race.update(0, ActionState())
        self.assertTrue(race.pickup.visible)


    def test_pickup_respawns_at_later_stations_and_refills_boost(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(PICKUP_STATIONS[0], PICKUP_DISTANCE)
        self.assertEqual(race.pickup_station, 0)
        for index, distance in enumerate(PICKUP_STATIONS):
            race.boost = 0.0
            race.distance, race.speed, race.x = distance - 0.1, 10, PICKUP_X
            race.update(0.1, ActionState())
            self.assertEqual(race.boost, 3.0)
            self.assertEqual(race.pickups_collected, index + 1)
            self.assertEqual(race.pickup_station, index + 1)
        self.assertEqual(race.snapshot()["pickups_collected"], len(PICKUP_STATIONS))
        self.assertFalse(race.pickup.visible)

    def test_pickup_stations_are_collected_in_order_only(self):
        race = running_race()
        race.build_scene()
        later = PICKUP_STATIONS[-1]
        race.boost = 0.0
        race.distance, race.speed, race.x = later - 0.1, 10, PICKUP_X
        race.update(0.1, ActionState())
        self.assertEqual(race.pickups_collected, 0)
        self.assertEqual(race.pickup_station, 0)

    def test_all_pickups_reset_on_restart(self):
        race = running_race()
        race.build_scene()
        race.distance, race.speed, race.x = PICKUP_STATIONS[0] - 0.1, 10, PICKUP_X
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.pickups_collected, 0)
        self.assertEqual(race.pickup_station, 0)
        self.assertFalse(race.pickup_collected)


    def test_race_ledger_accumulates_bonus_and_penalty(self):
        race = running_race()
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertEqual(race.checkpoint_bonus, 12.0)
        self.assertEqual(race.collision_penalty, 0.0)
        race.distance, race.speed = 199.9, 10
        race.update(0.1, ActionState())
        self.assertEqual(race.checkpoint_bonus, 24.0)
        self.assertEqual(race.snapshot()["checkpoint_bonus"], 24.0)

        race.distance, race.speed, race.x = 249.5, 12, 0
        race.update(0.1, ActionState())
        self.assertEqual(race.collision_penalty, 2.0)
        self.assertEqual(race.snapshot()["collision_penalty"], 2.0)

    def test_race_ledger_resets_on_restart(self):
        race = running_race()
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertGreater(race.checkpoint_bonus, 0)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.checkpoint_bonus, 0.0)
        self.assertEqual(race.collision_penalty, 0.0)

    def test_finish_screen_shows_the_ledger(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.checkpoint_bonus = 36.0
        race.collision_penalty = 4.0
        race.state = "finished"
        race.best_times["classic"] = 20.0
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("BONUS +36" in label for label in canvas.labels))
        self.assertTrue(any("PENALTY -4" in label for label in canvas.labels))


    def test_high_speed_warning_predicate(self):
        race = running_race()
        race.speed = 20.0
        self.assertFalse(race.high_speed())
        race.speed = 25.0
        self.assertFalse(race.high_speed())
        race.speed = 25.01
        self.assertTrue(race.high_speed())
        race.state = "finished"
        self.assertFalse(race.high_speed())

    def test_high_speed_warning_clears_on_brake_and_restart(self):
        race = running_race()
        race.speed = 28.0
        self.assertTrue(race.high_speed())
        race.speed = 5.0
        self.assertFalse(race.high_speed())
        race.speed = 28.0
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.high_speed())

    def test_hud_shows_speed_callout_when_fast(self):
        class Canvas:
            def __init__(self):
                self.labels = []
                self.colours = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)
                self.colours.append(color)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        race.speed = 28.0
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("TOO FAST" in label for label in canvas.labels))
        race.speed = 10.0
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertFalse(any("TOO FAST" in label for label in canvas.labels))


    def test_new_record_ribbon_shows_only_on_a_best_finish(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        race.state = "finished"
        race.best_times["classic"] = 20.0
        race.new_best = True
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("NEW RECORD" in label for label in canvas.labels))
        race.new_best = False
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertFalse(any("NEW RECORD" in label for label in canvas.labels))
        race.state = "racing"
        race.new_best = True
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertFalse(any("NEW RECORD" in label for label in canvas.labels))


    def test_g_toggles_ghost_visibility(self):
        race = running_race()
        race.build_scene()
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (2.0, 0.0, 20.0)]
        race.distance = 5.0
        race.update(0, ActionState())
        self.assertTrue(race.ghost.visible)
        self.assertTrue(race.snapshot()["show_ghost"])
        race.update(0, ActionState(pressed={"ghost"}))
        self.assertFalse(race.show_ghost)
        self.assertFalse(race.ghost.visible)
        self.assertFalse(race.snapshot()["show_ghost"])
        race.update(0, ActionState(pressed={"ghost"}))
        self.assertTrue(race.ghost.visible)

    def test_ghost_preference_persists_across_restart(self):
        race = running_race()
        race.build_scene()
        race.update(0, ActionState(pressed={"ghost"}))
        self.assertFalse(race.show_ghost)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.show_ghost)

    def test_ghost_toggle_works_through_real_keyboard_mapping(self):
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
        race = Race()
        race.bind_input(mapping)
        keyboard.keys = {"g"}
        race.update(0, mapping.sample(keyboard))
        self.assertFalse(race.show_ghost)
        keyboard.keys = set()
        race.update(0, mapping.sample(keyboard))
        keyboard.keys = {"g"}
        race.update(0, mapping.sample(keyboard))
        self.assertTrue(race.show_ghost)

    def test_ghost_hint_is_in_the_controls_line(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("G GHOST" in label for label in canvas.labels))


    def test_minimap_marks_upcoming_obstacles_and_car_lane(self):
        race = running_race()
        race.distance = 20.0
        race.x = 0.0
        rows = race.minimap_rows()
        self.assertEqual(len(rows), 8)
        self.assertIn("C", rows[0])
        # A boulder at 50 m, x=-2 should appear within the next 80 m.
        self.assertTrue(any("X" in row for row in rows))
        # First checkpoint at 100 m, pickup at 200 m are outside this window.
        self.assertFalse(any("=" in row for row in rows))

    def test_minimap_marks_checkpoint_and_pickup_when_ahead(self):
        race = running_race()
        race.distance = 180.0
        race.x = 0.0
        rows = race.minimap_rows()
        self.assertTrue(any("=" in row for row in rows))  # checkpoint at 200
        self.assertTrue(any("P" in row for row in rows))  # pickup station at 200

    def test_minimap_rows_are_well_formed(self):
        race = running_race()
        race.distance = 0.0
        race.x = 0.0
        rows = race.minimap_rows()
        self.assertEqual(len(rows), MINIMAP_ROWS)
        self.assertTrue(all(row.startswith("|") and row.endswith("|") and len(row) == 7
                            for row in rows))
        self.assertIn("C", rows[0])

    def test_minimap_is_drawn_in_the_racing_hud(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance = 40.0
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("COURSE AHEAD" in label for label in canvas.labels))


    def test_ready_screen_briefs_the_time_economy(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = Race()
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any(f"{START_TIME:.0f}" in label and "START" in label
                            for label in canvas.labels))
        self.assertTrue(any(f"+{CHECKPOINT_BONUS:.0f}" in label and "CHECKPOINT" in label
                            for label in canvas.labels))

    def test_time_constants_drive_the_simulation(self):
        race = running_race()
        self.assertEqual(race.remaining, START_TIME)
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertEqual(race.checkpoint_bonus, CHECKPOINT_BONUS)

    def test_time_briefing_absent_while_racing(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertFalse(any("START" in label and f"{START_TIME:.0f}" in label
                             for label in canvas.labels))


    def test_low_boost_predicate(self):
        race = running_race()
        race.boost = 2.0
        self.assertFalse(race.low_boost())
        race.boost = 1.0
        self.assertFalse(race.low_boost())
        race.boost = 0.5
        self.assertTrue(race.low_boost())
        race.state = "finished"
        self.assertFalse(race.low_boost())

    def test_low_boost_clears_on_recharge_and_restart(self):
        race = running_race()
        race.boost = 0.4
        self.assertTrue(race.low_boost())
        race.boost = 3.0
        self.assertFalse(race.low_boost())
        race.boost = 0.4
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.low_boost())

    def test_hud_shows_boost_low_callout(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        race.boost = 0.5
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertTrue(any("BOOST LOW" in label for label in canvas.labels))
        race.boost = 2.0
        canvas = Canvas()
        race.draw_ui(canvas, size)
        self.assertFalse(any("BOOST LOW" in label for label in canvas.labels))


    def test_collision_side_is_derived_from_the_boulder_position(self):
        race = running_race()
        # Boulder at 50 m, x=-2. Car at x=-1.5 hits its right side.
        race.distance, race.speed, race.x = 49.9, 20, -1.5
        race.update(0.5, ActionState())
        self.assertEqual(race.hits, 1)
        self.assertEqual(race.message, "COLLISION -2 SEC")
        self.assertEqual(race.collision_side, "RIGHT")
        self.assertEqual(race.snapshot()["collision_side"], "RIGHT")

    def test_collision_side_left_and_reset(self):
        race = running_race()
        # Boulder at 70 m, x=2. Car at x=1.5 hits its left side.
        race.distance, race.speed, race.x = 69.9, 20, 1.5
        race.update(0.5, ActionState())
        self.assertEqual(race.collision_side, "LEFT")
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.collision_side, "")

    def test_collision_side_shown_as_a_hud_label(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance, race.speed, race.x = 49.9, 20, -1.5
        race.update(0.5, ActionState())
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("HIT RIGHT SIDE" in label for label in canvas.labels))


    def test_next_grade_target_for_each_medal(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        size = type("Size", (), {"width": 960, "height": 540})()
        race.best_times["classic"] = 20.0

        race.state, race.elapsed, race.hits = "finished", 30.0, 5
        self.assertEqual(race.medal(), "BRONZE")
        self.assertIn(f"{SILVER_TIME:.0f}", race.next_grade_target())
        self.assertIn(f"{SILVER_HITS}", race.next_grade_target())

        race.elapsed, race.hits = 20.0, 1
        self.assertEqual(race.medal(), "SILVER")
        self.assertIn(f"{GOLD_TIME:.0f}", race.next_grade_target())
        self.assertIn(f"{GOLD_HITS}", race.next_grade_target())

        race.elapsed, race.hits = 17.0, 0
        self.assertEqual(race.medal(), "GOLD")
        self.assertEqual(race.next_grade_target(), "BEST POSSIBLE")

    def test_next_grade_target_shown_on_finish_screen(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.best_times["classic"] = 20.0
        race.state, race.elapsed, race.hits = "finished", 30.0, 5
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("NEXT GRADE" in label for label in canvas.labels))

    def test_next_grade_target_empty_before_finish(self):
        race = running_race()
        self.assertEqual(race.next_grade_target(), "")


    def test_ghost_turns_green_when_ahead_and_orange_when_behind(self):
        race = running_race()
        race.build_scene()
        # Best trace: 0 m at 0 s, 20 m at 2 s. At 10 m the best elapsed is 1 s.
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (2.0, 0.0, 20.0)]
        race.distance = 10.0
        race.elapsed = 0.5
        race.update(0, ActionState())
        self.assertLess(race.pace_delta(), 0)
        self.assertEqual(race.ghost.material, GHOST_AHEAD_MATERIAL)
        race.elapsed = 1.5
        race.update(0, ActionState())
        self.assertGreater(race.pace_delta(), 0)
        self.assertEqual(race.ghost.material, GHOST_BEHIND_MATERIAL)

    def test_ghost_reverts_to_base_off_race(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(race.ghost.material, GHOST_MATERIAL)
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (2.0, 0.0, 20.0)]
        race.distance, race.elapsed = 10.0, 0.5
        race.update(0, ActionState())
        self.assertEqual(race.ghost.material, GHOST_AHEAD_MATERIAL)
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.ghost.material, GHOST_MATERIAL)

    def test_ghost_base_without_a_best_trace(self):
        race = running_race()
        race.build_scene()
        race.update(0, ActionState())
        self.assertIsNone(race.pace_delta())
        self.assertEqual(race.ghost.material, GHOST_MATERIAL)


    def test_hard_steering_at_speed_leaves_drift_skids(self):
        race = running_race()
        race.build_scene()
        race.speed = 25.0
        for _ in range(10):
            race.update(1 / 60, ActionState(forward=1, right=1))
        self.assertGreater(len(race.skids), 0)
        self.assertTrue(any(node.visible for node in race.skid_nodes))

    def test_soft_steering_does_not_leave_drift_skids(self):
        race = running_race()
        race.build_scene()
        race.speed = 25.0
        for _ in range(10):
            race.update(1 / 60, ActionState(forward=1, right=0.2))
        self.assertEqual(race.skids, [])
        self.assertFalse(any(node.visible for node in race.skid_nodes))

    def test_braking_and_drift_share_one_bounded_pool(self):
        race = running_race()
        race.build_scene()
        race.speed = 30.0
        for _ in range(600):
            race.update(1 / 60, ActionState(forward=1, right=1))
            race.speed = 30.0
        self.assertLessEqual(len(race.skids), SKID_LENGTH)
        self.assertLessEqual(sum(node.visible for node in race.skid_nodes), SKID_LENGTH)


    def test_cleared_gate_pulses_then_settles(self):
        race = running_race()
        race.build_scene()
        base_scale = race.gates[0][0].transform.scale
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        self.assertIsNotNone(race.burst)
        pulsed = race.gates[0][0].transform.scale
        self.assertGreater(pulsed.y, base_scale.y)
        self.assertEqual(race.gates[1][0].transform.scale, base_scale)
        for _ in range(20):
            race.update(0.1, ActionState())
        self.assertIsNone(race.burst)
        self.assertEqual(race.gates[0][0].transform.scale, base_scale)

    def test_gate_pulse_resets_on_restart(self):
        race = running_race()
        race.build_scene()
        base_scale = race.gates[0][0].transform.scale
        race.distance, race.speed = 99.9, 10
        race.update(0.1, ActionState())
        race.update(0, ActionState(pressed={"restart"}))
        self.assertEqual(race.gates[0][0].transform.scale, base_scale)


    def test_brake_lights_brighten_while_braking(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(len(race.tail_lamps), 2)
        base = race.tail_lamps[0].material
        race.speed = 20.0
        race.update(1 / 60, ActionState(forward=-1))
        self.assertTrue(race.braking)
        self.assertNotEqual(race.tail_lamps[0].material, base)
        race.update(1 / 60, ActionState(forward=1))
        self.assertFalse(race.braking)
        self.assertEqual(race.tail_lamps[0].material, base)

    def test_brake_lights_off_at_low_speed(self):
        race = running_race()
        race.build_scene()
        base = race.tail_lamps[0].material
        race.speed = 2.0
        race.update(1 / 60, ActionState(forward=-1))
        self.assertFalse(race.braking)
        self.assertEqual(race.tail_lamps[0].material, base)

    def test_brake_lights_clear_on_restart(self):
        race = running_race()
        race.build_scene()
        base = race.tail_lamps[0].material
        race.speed = 20.0
        race.update(1 / 60, ActionState(forward=-1))
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.braking)
        self.assertEqual(race.tail_lamps[0].material, base)


    def test_boost_headlights_glow_while_boosting(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(len(race.headlamps), 2)
        base = race.headlamps[0].material
        race.update(1 / 60, ActionState(forward=1, held={"sprint"}))
        self.assertTrue(race.boosting)
        self.assertNotEqual(race.headlamps[0].material, base)
        race.update(1 / 60, ActionState(forward=1))
        self.assertFalse(race.boosting)
        self.assertEqual(race.headlamps[0].material, base)

    def test_boost_headlights_clear_on_restart(self):
        race = running_race()
        race.build_scene()
        base = race.headlamps[0].material
        race.update(1 / 60, ActionState(forward=1, held={"sprint"}))
        race.update(0, ActionState(pressed={"restart"}))
        self.assertFalse(race.boosting)
        self.assertEqual(race.headlamps[0].material, base)


    def test_achievements_derive_from_record_state(self):
        race = Race()
        names = dict(race.achievements())
        self.assertEqual(len(names), 4)
        self.assertFalse(names["FIRST FINISH"])
        self.assertFalse(names["GOLD MEDAL"])
        self.assertFalse(names["ALL COURSES"])
        self.assertFalse(names["NEAR MISS PRO"])

        race.lifetime_totals["classic"] = {"finishes": 1, "golds": 1}
        race.best_streak_bests["classic"] = 3
        race.best_times.update({"classic": 20.0, "mirror": 21.0, "canyon": 22.0})
        names = dict(race.achievements())
        self.assertTrue(names["FIRST FINISH"])
        self.assertTrue(names["GOLD MEDAL"])
        self.assertTrue(names["ALL COURSES"])
        self.assertTrue(names["NEAR MISS PRO"])
        self.assertEqual(race.trophy_count(), 4)

    def test_trophy_count_is_shown_on_ready_screen(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = Race()
        race.lifetime_totals["classic"] = {"finishes": 1, "golds": 0}
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("TROPHIES 1/4" in label for label in canvas.labels))


    def test_steering_hint_points_to_a_safe_lane(self):
        race = running_race()
        # Rock at 50 m, x=-2; sitting on its lane steers LEFT to the -3.6 lane.
        race.distance = 40.0
        race.x = -2.0
        self.assertEqual(race.steering_hint(), "LEFT")
        # Rock at 70 m, x=2; sitting on its lane steers RIGHT to the 3.6 lane.
        race.distance = 60.0
        race.x = 2.0
        self.assertEqual(race.steering_hint(), "RIGHT")
        race.distance = 40.0
        race.x = 0.0
        self.assertEqual(race.steering_hint(), "CENTER")

    def test_steering_hint_empty_when_no_boulder_is_near(self):
        race = running_race()
        race.distance = 0.0
        race.x = 0.0
        self.assertEqual(race.steering_hint(), "")

    def test_steering_hint_shown_on_the_hud(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance = 40.0
        race.x = -2.0
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("STEER LEFT" in label for label in canvas.labels))


    def test_finish_confetti_spawns_on_a_win(self):
        race = running_race()
        race.build_scene()
        self.assertGreater(len(race.confetti_nodes), 10)
        self.assertFalse(any(node.visible for node in race.confetti_nodes))
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "finished")
        self.assertIsNotNone(race.confetti)
        self.assertTrue(any(node.visible for node in race.confetti_nodes))

    def test_no_confetti_on_a_failure(self):
        race = running_race()
        race.build_scene()
        race.remaining = 0.01
        race.update(0.1, ActionState())
        self.assertEqual(race.state, "failed")
        self.assertIsNone(race.confetti)
        self.assertFalse(any(node.visible for node in race.confetti_nodes))

    def test_confetti_decays_and_clears_on_restart(self):
        race = running_race()
        race.build_scene()
        race.distance, race.speed, race.elapsed, race.checkpoint = 399.9, 10, 20, 3
        race.update(0.1, ActionState())
        self.assertIsNotNone(race.confetti)
        for _ in range(30):
            race.update(0.1, ActionState())
        self.assertIsNone(race.confetti)
        self.assertFalse(any(node.visible for node in race.confetti_nodes))
        race.update(0, ActionState(pressed={"restart"}))
        self.assertIsNone(race.confetti)


    def test_minimap_marks_the_ghost_distance(self):
        race = running_race()
        race.distance = 20.0
        race.x = 0.0
        # Best trace: 0 m at 0 s, 20 m at 2 s, 40 m at 4 s. At elapsed 1 s the
        # ghost is at 10 m, which is behind the car (10 m back, within 80 m).
        race.best_traces["classic"] = [(0.0, 0.0, 0.0), (2.0, 0.0, 20.0), (4.0, 0.0, 40.0)]
        race.elapsed = 1.0
        rows = race.minimap_rows()
        # The ghost is behind the car, so it should not appear in the ahead strip.
        self.assertFalse(any("G" in row for row in rows))
        # At elapsed 3 s the ghost is at 30 m, 10 m ahead of the car.
        race.elapsed = 3.0
        rows = race.minimap_rows()
        self.assertTrue(any("G" in row for row in rows))

    def test_minimap_ghost_absent_without_a_trace(self):
        race = running_race()
        race.distance = 20.0
        rows = race.minimap_rows()
        self.assertFalse(any("G" in row for row in rows))


    def test_speedometer_bars_light_with_speed(self):
        race = running_race()
        race.build_scene()
        self.assertEqual(len(race.speed_bars), 8)
        race.speed = 0.0
        race.update(0, ActionState())
        self.assertEqual(race.lit_speed_bars(), 0)
        self.assertFalse(any(node.visible for node in race.speed_bars))
        race.speed = 15.0
        race.update(0, ActionState())
        self.assertGreater(race.lit_speed_bars(), 0)
        self.assertLessEqual(race.lit_speed_bars(), 8)
        self.assertEqual(sum(node.visible for node in race.speed_bars), race.lit_speed_bars())
        race.speed = 30.0
        race.update(0, ActionState())
        self.assertEqual(race.lit_speed_bars(), 8)

    def test_speedometer_marks_and_colors(self):
        race = running_race()
        race.build_scene()
        unlit = race.speed_bars[0].material
        race.speed = 30.0
        race.update(0, ActionState())
        self.assertNotEqual(race.speed_bars[0].material, unlit)
        self.assertEqual(race.speed_bars[7].material, race.speed_lit_material)


    def test_proximity_warning_when_close_to_a_boulder(self):
        race = running_race()
        # Boulder at 50 m, x=-2. Car 15 m before at x=-1.0 has gap 1.0 < NEAR_MISS_GAP.
        race.distance = 35.0
        race.x = -1.0
        self.assertTrue(race.boulder_proximity())
        race.x = 2.0
        self.assertFalse(race.boulder_proximity())

    def test_proximity_warning_absent_when_far(self):
        race = running_race()
        race.distance = 0.0
        race.x = -2.0
        self.assertFalse(race.boulder_proximity())

    def test_proximity_warning_shown_on_hud(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.distance = 35.0
        race.x = -1.0
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("TOO CLOSE" in label for label in canvas.labels))


    def test_time_bar_reflects_remaining_time(self):
        race = running_race()
        race.remaining = START_TIME
        self.assertEqual(race.time_bar(10), "[##########]")
        race.remaining = START_TIME / 2
        self.assertEqual(race.time_bar(10), "[#####     ]")
        race.remaining = 0.0
        self.assertEqual(race.time_bar(10), "[          ]")

    def test_time_bar_shown_on_the_hud(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.remaining = START_TIME / 2
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("TIME" in label and "[" in label and "#" in label
                            for label in canvas.labels))


    def test_checkpoints_remaining(self):
        race = running_race()
        self.assertEqual(race.checkpoints_remaining(), 3)
        race.checkpoint = 1
        self.assertEqual(race.checkpoints_remaining(), 2)
        race.checkpoint = 3
        self.assertEqual(race.checkpoints_remaining(), 0)

    def test_checkpoint_countdown_on_hud(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.checkpoint = 1
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any("2 LEFT" in label for label in canvas.labels))


    def test_pickups_remaining(self):
        race = running_race()
        self.assertEqual(race.pickups_remaining(), len(PICKUP_STATIONS))
        race.pickups_collected = 1
        self.assertEqual(race.pickups_remaining(), len(PICKUP_STATIONS) - 1)
        race.pickups_collected = len(PICKUP_STATIONS)
        self.assertEqual(race.pickups_remaining(), 0)

    def test_pickups_remaining_on_hud(self):
        class Canvas:
            def __init__(self):
                self.labels = []

            def text(self, x, y, text, color, scale):
                self.labels.append(text)

        race = running_race()
        race.pickups_collected = 1
        canvas = Canvas()
        race.draw_ui(canvas, type("Size", (), {"width": 960, "height": 540})())
        self.assertTrue(any(f"{len(PICKUP_STATIONS) - 1} PICKUPS LEFT" in label
                            for label in canvas.labels))


if __name__ == "__main__":
    unittest.main()
