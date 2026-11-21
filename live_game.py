"""Interactive game adapter with durable personal records."""
from __future__ import annotations

import sys
from pathlib import Path

from beaconfall import LOW_TIME, Race
from keystone.audio import Mixer, sine, square
from keystone.ui.font import text_width
from records import COURSES, MEDAL_RANK, RecordError, RecordStore, RunResult


class LiveGame(Race):
    """Keep persistent I/O outside the deterministic simulation factory."""

    def __init__(self, store: RecordStore | None = None) -> None:
        super().__init__()
        self.record_label = "BEST"
        self.best_nears = dict.fromkeys(COURSES, 0)
        self.best_streak_bests = dict.fromkeys(COURSES, 0)
        self.last_sessions = {course: {} for course in COURSES}
        self.lifetime_totals = {course: {"finishes": 0, "golds": 0} for course in COURSES}
        self.lifetime_distance = dict.fromkeys(COURSES, 0.0)
        self.best_medals = dict.fromkeys(COURSES, "")
        self.clean_finishes = dict.fromkeys(COURSES, 0)
        self.run_history = []
        self.countdown = 0.0
        self.go_flash = 0.0
        self.paused = False
        self.mixer = Mixer()
        self.low_time_cued = False
        self.last_beep_clip = None
        self.last_chime_clip = None
        self.last_collision_clip = None
        self.grade_improved = False
        self.records_warning = False
        self.store = store
        if self.store is None:
            try:
                self.store = RecordStore(Path.home() / ".beaconfall" / "records.json")
            except (OSError, RuntimeError) as exc:
                self._warn_records(exc)
                return
        try:
            self.best_times.update(self.store.load())
            self.best_nears.update(self.store.load_near())
            self.best_streak_bests.update(self.store.load_streak())
            self.best_splits.update(self.store.load_splits())
            self.best_traces.update(self.store.load_traces())
            self.last_sessions.update(self.store.load_last())
            self.lifetime_totals.update(self.store.load_totals())
            self.lifetime_distance.update(self.store.load_distance())
            self.best_medals.update(self.store.load_medals())
            self.clean_finishes.update(self.store.load_clean())
            self.run_history = self.store.load_history()
        except RecordError as exc:
            self._warn_records(exc)

    def bind_input(self, mapping: object) -> None:
        super().bind_input(mapping)
        mapping.bind("pause", "p")

    def skip_countdown(self) -> None:
        """Clear the start countdown (for tests and scripted adapters)."""
        self.countdown = 0.0
        self.go_flash = 0.0

    def chime_frequencies(self) -> tuple[float, float, float]:
        """Rising base frequencies for the three checkpoint chimes."""
        return (523.25, 659.25, 783.99)

    def _clear_audio_cue(self) -> None:
        self.mixer.clear()
        self.low_time_cued = False
        self.last_beep_clip = None
        self.last_chime_clip = None
        self.last_collision_clip = None

    def _warn_records(self, error: Exception) -> None:
        self.records_warning = True
        print(f"Records unavailable.\nWhy: {error}\n"
              "Fix: check the record folder, free space, and file permissions; "
              "keep newer-format records for a compatible version.", file=sys.stderr)

    def update(self, dt: float, actions: object) -> None:
        if "pause" in actions.pressed:
            self.paused = not self.paused
        if self.paused:
            if "restart" in actions.pressed:
                self.paused = False
                self.countdown = 0.0
                self.go_flash = 0.0
                self.grade_improved = False
                self.reset()
                self._clear_audio_cue()
                self._sync_scene()
            return
        if self.countdown > 0:
            if "restart" in actions.pressed:
                self.countdown = 0.0
                self.go_flash = 0.0
                self.grade_improved = False
                self.reset()
                self._clear_audio_cue()
                self._sync_scene()
                return
            self.countdown = max(0.0, self.countdown - dt)
            if self.countdown < 1e-9:
                self.countdown = 0.0
                self.go_flash = 0.6
            return
        if self.go_flash > 0:
            self.go_flash = max(0.0, self.go_flash - dt)
        previous_state = self.state
        previous_best = self.best_time
        previous_checkpoint = self.checkpoint
        previous_hits = self.hits
        was_cued = self.low_time_cued
        super().update(dt, actions)
        if self.state == "racing" and self.hits > previous_hits:
            self.last_collision_clip = square(140.0, 0.18, name="collision")
            self.mixer.play(self.last_collision_clip, gain=0.4)
        if self.state == "racing" and self.checkpoint > previous_checkpoint:
            gate = self.checkpoint
            frequency = self.chime_frequencies()[gate - 1]
            self.last_chime_clip = sine(frequency, 0.15, name=f"checkpoint_{gate}")
            self.mixer.play(self.last_chime_clip, gain=0.5)
        if "restart" in actions.pressed and previous_state != "ready":
            self._clear_audio_cue()
            self.grade_improved = False
        if previous_state == "ready" and self.state == "racing":
            self.countdown = 3.0
        low_now = self.state == "racing" and self.remaining <= LOW_TIME
        if low_now and not was_cued:
            self.last_beep_clip = sine(880.0, 0.12, name="low_time")
            self.mixer.play(self.last_beep_clip, gain=0.5)
            self.low_time_cued = True
        elif not low_now and was_cued:
            self.low_time_cued = False
        improved_time = (self.best_time is not None
                         and (previous_best is None or self.best_time < previous_best))
        improved_near = self.near_misses > self.best_nears[self.course]
        improved_streak = self.best_near_streak > self.best_streak_bests[self.course]
        if self.store is not None and previous_state == "racing" and self.state == "finished":
            medal = self.medal()
            previous_grade = MEDAL_RANK.get(self.best_medals[self.course], 0)
            self.grade_improved = MEDAL_RANK[medal] > previous_grade
            summary = {"time": self.elapsed, "medal": medal, "hits": self.hits,
                       "near_misses": self.near_misses, "streak": self.best_near_streak}
            try:
                result = RunResult(self.course, self.best_time, self.near_misses,
                                   self.best_near_streak, self.current_splits, summary, medal,
                                   self.current_trace, self.distance, self.hits == 0)
                saved = self.store.finish_run(result)
                self.best_times.update(saved.times)
                self.best_nears.update(saved.near)
                self.best_streak_bests.update(saved.streak)
                self.best_splits.update(saved.splits)
                self.best_traces.update(saved.traces)
                self.last_sessions.update(saved.last)
                self.lifetime_totals.update(saved.totals)
                self.lifetime_distance.update(saved.distance)
                self.best_medals.update(saved.medals)
                self.clean_finishes.update(saved.clean)
                self.run_history = saved.history
                self.records_warning = False
            except RecordError as exc:
                self._warn_records(exc)

    def draw_ui(self, canvas: object, state: object) -> None:
        super().draw_ui(canvas, state)
        center = int(state.width) // 2
        if self.countdown > 0:
            number = str(int(self.countdown - 1e-9) + 1)
            canvas.text(center - text_width(number, 4) // 2, int(state.height) // 2 - 40,
                        number, (1.0, 0.85, 0.25, 1.0), 4)
        elif self.go_flash > 0:
            canvas.text(center - text_width("GO!", 3) // 2, int(state.height) // 2 - 40,
                        "GO!", (0.3, 1.0, 0.4, 1.0), 3)
        if self.paused:
            canvas.text(center - text_width("PAUSED", 3) // 2, int(state.height) // 2 - 80,
                        "PAUSED", (1.0, 0.95, 0.4, 1.0), 3)
        if self.state == "finished" and self.grade_improved:
            label = "BEST GRADE!"
            canvas.text(center - text_width(label, 1) // 2, int(state.height) // 2 + 150,
                        label, (1.0, 0.85, 0.3, 1.0), 1)
        if self.state == "ready":
            for index, entry in enumerate(self.run_history[:3]):
                text = f"LAST {entry['course'].upper()} {entry['elapsed']:.1f}s {entry['medal']}"
                canvas.text(center - text_width(text, 1) // 2,
                            int(state.height) // 2 + 235 + index * 12,
                            text, (0.7, 0.85, 0.95, 1.0), 1)
        if self.records_warning:
            text = "RECORDS NOT SAVED - SEE CONSOLE"
            canvas.text(int(state.width) // 2 - text_width(text, 1) // 2,
                        int(state.height) - 105, text, (1.0, 0.55, 0.3, 1.0), 1)
