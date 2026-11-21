# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document catalogues Python modules, classes, and exported functions. See Map Coverage for any stack it does not index.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `17`
- **Total Classes**: `23`
- **Total Top-Level Functions**: `21`
- **Total Class Methods**: `339`
- **Total Source Lines**: `5158`

## 🧭 Map Coverage
- **Indexed**: python (`17` module(s))
- **Not indexed by this map**: none (no non-Python source files were found)

---

## 📦 Modules & Exported Symbols

### [`beaconfall.py`](beaconfall.py)
> *Beaconfall: a compact downhill time trial for the Keystone engine.*

**Size**: `950` lines

**Classes:**
- `class Race` - *Fixed-step driving simulation and Keystone game adapter.*
  - Method `.__init__()`
  - Property `.course_rocks`
  - Property `.best_time`
  - Method `.reset()`
  - Method `.bind_input(mapping)`
  - Method `.actions()`
  - Method `.build_scene()`
  - Method `._sync_scene()`
  - Method `.ghost_state()` - *Interpolate the best run's (x, distance) at the current elapsed time.*
  - Method `.pace_delta()` - *Seconds slower (+) or faster (-) than the best run at this distance.*
  - Method `._finish()`
  - Method `.update(dt, actions)`
  - Method `.achievements()` - *Milestones derived from already-tracked per-course records.*
  - Method `.trophy_count()`
  - Method `.next_grade_target()` - *What is needed for the next better medal, or '' before a finish.*
  - Method `.low_time()` - *True when a live race is within the low-time warning threshold.*
  - Method `.high_speed()` - *True when a live race is in the high-speed warning band.*
  - Method `.low_boost()` - *True when a live race has a nearly depleted boost charge.*
  - Method `.medal()` - *Grade completed runs; unfinished runs do not receive a medal.*
  - Method `.next_marker()` - *Distance remaining to the next checkpoint, or to the finish line.*
  - Method `.split_summary()` - *One label per recorded checkpoint, with a signed delta when a best exists.*
  - Method `.steering_hint()` - *A lane hint for the next nearby boulder, or '' when none is close.*
  - Property `.speed_lit_material`
  - Method `.lit_speed_bars()`
  - Method `.ghost_distance()` - *Best-run distance at the current elapsed time, or None if no trace.*
  - Method `.boulder_proximity()` - *True when the next boulder is close ahead and the car's gap is in the near-miss band.*
  - Method `.minimap_rows()` - *Render the next MINIMAP_DEPTH metres as rows of lane characters.*
  - Method `.checkpoints_remaining()`
  - Method `.pickups_remaining()`
  - Method `.time_bar(width)`
  - Method `.progress_bar(width)`
  - Method `.snapshot()`
  - Method `.status()`
  - Method `.draw_ui(canvas, state)`

---

### [`demo.py`](demo.py)
> *Drive the actual race headlessly for AIKit's scripted demo.*

**Size**: `46` lines

**Functions:**
- `def steer_around(race)` - *Steer toward the closest safe lane for the next boulder.*
- `def main()`

---

### [`inventory.py`](inventory.py)
> *Project-owned UI inventory: one `kind|name|locator` line per control.*

**Size**: `13` lines

---

### [`live_game.py`](live_game.py)
> *Interactive game adapter with durable personal records.*

**Size**: `196` lines

**Classes:**
- `class LiveGame` - *Keep persistent I/O outside the deterministic simulation factory.*
  - Method `.__init__(store)`
  - Method `.bind_input(mapping)`
  - Method `.skip_countdown()` - *Clear the start countdown (for tests and scripted adapters).*
  - Method `.chime_frequencies()` - *Rising base frequencies for the three checkpoint chimes.*
  - Method `._clear_audio_cue()`
  - Method `._warn_records(error)`
  - Method `.update(dt, actions)`
  - Method `.draw_ui(canvas, state)`

---

### [`play.py`](play.py)
> *Launch Beaconfall with the adjacent Keystone checkout.*

**Size**: `49` lines

**Functions:**
- `def engine_root(root)` - *Locate either an exported engine or the adjacent development checkout.*
- `def game_spec(arguments)` - *Keep offline tools deterministic; normal windowed play loads records.*
- `def main()`

---

### [`records.py`](records.py)
> *Crash-safe, per-course records for interactive Beaconfall runs.*

**Size**: `572` lines

