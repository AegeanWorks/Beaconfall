# Beaconfall

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/AegeanWorks/AIKit)

Beaconfall is a 3D downhill time trial built with Keystone. Drive 400 metres through a pine-lined mountain course, steer around boulders and reach the finish before the clock runs out. No single stationary line avoids every obstacle. Three checkpoints add time and their gates pulse and turn green with a brief particle burst and a rising chime as you clear them; the HUD counts how many remain; collisions slow the car, cost two seconds, flash it red, jolt the camera, play a low tone and report which side of the boulder was struck. The HUD shows a progress bar with checkpoint ticks and how far the next checkpoint or finish is, and a win sprays a brief confetti burst at the finish line, the finish screen marks a new session best with a NEW RECORD ribbon, shows how much faster or slower the run was than the previous best, lists each checkpoint split with its delta from the best run, totals the checkpoint bonus and collision penalty, and marks a best medal grade when improved.

## Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10 or newer, an OpenGL 3.3-capable driver, and the Keystone checkout alongside this project at `../keystone`.
- **Canonical Regression Shield Gate**:
  ```bash
  python -m unittest discover -s tests
  ```

```bash
python -m pip install -r ../keystone/requirements.txt
python play.py
```

On Windows, double-click `start-beaconfall.cmd` to start the game. On macOS or Linux, run `sh start-beaconfall.sh` from the project folder. Both launchers pass optional command-line arguments to `play.py`.

Press **F** on the ready screen to cycle through the classic, mirrored and canyon courses, then **Space** to start. The canyon is a separate winding line through alternating boulders; each course keeps its own times, splits and ghost, and the ready screen lists all three bests with the selection marked. Hold **W** to accelerate, **S** to brake (lighting the tail lamps and leaving fading skid marks at speed), and **A/D** to steer (hard steering at speed also leaves drift marks); the arrow keys also drive, and the car points into the turn with wheels that roll as you travel and a bar gauge that lights up with speed, while the camera eases back and widens as speed rises. Hold **Left Shift** while accelerating to boost; the three-second charge slowly refills when Shift is released, and three glowing pickups along the course (on the right-hand side) each refill it instantly once per run and must be taken in order; the HUD counts how many remain. Boost lights the headlamps, leaves a fading orange trail behind the car, and a BOOST LOW callout appears when the charge drops below one second. A 3-2-1-GO countdown holds the car at the start of normal play; scripted and headless races skip it. Press **G** to hide or show the best-run ghost, and **P** to pause or resume (normal play only). Press **R** to return to the ready screen. On the finish or time-up screen, press **Space** to retry the same course immediately, or **R** to return to course selection. The race begins with 45 seconds; each of the three checkpoints adds 12 seconds (both values are now named constants that also drive the ready-screen briefing). The timer has a shrinking bar and turns red, shows TIME LOW and plays a short beep when 10 seconds or less remain, and shows TOO FAST above 25 m/s. Collision and checkpoint messages show time changes as they happen. Once you have a best time for a course, each checkpoint message also shows how many seconds you are ahead of or behind that run at the same checkpoint, and the HUD shows a live pace difference, a compact course minimap of the obstacles ahead (with a G marker for the best-run ghost) a LEFT/RIGHT/CENTER steering hint for the next boulder and a TOO CLOSE warning when threading one while racing. Best checkpoint splits persist with the record file, so those comparisons survive a restart of the game. Avoid the red boulders and reach the checkered finish banner at 400 m to win; threading one closely without hitting it earns a NEAR MISS message, consecutive clean close passes build a streak, and a collision breaks it; the finish screen counts them. Keystone's pause and display controls remain available in the overlay.

Finish in under 18 seconds without a collision for gold. Under 25 seconds with at most two collisions earns silver; every other finish earns bronze, and the finish screen shows the requirement for the next grade. Normal play through `play.py` or the one-click launcher stores the best time, near-miss count, streak, splits, last run and lifetime totals for each course in `~/.beaconfall/records.json` with one atomic write per finish, plus a backup; the ready screen shows all three plus a summary of the last run and lifetime finishes/golds on the selected course; a trophy counter tracks four milestones (first finish, gold, all courses, near-miss streak), and a lifetime distance total is shown in kilometres; the last three finishes across all courses are listed on the ready screen; the best medal per course and a count of collision-free finishes are saved too and marked on the ready-screen panel. The same launchers work in a Keystone export, using its vendored engine. Headless commands and the Keystone project's generated `run.py` use session-only records so scripted simulations stay independent of player saves. After you set a best time for a course in the current session, a cyan ghost car replays that run beside you, turning green while you are ahead of it and orange while behind; the best run's path is saved with the records so the ghost survives a relaunch, and it is hidden again after a restart. If records cannot be read or written, the game continues with an on-screen warning.

## Verify

```bash
python -m unittest discover -s tests
python play.py --simulate --frames 120
python play.py --verify-determinism --frames 120
python play.py --verify-gameplay --frames 120
python play.py --project . --validate-project
python play.py --headless --frames 1 --size 960x540 --ui --out frame.png
```

`beaconfall.py` owns the race and scene, `verify_gameplay.py` drives two identical races and checks full internal state (including hidden fields), `keystone.json` describes the Keystone project, `play.py` starts the engine, and `tests/` checks the driving and race rules. Run commands from this project directory. The headless render needs a working OpenGL context; simulation and unit tests do not need a window.

## What's Inside

```text
beaconfall/
├── beaconfall.py    <- driving rules and Keystone scene
├── live_game.py     <- interactive saved-record adapter
├── records.py       <- versioned record storage
├── verify_gameplay.py <- full-state determinism verifier
├── play.py          <- engine launcher
├── start-beaconfall.cmd <- Windows one-click launcher
├── start-beaconfall.sh  <- macOS and Linux launcher
├── keystone.json    <- Keystone project manifest
├── tests/           <- race tests
├── LICENSE          <- game license
├── LICENSES/        <- license texts
├── COMMERCIAL.md    <- commercial terms
├── ASSETS.md        <- asset manifest
├── REUSE.toml       <- licensing metadata
├── demo.py          <- compatibility demo
├── inventory.py     <- compatibility inventory
├── .gitattributes   <- line endings
├── .gitignore       <- generated files
├── README.md        <- project guide
└── .aikit/          <- project memory
```

## License

Free for personal play under the Aegean Game License 1.1; see [LICENSE](LICENSE). Commercial use requires the license described in [COMMERCIAL.md](COMMERCIAL.md).
