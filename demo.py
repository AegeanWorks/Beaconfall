"""Drive the actual race headlessly for AIKit's scripted demo."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "keystone"))

from beaconfall import Race
from keystone.input import ActionState


def steer_around(race: Race) -> float:
    """Steer toward the closest safe lane for the next boulder."""
    upcoming = next(((distance, x) for distance, x in race.course_rocks if distance > race.distance), None)
    if upcoming is None or upcoming[0] - race.distance > 25:
        return 0.0
    lanes = (-3.6, 0.0, 3.6)
    safe = [lane for lane in lanes if abs(lane - upcoming[1]) > 1.5]
    target = min(safe, key=lambda lane: abs(lane - race.x))
    return max(-1.0, min(1.0, (target - race.x) * 4))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scripted", action="store_true", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    race = Race()
    start = race.snapshot()
    race.update(0, ActionState(pressed=frozenset({"start"})))
    for _ in range(6000):
        race.update(1 / 60, ActionState(forward=1, right=steer_around(race)))
        if race.state != "racing":
            break
    print(f"SEED: {args.seed} (course is fixed)")
    print(f"WORLD-DELTA: distance={start['distance']}->{race.distance:.1f}")
    print(f"WORLD-DELTA: checkpoints={start['checkpoint']}->{race.checkpoint}")
    print(f"WORLD-DELTA: state={start['state']}->{race.state}")
    return 0 if race.state == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