**Classes:**
- `class RunResult` - *Everything a completed run contributes to the persistent records.*
- `class Records` - *All persisted bests: times, near-miss counts, streak peaks and checkpoint splits.*
  - Method `.empty()`
- `class RecordError` - *Records could not be safely read or updated.*
- `class _Unsupported`
- `class RecordStore` - *Read and merge best times under one cross-process lock.*
  - Method `.__init__(path)`
  - Method `.load()`
  - Method `.load_near()`
  - Method `.load_streak()`
  - Method `.load_splits()`
  - Method `.load_last()`
  - Method `.load_history()`
  - Method `.load_clean()`
  - Method `.load_medals()`
  - Method `.load_distance()`
  - Method `.load_traces()`
  - Method `.load_totals()`
  - Method `._commit(saved)` - *Encode, back up and atomically write a Records object.*
  - Method `.finish_run(result)` - *Update every best and increment lifetime totals in one atomic write.*
  - Method `.record(course, elapsed, near_misses, best_streak, splits, last, totals)`

**Functions:**
- `def _valid_medal(value)`
- `def _valid_history(value)`
- `def _valid_trace(value)`
- `def _valid_totals(value)`
- `def _valid_last(value)`
- `def _replace(source, target)`
- `def _sync_directory(directory)`
- `def _atomic_bytes(path, data)`
- `def _locked(path)`
- `def _decode(path)`
- `def _read(path)`

---

### [`tests/test_audio_cue.py`](tests/test_audio_cue.py)
**Size**: `71` lines

**Classes:**
- `class AudioCueTests`
  - Method `.setUp()`
  - Method `.start_racing()`
  - Method `.test_game_exposes_a_mixer()`
  - Method `.test_low_time_fires_one_voice()`
  - Method `.test_beep_is_one_shot_until_time_recovers()`
  - Method `.test_beep_clip_is_deterministic_wav()`
  - Method `.test_restart_clears_the_cue()`

---

### [`tests/test_checkpoint_chime.py`](tests/test_checkpoint_chime.py)
**Size**: `67` lines

**Classes:**
- `class CheckpointChimeTests`
  - Method `.setUp()`
  - Method `.cross_checkpoint(number)`
  - Method `.test_checkpoint_plays_a_chime()`
  - Method `.test_each_gate_has_a_distinct_rising_pitch()`
  - Method `.test_chime_is_one_shot_per_crossing()`
  - Method `.test_restart_clears_chimes()`
  - Method `.test_mixer_still_works_after_chime()`

---

### [`tests/test_collision_chime.py`](tests/test_collision_chime.py)
**Size**: `52` lines

**Classes:**
- `class CollisionChimeTests`
  - Method `.setUp()`
  - Method `.collide()`
  - Method `.test_collision_plays_one_voice()`
  - Method `.test_no_replay_without_a_new_hit()`
  - Method `.test_restart_clears_collision_chime()`

---

### [`tests/test_countdown.py`](tests/test_countdown.py)
**Size**: `74` lines

**Classes:**
- `class Canvas`
  - Method `.__init__()`
  - Method `.text(x, y, text, color, scale)`
- `class CountdownTests`
  - Method `.setUp()`
  - Method `.test_start_begins_a_countdown()`
  - Method `.test_car_is_held_still_during_countdown()`
  - Method `.test_countdown_releases_the_car()`
  - Method `.test_countdown_shows_3_2_1_then_go()`
  - Method `.test_restart_clears_the_countdown()`

---

### [`tests/test_determinism.py`](tests/test_determinism.py)
**Size**: `70` lines

**Classes:**
- `class DeterminismTests`
  - Method `.test_full_state_includes_hidden_fields()`
  - Method `.test_identical_scripted_runs_match()`
  - Method `.test_divergence_in_hidden_state_is_detected()`
  - Method `.test_verify_gameplay_drives_the_car()`
  - Method `.test_verify_gameplay_flag_is_an_offline_spec()`
  - Method `.test_hidden_state_beyond_the_snapshot_is_compared()`
- `class RaceStub` - *Minimal stand-in exposing the fields full_state reads.*
  - Method `.__init__()`
  - Method `.snapshot()`

---

### [`tests/test_grade_indicator.py`](tests/test_grade_indicator.py)
**Size**: `77` lines

**Classes:**
- `class Canvas`
  - Method `.__init__()`
  - Method `.text(x, y, text, color, scale)`
