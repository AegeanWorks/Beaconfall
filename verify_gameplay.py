"""Determinism check that drives the race and hashes full internal state."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "keystone"))

from beaconfall import Race
from demo import steer_around
from keystone.input import ActionState


def full_state(race: Race) -> dict[str, object]:
    """Public snapshot plus hidden state a snapshot hash would miss."""
    state = dict(race.snapshot())
    state["current_trace"] = list(race.current_trace)
    state["current_splits"] = dict(race.current_splits)
    state["near_indices"] = sorted(race.near_indices)
    state["hit_indices"] = sorted(race.hit_indices)
    state["best_times"] = dict(race.best_times)
    state["near_misses"] = race.near_misses
    state["near_streak"] = race.near_streak
    state["best_near_streak"] = race.best_near_streak
    return state


def _drive(frames: int, sprint: bool) -> Race:
    race = Race()
    race.update(0, ActionState(pressed=frozenset({"start"})))
    held = {"sprint"} if sprint else set()
    for _ in range(frames):
        race.update(1 / 60, ActionState(forward=1, right=steer_around(race), held=held))
        if race.state != "racing":
            break
    return race


def verify_gameplay(frames: int = 120, sprint: bool = True) -> dict[str, object]:
    """Run two identical scripted drives and compare their full state."""
    runs = []
    for _ in range(2):
        race = _drive(frames, sprint)
        state = full_state(race)
        payload = json.dumps(state, sort_keys=True, default=str)
        runs.append((race, hashlib.md5(payload.encode("utf-8")).hexdigest(), payload))
    ok = runs[0][1] == runs[1][1]
    first = runs[0][0]
    return {
        "ok": ok,
        "runs": 2,
        "hash": runs[0][1],
        "distance": round(first.distance, 3),
        "state": first.state,
        "frames": frames,
    }


def main(arguments: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    frames = 120
    sprint = "--no-sprint" not in arguments
    if "--frames" in arguments:
        index = arguments.index("--frames")
        if index + 1 < len(arguments):
            frames = int(arguments[index + 1])
    result = verify_gameplay(frames=frames, sprint=sprint)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