- `class Size`
- `class GradeIndicatorTests`
  - Method `.setUp()`
  - Method `.start()`
  - Method `.finish(elapsed, hits)`
  - Method `.test_gold_after_silver_sets_grade_improved()`
  - Method `.test_no_improvement_does_not_set_the_flag()`
  - Method `.test_first_finish_sets_the_flag()`
  - Method `.test_restart_clears_the_flag()`

---

### [`tests/test_pause.py`](tests/test_pause.py)
**Size**: `84` lines

**Classes:**
- `class Canvas`
  - Method `.__init__()`
  - Method `.text(x, y, text, color, scale)`
- `class Size`
- `class PauseTests`
  - Method `.setUp()`
  - Method `.test_p_toggles_pause()`
  - Method `.test_pause_freezes_the_car()`
  - Method `.test_pause_binding_works_through_a_real_keyboard()`
  - Method `.test_pause_shows_a_hud_label()`
  - Method `.test_restart_clears_pause()`

---

### [`tests/test_race.py`](tests/test_race.py)
**Size**: `2170` lines

**Classes:**
- `class RaceTests`
  - Method `.test_course_can_be_mirrored_before_start_but_not_mid_race()`
  - Method `.test_each_course_keeps_its_own_session_best()`
  - Method `.test_keyboard_bindings_drive_start_boost_and_restart()`
  - Method `.test_session_best_survives_restarts_and_ignores_slower_runs()`
  - Method `.test_ready_screen_shows_session_best()`
  - Method `.test_medals_require_a_finish_and_respect_time_and_hits()`
  - Method `.test_no_stationary_lane_avoids_every_obstacle()`
  - Method `.test_waits_for_start_without_consuming_time()`
  - Method `.test_acceleration_steering_and_braking()`
  - Method `.test_boost_increases_speed_drains_and_recharges()`
  - Method `.test_checkpoint_and_finish()`
  - Method `.test_timeout_and_restart()`
  - Method `.test_timeout_before_checkpoint_cannot_grant_bonus()`
  - Method `.test_checkpoint_bonus_preserves_the_rest_of_the_frame()`
  - Method `.test_timeout_before_finish_is_not_a_win()`
  - Method `.test_finish_before_deadline_wins_even_if_frame_extends_past_it()`
  - Method `.test_collisions_only_apply_once()`
  - Method `.test_fatal_collision_does_not_award_a_later_checkpoint()`
  - Method `.test_collision_uses_steering_position_at_crossing()`
  - Method `.test_steering_toward_boulder_after_crossing_is_not_a_hit()`
  - Method `.test_fatal_impact_stops_at_the_crossing_position()`
  - Method `.test_finish_stops_lateral_motion_at_the_finish_line()`
  - Method `.test_checkpoint_before_collision_awards_time_first()`
  - Method `.test_race_feedback_expires_and_restart_clears_it()`
  - Method `.test_collision_feedback_is_drawn()`
  - Method `.test_scene_and_snapshot()`
  - Method `.test_road_markings_move_with_the_car()`
  - Method `.test_car_faces_steering_direction_and_centers_on_release()`
  - Method `.test_full_course_is_winnable()`
  - Method `.test_gold_is_attainable_with_boost_and_clean_driving()`
  - Method `.test_mirrored_course_has_a_collision_free_route()`
  - Method `.test_space_retries_immediately_after_finish()`
  - Method `.test_space_retries_after_timeout()`
  - Method `.test_space_retry_keeps_the_selected_course()`
  - Method `.test_r_still_returns_to_ready_from_the_end_screen()`
  - Method `.test_start_does_not_interrupt_a_live_race()`
  - Method `.test_end_screen_shows_space_retry_prompt()`
  - Method `.test_best_splits_are_saved_with_a_new_best()`
  - Method `.test_checkpoint_message_compares_with_the_best_split()`
  - Method `.test_splits_are_separate_per_course()`
  - Method `.test_current_splits_clear_on_restart()`
  - Method `.test_slower_finish_keeps_the_best_splits()`
  - Method `.test_trace_is_captured_and_kept_only_with_the_best_run()`
  - Method `.test_ghost_interpolates_between_trace_samples()`
  - Method `.test_ghost_is_absent_without_a_best_run()`
  - Method `.test_ghost_scene_node_follows_the_trace()`
  - Method `.test_ghost_hides_outside_a_race()`
  - Method `.test_slower_run_keeps_the_ghost_trace()`
  - Method `.test_new_best_banner_appears_and_clears_on_restart()`
  - Method `.test_slower_finish_does_not_claim_a_new_best()`
  - Method `.test_next_marker_tracks_checkpoints_and_finish()`
  - Method `.test_hud_shows_the_next_marker()`
  - Method `.test_collision_flashes_the_car_and_restores_it_when_the_message_expires()`
  - Method `.test_checkpoint_and_finish_messages_do_not_flash_the_car()`
  - Method `.test_restart_clears_a_collision_flash()`
  - Method `.test_course_cycles_through_all_three_layouts()`
  - Method `.test_no_stationary_lane_avoids_the_canyon_obstacles()`
  - Method `.test_canyon_has_a_collision_free_route()`
  - Method `.test_records_schema_covers_all_three_courses()`
  - Method `.test_canyon_best_splits_and_ghost_do_not_leak_to_classic()`
  - Method `.test_one_key_retry_keeps_canyon()`
  - Method `.test_boost_creates_a_trail_that_fades_after_release()`
  - Method `.test_trail_is_bounded_by_the_node_pool()`
  - Method `.test_no_trail_without_boost()`
  - Method `.test_trail_clears_on_restart()`
  - Method `.test_trail_nodes_follow_recorded_positions()`
  - Method `.test_camera_pulls_back_and_widens_with_speed()`
  - Method `.test_camera_response_is_bounded()`
  - Method `.test_camera_still_aims_at_the_track_when_pulled_back()`
  - Method `.test_gate_posts_turn_green_as_checkpoints_clear()`
  - Method `.test_finish_gate_turns_green_only_on_a_finish()`
  - Method `.test_gate_colours_revert_on_restart()`
  - Method `.test_close_clean_pass_counts_as_a_near_miss()`
  - Method `.test_wide_pass_is_not_a_near_miss()`
  - Method `.test_collision_is_not_also_a_near_miss()`
  - Method `.test_near_miss_counts_once_and_resets_on_restart()`
  - Method `.test_near_miss_message_does_not_flash_the_car()`
  - Method `.test_ready_screen_lists_all_course_records()`
  - Method `.test_record_panel_marker_follows_the_selected_course()`
  - Method `.test_finish_banner_tracks_the_finish_line()`
  - Method `.test_finish_banner_is_hidden_at_the_start_and_after_restart()`
  - Method `.test_first_finish_has_no_delta_and_later_runs_compare_with_the_best()`
  - Method `.test_finish_delta_clears_on_restart()`
  - Method `.test_pace_delta_interpolates_the_best_trace_by_distance()`
  - Method `.test_pace_delta_is_clamped_and_absent_without_a_trace()`
  - Method `.test_hud_shows_pace_only_when_a_best_trace_exists()`
  - Method `.test_progress_bar_marks_checkpoints_and_fills_with_distance()`
  - Method `.test_hud_shows_the_progress_bar()`
  - Method `.test_collision_shakes_the_camera_then_settles()`
  - Method `.test_checkpoint_messages_do_not_shake_the_camera()`
  - Method `.test_low_time_warning_predicate()`
  - Method `.test_low_time_warning_is_racing_only_and_clears_on_restart()`
  - Method `.test_hud_shows_time_low_with_warning_colour()`
  - Method `.test_braking_at_speed_leaves_skid_marks_that_fade()`
  - Method `.test_no_skids_without_braking_or_at_low_speed()`
  - Method `.test_skid_pool_is_bounded_and_clears_on_restart()`
  - Method `.test_near_miss_streak_grows_and_shows_a_combo()`
  - Method `.test_collision_breaks_the_streak()`
  - Method `.test_streak_resets_on_restart()`
  - Method `.test_wheels_roll_with_distance_and_reset()`
  - Method `.test_wheel_spin_is_shared_across_all_four_wheels()`
  - Method `.test_checkpoint_triggers_a_burst_that_decays()`
  - Method `.test_burst_only_triggers_on_checkpoints_not_collisions()`
  - Method `.test_burst_clears_on_restart()`
  - Method `.test_split_summary_lists_each_checkpoint_with_delta()`
  - Method `.test_split_summary_omits_delta_without_a_reference()`
  - Method `.test_split_summary_is_empty_with_no_checkpoints()`
  - Method `.test_boost_pickup_refills_boost_and_hides_after_collection()`
  - Method `.test_pickup_is_collected_only_once()`
  - Method `.test_missing_the_pickup_does_not_refill_boost()`
  - Method `.test_pickup_resets_on_restart()`
  - Method `.test_pickup_respawns_at_later_stations_and_refills_boost()`
  - Method `.test_pickup_stations_are_collected_in_order_only()`
  - Method `.test_all_pickups_reset_on_restart()`
  - Method `.test_race_ledger_accumulates_bonus_and_penalty()`
  - Method `.test_race_ledger_resets_on_restart()`
  - Method `.test_finish_screen_shows_the_ledger()`
  - Method `.test_high_speed_warning_predicate()`
  - Method `.test_high_speed_warning_clears_on_brake_and_restart()`
  - Method `.test_hud_shows_speed_callout_when_fast()`
  - Method `.test_new_record_ribbon_shows_only_on_a_best_finish()`
  - Method `.test_g_toggles_ghost_visibility()`
  - Method `.test_ghost_preference_persists_across_restart()`
  - Method `.test_ghost_toggle_works_through_real_keyboard_mapping()`
  - Method `.test_ghost_hint_is_in_the_controls_line()`
  - Method `.test_minimap_marks_upcoming_obstacles_and_car_lane()`
  - Method `.test_minimap_marks_checkpoint_and_pickup_when_ahead()`
  - Method `.test_minimap_rows_are_well_formed()`
  - Method `.test_minimap_is_drawn_in_the_racing_hud()`
  - Method `.test_ready_screen_briefs_the_time_economy()`
  - Method `.test_time_constants_drive_the_simulation()`
  - Method `.test_time_briefing_absent_while_racing()`
  - Method `.test_low_boost_predicate()`
  - Method `.test_low_boost_clears_on_recharge_and_restart()`
  - Method `.test_hud_shows_boost_low_callout()`
  - Method `.test_collision_side_is_derived_from_the_boulder_position()`
  - Method `.test_collision_side_left_and_reset()`
  - Method `.test_collision_side_shown_as_a_hud_label()`
  - Method `.test_next_grade_target_for_each_medal()`
  - Method `.test_next_grade_target_shown_on_finish_screen()`
  - Method `.test_next_grade_target_empty_before_finish()`
  - Method `.test_ghost_turns_green_when_ahead_and_orange_when_behind()`
  - Method `.test_ghost_reverts_to_base_off_race()`
  - Method `.test_ghost_base_without_a_best_trace()`
  - Method `.test_hard_steering_at_speed_leaves_drift_skids()`
  - Method `.test_soft_steering_does_not_leave_drift_skids()`
  - Method `.test_braking_and_drift_share_one_bounded_pool()`
  - Method `.test_cleared_gate_pulses_then_settles()`
  - Method `.test_gate_pulse_resets_on_restart()`
  - Method `.test_brake_lights_brighten_while_braking()`
  - Method `.test_brake_lights_off_at_low_speed()`
  - Method `.test_brake_lights_clear_on_restart()`
  - Method `.test_boost_headlights_glow_while_boosting()`
  - Method `.test_boost_headlights_clear_on_restart()`
  - Method `.test_achievements_derive_from_record_state()`
  - Method `.test_trophy_count_is_shown_on_ready_screen()`
  - Method `.test_steering_hint_points_to_a_safe_lane()`
  - Method `.test_steering_hint_empty_when_no_boulder_is_near()`
  - Method `.test_steering_hint_shown_on_the_hud()`
  - Method `.test_finish_confetti_spawns_on_a_win()`
  - Method `.test_no_confetti_on_a_failure()`
  - Method `.test_confetti_decays_and_clears_on_restart()`
  - Method `.test_minimap_marks_the_ghost_distance()`
  - Method `.test_minimap_ghost_absent_without_a_trace()`
  - Method `.test_speedometer_bars_light_with_speed()`
  - Method `.test_speedometer_marks_and_colors()`
  - Method `.test_proximity_warning_when_close_to_a_boulder()`
  - Method `.test_proximity_warning_absent_when_far()`
  - Method `.test_proximity_warning_shown_on_hud()`
  - Method `.test_time_bar_reflects_remaining_time()`
  - Method `.test_time_bar_shown_on_the_hud()`
  - Method `.test_checkpoints_remaining()`
  - Method `.test_checkpoint_countdown_on_hud()`
  - Method `.test_pickups_remaining()`
  - Method `.test_pickups_remaining_on_hud()`

**Functions:**
- `def running_race()`

---

### [`tests/test_records.py`](tests/test_records.py)
**Size**: `514` lines

**Classes:**
- `class RecordTests`
  - Method `.setUp()`
  - Method `.test_records_merge_across_instances_and_keep_fastest_per_course()`
  - Method `.test_canyon_record_round_trips_with_an_older_two_course_file()`
  - Method `.test_near_miss_bests_round_trip_and_old_files_load()`
  - Method `.test_invalid_near_miss_value_is_treated_as_corrupt()`
  - Method `.test_live_game_persists_near_miss_bests()`
  - Method `.test_both_primary_and_backup_corrupt_yields_empty_records()`
  - Method `.test_run_history_defaults_is_bounded_and_ordered()`
  - Method `.test_invalid_history_is_treated_as_corrupt()`
  - Method `.test_run_history_shown_on_ready_screen()`
  - Method `.test_live_game_restores_run_history()`
  - Method `.test_clean_finishes_default_and_accumulate()`
  - Method `.test_invalid_clean_is_treated_as_corrupt()`
  - Method `.test_live_game_persists_clean_finishes()`
  - Method `.test_best_medal_defaults_and_improves_only()`
  - Method `.test_invalid_medal_is_treated_as_corrupt()`
  - Method `.test_live_game_restores_best_medal()`
  - Method `.test_finish_run_accepts_a_run_result()`
  - Method `.test_lifetime_distance_defaults_and_accumulates()`
  - Method `.test_invalid_distance_is_treated_as_corrupt()`
  - Method `.test_live_game_accumulates_distance()`
  - Method `.test_ghost_trace_round_trips_and_old_files_load()`
  - Method `.test_ghost_trace_is_capped_and_invalid_values_quarantine()`
  - Method `.test_live_game_restores_the_ghost_trace()`
  - Method `.test_lifetime_totals_round_trip_and_old_files_load()`
  - Method `.test_invalid_totals_are_treated_as_corrupt()`
  - Method `.test_live_game_accumulates_lifetime_totals()`
  - Method `.test_both_write_paths_produce_the_same_json_shape()`
  - Method `.test_last_session_round_trips_and_old_files_load()`
  - Method `.test_invalid_last_session_is_treated_as_corrupt()`
  - Method `.test_live_game_persists_and_restores_last_session()`
  - Method `.test_best_splits_round_trip_with_string_keys()`
  - Method `.test_invalid_split_value_is_treated_as_corrupt()`
  - Method `.test_live_game_restores_persisted_splits()`
  - Method `.test_best_near_streak_round_trips_and_old_files_load()`
  - Method `.test_invalid_streak_value_is_treated_as_corrupt()`
  - Method `.test_live_game_persists_the_best_streak()`
  - Method `.test_corrupt_primary_recovers_backup_and_is_quarantined()`
  - Method `.test_empty_file_is_quarantined()`
  - Method `.test_huge_numeric_value_is_treated_as_corrupt()`
  - Method `.test_newer_schema_is_never_overwritten()`
  - Method `.test_low_disk_space_does_not_write_record()`
  - Method `.test_unreadable_record_is_not_quarantined_or_overwritten()`
  - Method `.test_stale_lock_is_reclaimed()`
  - Method `.test_live_lock_timeout_does_not_remove_another_writer_lock()`
  - Method `.test_live_game_survives_home_directory_failure()`
  - Method `.test_live_game_persists_and_loads_a_completed_run()`
  - Method `.test_default_live_record_path_is_under_home()`
  - Method `.test_save_failure_keeps_the_game_playable_and_warns()`
  - Method `.test_headless_modes_do_not_load_live_records()`
  - Method `.test_launcher_finds_a_vendored_engine_in_an_export()`

---

### [`tests/test_records_integration.py`](tests/test_records_integration.py)
> *Integration check for overlapping record writers.*

**Size**: `77` lines

**Classes:**
- `class RecordConcurrencyTests`
  - Method `.test_simultaneous_processes_preserve_both_course_records()`
  - Method `.test_concurrent_finishes_both_count_toward_lifetime_totals()`
  - Method `.test_record_is_visible_to_a_new_game_process()`

---

### [`verify_gameplay.py`](verify_gameplay.py)
> *Determinism check that drives the race and hashes full internal state.*

**Size**: `76` lines

**Functions:**
- `def full_state(race)` - *Public snapshot plus hidden state a snapshot hash would miss.*
- `def _drive(frames, sprint)`
- `def verify_gameplay(frames, sprint)` - *Run two identical scripted drives and compare their full state.*
- `def main(arguments)`

---
