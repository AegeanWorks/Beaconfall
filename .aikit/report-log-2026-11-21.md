# Beaconfall improvement log — opencode (Hy4 flash Free)

- **Author**: opencode (this session)
- **Date**: 2026-11-21
- **Scope**: the `projects/beaconfall` game, with findings about AIKit governance and the Keystone engine.
- **Note**: this file was deleted by a `reports/` inbox clean between turns and is recreated here from the session record, per `reports/README.md`. It is local-only (git-ignored) and should be triaged into `.idea-catcher/` when done. Earlier versions reached 52,788 bytes across 21 prior sections; this reconstruction condenses those findings and adds the latest iteration.

All work was done in the uncommitted Beaconfall working tree. Every iteration used failing-first tests, ran the full suite and all five project gates, and recorded a Phase 2 plan plus a Phase 4 `--checklists passed` checkpoint on the `beaconfall-game` task (taken over from `codex:beaconfall` once its lease expired). No commit or push was authorized, so the tree remains deliberately uncommitted.

## Verification trajectory

Starting baseline 48 tests; finished this session at **114 tests passing, exit 0**, **5/5 gates passed** (`python aikit.py check beaconfall --allow-dirty --all-gates`). Gates: hygiene, guidelines (knowledge base + README + hygiene rules), secrets, compat, test. The generated `.aikit/codebase_map.md` was regenerated twice when a stale map failed the guidelines gate, then stayed fresh for later iterations.

## Shipped improvements (18 iterations)

1. **One-key retry** — Space on the finish/time-up screen restarts the same course; R returns to course selection.
2. **Checkpoint split deltas** — each session best stores per-checkpoint times; later runs show `+/- x.xs` at each gate.
3. **Ghost car** — a 20 Hz position trace per best run, interpolated by elapsed time, rendered as a cyan node.
4. **HUD clarity** — NEXT checkpoint/finish distance, `NEW BEST!` banner.
5. **Collision flash** — car parts swap to a red emissive material while the collision message is active.
6. **Canyon course** — a third 13-boulder layout; F cycles classic → mirror → canyon; per-course records/splits/ghost.
7. **Boost trail** — a fixed 12-node pool of fading orange markers behind a boosting car.
8. **Speed-sensitive camera** — height/distance/FOV ease 9/14/60° → 11/19/70° with speed.
9. **Gate colours** — posts turn green as checkpoints clear; finish gate green only on a finish.
10. **Near misses** — close clean passes (1.15–1.7 m) show `NEAR MISS` and count, without time rewards.
11. **All-course record panel** — ready screen lists all three bests with a `>` selection marker.
12. **Finish banner** — 13 checkered post/flag nodes appear at 400 m.
13. **Finish-time delta** — signed comparison with the previous best on the finish screen and snapshot.
14. **Live pace indicator** — `PACE +/-x.xs VS BEST` interpolated from the best trace by distance.
15. **Persistent near-miss bests** — record files gained an additive `"near"` map and `load_near()`.
16. **HUD progress bar** — 20-cell ASCII bar with checkpoint ticks.
17. **Collision camera shake** — bounded deterministic offsets from the collision message timer.
18. **Low-time warning** — timer turns red and `TIME LOW` appears at ≤ 10 s remaining (latest, below).

## Findings: AIKit

1. **Generated map freshness is gate-decided, not edit-decided.** `check` failed once on a stale `.aikit/codebase_map.md`; regenerating it with `scripts/update_knowledge_base.py --workspace projects/beaconfall` fixed it. Later additions of methods, constants and a new module constant left the map fresh. The safe rule is to let the guidelines gate decide, not to regenerate after every edit.
2. **The gates-only summary can announce exit 0 while the process exits 1.** `3/5 gates passed ... accepted by --allow-dirty (exit 0)` appeared on a failing run whose real exit was 1; derive the parenthetical from the final verdict. A cheap-gate failure also labels the skipped test gate in the `Failed gate(s)` line.
3. **Ownership handoff is observable.** `aikit.py checkpoint ... --take-over --agent opencode:session` succeeded on an expired lease and recorded `continued from 'codex:beaconfall'`.
4. **UI proof is separate from gate proof.** `ui_required` is false; all five gates passed on HUD changes with no visual review. Canvas-double tests prove strings are emitted, not that they are legible.
5. **Additive state survives under `schema: 1` when defaults are total.** Both the canyon course key and the `"near"` map load from old files with zero/None defaults, with invalid values quarantining like bad times.
6. **Internal API changes still break test doubles.** After `_decode/_read` returned a pair, the `BrokenStore` stub lacked `load_near` and the new `record` signature; one stub update fixed it while the public `load()` stayed stable.
7. **A write must happen when either tracked value improves.** The original early-return in `RecordStore.record` would have dropped a better near-miss count on a slower time; fixed with `time_improved or near_improved`.
8. **Save path takes two locks per finish** (`record()` then `load_near()`); correct but a future refactor could return both maps from one call.
9. **Gate timings are load-sensitive, verdict is not.** Compat/test gates varied from ~1 s to ~20 s across runs; the project's `test_budget_ms: null` prevents host load from failing a green suite.
10. **Map staleness is change-sensitive.** Adding module-level symbols did not dirty it; the gate remains the authority.

## Findings: Keystone

1. **`ActionState.pressed` is a one-shot edge; `held` is continuous** — this makes one-key retry safe (holding Space from the start cannot re-trigger at the finish).
2. **The default 120-frame determinism check stays on the ready screen** (`"state": "ready"`), so scripted drives are needed as gameplay evidence.
3. **One key per named action remains a game-side workaround** (`InputMap.bind` stores a single key; Beaconfall synthesises four arrow actions).
4. **`Node.add_child()` returns `None`, `Scene.add()` returns the node** — the first flash implementation caused ten errors by assigning the return of `add_child`.
5. **`Material` and `Transform` are frozen slots dataclasses** — runtime appearance/motion requires assigning a different `Material` / a whole new `Transform`, so base materials and scales must be captured at build time.
6. **`Node.visible` + transform is a complete replay/effect primitive** — ghost, trail, banner and gates all needed no engine change; a fixed node pool is the right shape for transient effects.
7. **The whole game HUD is gated by the developer overlay.** `app.py::_draw_ui` returns early when the overlay is None; `overlay.py::HumanOverlay.build` returns an empty canvas before `game_draw` when `self.visible` is false. Hiding the overlay hides every game label.
8. **`PerspectiveCamera.look_at` must be re-applied after moving the camera** or orientation goes stale; camera state is plain mutable dataclass data. Camera reference speed (30 m/s) is soft-coupled to the boost cap.
9. **Swept crossing data is reusable** for near misses without new physics; crossing-kind ordering gives collisions/checkpoints precedence at the same distance.
10. **Replay data is bidirectional** — the ghost trace interpolates by both time (ghost) and distance (pace). Adding a snapshot key (e.g. `near_misses`, `finish_delta`) keeps determinism when hidden state is input-derived.
11. **ASCII is safest for the bitmap font** (`--`, `#`, `|`), avoiding glyph-coverage questions.
12. **Deterministic camera shake needs no RNG**; composed camera effects make fixed test expectations fragile.

## Process notes

- PowerShell reports native stderr as error records, so `python -m unittest ... | Select-Object` can show `Exit code: 1` even when Python exits 0; use `$LASTEXITCODE`.
- Two transient `-1` exits on parallel-shell test reruns were environmental; sequential reruns both returned 0 with the expected `Ran N tests ... OK`.
- Expected formatted values must be *derived*, not guessed: I mis-predicted a split delta (`-2.0s` vs correct `-1.0s`) and a progress-bar segment count (five dashes vs four). Implementation was correct; tests were fixed.
- For before/after stats, capture the prior value before updating it (finish delta) — otherwise a passing "value exists" test can hide a constant zero.

## Latest iteration: low-time warning (iteration 18)

**Feature.** `LOW_TIME = 10.0`; `Race.low_time()` is true only while racing with `remaining <= LOW_TIME`. The HUD then renders the timer in red `(1.0, 0.35, 0.2, 1.0)` and adds a `TIME LOW` label. Derived from state, so a checkpoint refill or restart clears it automatically.

**Evidence.** With three tests added and no implementation, `Ran 114 tests ... FAILED (failures=1, errors=2)`; after implementation `Ran 114 tests in 1.316s / OK`, exit 0. Demo (`scratch/beaconfall_lowtime_demo.py`):

```
remaining 40.0   low False  colour (0.95, 0.96, 1.0)  warning False
remaining 10.01  low False  colour (0.95, 0.96, 1.0)  warning False
remaining 10.0   low True   colour (1.0, 0.35, 0.2)   warning True
remaining 3.0    low True   colour (1.0, 0.35, 0.2)   warning True
```

`demo.py --scripted`: `checkpoints=0->3`, `state=ready->finished`, exit 0. All five project gates passed. Phase 4 `--checklists passed` checkpoint recorded. Tree remains uncommitted.

**Findings from this iteration.** (1) HUD colour is just an RGBA 4-tuple on `canvas.text`, so conditional emphasis is cheap but still subject to overlay-visibility coupling. (2) A derived predicate avoids a synchronisation flag — checkpoint/restart clear it for free. (3) The 10.0/10.01 boundary is pinned by its own test. (4) Displayed time is rounded to one decimal while the warning uses the raw value, so at ~10.01 the HUD can read `TIME 10.0` without the warning for ~10 ms — harmless, but worth noting.

## Nineteenth iteration: braking skid marks

**Feature.** A fixed pool of 14 dark flat marker nodes is created once in `build_scene()`. While
throttle is negative and speed exceeds 5 m/s, two marks (one per wheel side) are appended with life
decaying at 1.2/s using simulation `dt`; `_sync_scene()` positions them behind the car and hides
unused nodes. Releasing the brake or restarting clears them.

**Evidence.** With three tests added and no implementation, `test_race` failed to import
`SKID_LENGTH`; after implementation `Ran 117 tests in 1.798s / OK`, exit 0. Demo
(`scratch/beaconfall_skid_demo.py`):

```text
pool: 14 limit: 14
braking: 14 visible: 14
released: 0 visible: 0
long brake: 14 visible: 14
restart: 0 0
```

All five project gates passed; the codebase map needed no regeneration for the new constant.

**Findings from this iteration.** (1) Skid marks reuse the boost-trail fixed-pool pattern with a
different trigger (braking vs boosting) and material, confirming the pattern generalises to multiple
effects without engine changes. (2) I first stored `(node, side)` tuples in `skid_nodes` while the
tests expected plain nodes, causing two `AttributeError` failures; simplifying to a plain node list
(the car's x already encodes the side) fixed it. (3) The emission threshold uses simulation speed
*before* the braking step, so a single hard-brake frame still emits a mark — intentional, since the
visual should appear at the moment the brake is applied. (4) With trail, skids, banner and ghost,
the scene now holds ~50 fixed nodes, all created at build time; the 117-test suite stayed under
2 s, so the fixed-pool approach shows no measurable cost.

## Twentieth iteration: near-miss streak

**Feature.** `near_streak` increments on each near miss and resets on collision or restart;
`best_near_streak` keeps the peak for the run. The first near miss still reads `NEAR MISS`, later
ones show `Nx NEAR MISS STREAK`; both counters are in the snapshot. No time, medal or storage change.

**Evidence.** With three tests added and no implementation, `Ran 120 tests ... FAILED (errors=3)`
(missing `near_streak`); after implementation `Ran 120 tests in 2.089s / OK`, exit 0. Demo
(`scratch/beaconfall_streak_demo.py`):

```text
pass at 49.9 x -0.6 -> NEAR MISS streak 1 best 1
pass at 69.9 x 0.6   -> 2x NEAR MISS STREAK streak 2 best 2
collision            -> COLLISION -2 SEC hits 1 streak 0 best 2
snapshot: 0 2
```

All five project gates passed; the codebase map needed no regeneration.

**Findings from this iteration.** (1) The streak reuses the near-miss crossing kind, so it adds a
skill incentive with no new physics or timing path. (2) My first test attempts picked x positions
that were actually collisions or wide passes (the ROCKS x-coordinates alternate -2/+2/0), so the
streak never grew; reading the rock table and choosing gaps of 1.4 m and 0 m fixed them. Geometric
test fixtures must be derived from the actual course data, not guessed. (3) `best_near_streak` is
kept through a collision because it records the run's peak, while `near_streak` resets — the demo
pins that distinction. (4) The combo message overwrites the collision message only when their
crossing order puts the collision later; the crossing-kind sort keeps that ordering deterministic.

## Twenty-first iteration: rolling wheels

**Feature.** The four wheel nodes are retained at build time with their base orientation and
position. `_sync_scene()` composes a spin quaternion (rotation about the X axle, `distance / 0.24`
radians) with the base Z-axis orientation and assigns a new frozen `Transform`. Spin is derived
from distance, so restart resets it automatically.

**Evidence.** With two tests added and no implementation, `Ran 122 tests ... FAILED (errors=2)`
(missing `wheel_nodes`); after implementation `Ran 122 tests in 1.702s / OK`, exit 0. Demo
(`scratch/beaconfall_wheels_demo.py`):

```text
wheel count: 4
distance 0   rotation (0.707, 0.0, 0.0, 0.707)
distance 5   rotation (-0.387, -0.592, 0.592, -0.387)
distance 20  rotation (-0.479, -0.52, 0.52, -0.479)
distance 100 rotation (0.389, 0.59, -0.59, 0.389)
after restart equals base: True
```

All five project gates passed; the codebase map needed no regeneration for the new lists.

**Findings from this iteration.** (1) My first test asserted a specific quaternion Y-component,
but the wheels already carry a base 90° Z rotation, so the composed quaternion's components are not
a simple function of distance; I switched to asserting rotation changes with distance, is shared
across all wheels, and returns to base on restart — behaviour, not internal encoding. (2) Keystone's
`Quat.__mul__` lets the game compose spin with a fixed base orientation cleanly; with frozen
`Transform`, the whole transform must be rebuilt each frame, consistent with earlier findings.
(3) Using distance (not elapsed time) for spin keeps wheels physically consistent with travel even
when a checkpoint extends the frame or a collision slows the car mid-frame. (4) The wheel radius
0.24 is duplicated between mesh construction and the spin divisor; a future refactor should name it
a module constant to avoid the wheels slipping visually if the mesh changes.

## Twenty-second iteration: checkpoint burst

**Feature.** A fixed pool of 12 emissive nodes forms a particle ring. On a checkpoint crossing the
burst state is set to `(index, 1.0)`; each frame it decays at 2.0/s, and `_sync_scene()` renders the
nodes radiating from the gate at that world distance — radius grows and node size shrinks with life.
Collisions do not trigger it; restart clears it.

**Evidence.** With three tests added and no implementation, `test_race` failed to import
`BURST_LENGTH`; after implementation `Ran 125 tests in 1.831s / OK`, exit 0. Demo
(`scratch/beaconfall_burst_demo.py`):

```text
pool: 12 limit: 12
on checkpoint: 1 burst (1, 1.0) visible 12 scale 0.23
mid decay:     burst (1, 0.2)  visible 12 scale 0.086
after decay:   burst None      visible 0
after restart: burst None      visible 0
```

All five project gates passed; the codebase map needed no regeneration for the new constant.

**Findings from this iteration.** (1) The burst lives entirely in presentation state: `burst` is a
`(checkpoint, life)` tuple derived from a crossing and the frame timer, so it needs no game-rule
test beyond "triggered on checkpoint, not collision, decays, resets". (2) Keystone's frozen
`Transform` again required rebuilding each node's transform per frame; with 12 nodes and a simple
trig lookup the per-frame cost is negligible. (3) The burst reuses the same `z = 3 - (world_distance -
car_distance)` mapping as gates and banners, so it stays glued to the gate as the car approaches.
(4) The scene now holds several fixed node pools (trail, skids, burst, finish, ghost); the 125-test
suite stayed under 2 s, so the pooled-effect approach remains sound.

## Twenty-third iteration: corrupt-backup recovery bug fix

While reading `records.py` I found a real latent bug: the final fallback in `_read()` (reached when
BOTH the primary and its `.bak` are corrupt) returned `dict.fromkeys(COURSES)` — a single dict —
while every other path returns a `(times, near)` tuple. `load()` then did `_read(...)[0]`, raising
`KeyError: 0` (a dict has no integer key 0), and `load_near()` would fail the same way.

**Evidence.** A failing-first test wrote two corrupt files:
`Ran 126 tests ... FAILED (errors=1)` with `KeyError: 0`. After changing the fallback to return
`(dict.fromkeys(COURSES), dict.fromkeys(COURSES, 0))`, `Ran 126 tests in 1.931s / OK`, exit 0. A
direct reproduction confirms:

```text
Warning: invalid records moved to ...records.json.corrupt_...
Warning: invalid record backup moved to ...records.json.bak.corrupt_...
load: {'classic': None, 'mirror': None, 'canyon': None}
load_near: {'classic': 0, 'mirror': 0, 'canyon': 0}
```

The two quarantine files appear with distinct names (`records.json.corrupt_*` and
`records.json.bak.corrupt_*`). All five project gates passed.

**Findings from this iteration.** (1) This is a genuine defect, not a feature — the recovery path
that matters most (both copies bad) was the one broken. (2) It was invisible until the return type
became a tuple in an earlier iteration; before that, a bare dict was correct, so this is a
regression introduced by the persistence expansion. (3) Tuple-shaped returns are fragile under
partial edits; a future refactor to a small `Records` dataclass would make the contract explicit
and prevent this class of bug. (4) My first test asserted one quarantine file with a single glob,
but the backup quarantine uses a different filename pattern; I corrected the assertion to check
both patterns rather than weakening it.

## Twenty-fourth iteration: persistent best streak + Records dataclass

**Feature.** Added a third persisted map `streak` (best near-miss streak per course) and, to avoid
compounding the tuple fragility from the last bug, refactored the internal `_decode`/`_read` return
from a 2-tuple to a frozen `Records(times, near, streak)` dataclass with an `empty()` factory.
`load_streak()` is the new public accessor; `record()` gained a `best_streak` argument; `LiveGame`
loads, persists and displays it in the ready panel alongside time and near count.

**Evidence.** With three tests added and no implementation, `Ran 129 tests ... FAILED (failures=1,
errors=2)`; after implementation `Ran 129 tests in 5.643s / OK`, exit 0. Reload check:

```text
saved streak: {'classic': 6, 'mirror': 0, 'canyon': 0}
reloaded streak bests: {'classic': 6, 'mirror': 0, 'canyon': 0}
stored json streak: {'canyon': 0, 'classic': 6, 'mirror': 0}
```

Old two-field files load with a zero streak; invalid streak values quarantine like times; corrupt
backups still return `Records.empty()`. All five project gates passed.

**Findings from this iteration.** (1) A frozen dataclass with named fields removes the entire class
of index/shape bugs that caused the last iteration's regression — `_read()` returning the wrong
shape is now impossible without an attribute error, and `load*()` use `.times/.near/.streak`. (2)
Three `load*()` calls each take the lock and decode the file; a single `load_all()` returning the
dataclass would be cleaner, but `LiveGame` keeps them separate to preserve the public API, so the
cost is three reads at startup and three at each improved finish. (3) The ready panel now shows
three stats per course; the line is getting long (time, NM count, streak), which again argues for a
visual capture to confirm it fits at the minimum resolution. (4) This closes the durability gap
flagged in the near-miss-streak iteration: the combo stat now survives launches like times and near
counts.

## Twenty-fifth iteration: finish-screen split summary

**Feature.** `Race.split_summary()` returns one label per recorded checkpoint (`CPn X.Xs` plus a
signed `+/- X.Xs VS BEST` when a reference split exists). The finish screen lists them below the
finish delta, turning the transient per-gate messages into a reviewable breakdown.

**Evidence.** With three tests added and no implementation, `Ran 132 tests ... FAILED (errors=3)`
(missing `split_summary`); after implementation `Ran 132 tests in 3.261s / OK`, exit 0. Demo
(`scratch/beaconfall_summary_demo.py`), comparing a slower normal run against a boosted best:

```text
best splits:      {1: 5.66, 2: 9.83, 3: 13.99}
boosted best:     {1: 4.49, 2: 8.65, 3: 12.82}
slower run:       {1: 5.66, 2: 9.83, 3: 13.99}
summary: ['CP1 5.7s  +1.2s VS BEST', 'CP2 9.8s  +1.2s VS BEST', 'CP3 14.0s  +1.2s VS BEST']
```

**Findings from this iteration.** (1) One test set `state = "finished"` directly and hit
`TypeError: unsupported format string passed to NoneType` on the existing best-time label; I fixed
the fixture by also setting `best_times["classic"]`, since a real finish always has a best via
`_finish()`. (2) The split summary reuses `current_splits` and `best_splits`, so it adds a feature
with no new state. (3) A first run shows three plain labels with no delta, because its own splits
become the reference — correct, and pinned by a test. (4) The finish screen is now quite dense
(time/hits/near misses, medal, record, finish delta, three split lines); layout still rests on font
metrics, not a frame capture.

**Environmental note.** The first full-gate run failed only on `secrets` with a `RuntimeError`
that the Rust native library `aikit_native.dll` was stale against `lib.rs` — the concurrent
`rust-migration` agent (owned by antigravity) had edited the source and multiple `cargo`/`rustc`
processes were rebuilding. No secret was detected; I did not rebuild (to avoid contending with
that agent's build lock). Retrying after the build finished returned `[OK] No credential patterns`
and all 5 gates passed. This is a transient cross-agent condition, not a Beaconfall defect.

## Twenty-sixth iteration: persistent best splits

**Feature.** The `Records` dataclass gained a `splits` map (per-course checkpoint times). JSON keys
are strings (`"1"`, `"2"`, `"3"`) and are validated on decode (digits 1–3, finite positive values);
`load_splits()` and `record(..., splits=...)` expose it, and `LiveGame` restores it at startup and
saves it with a new best time. Old files load with empty splits, so split deltas after a relaunch
become available as soon as a best time exists.

**Evidence.** With three tests added and no implementation, `Ran 135 tests ... FAILED (failures=1,
errors=2)`; after implementation `Ran 135 tests in 3.723s / OK`, exit 0. Relaunch check:

```text
saved splits:   {1: 5.0, 2: 9.0, 3: 13.0}
reloaded splits:{1: 5.0, 2: 9.0, 3: 13.0}
delta after relaunch: CHECKPOINT +12 SEC  +0.5s
```

All five project gates passed.

**Findings from this iteration.** (1) I shadowed the `splits` function argument with the persisted
`splits` map inside `record()`, so the new splits were never written; a direct reproduction exposed
it and renaming the argument fixed it. This is the same class of bug as the earlier tuple issue:
careless state naming inside a method that already has many similarly-named values. (2) My test
first recorded the same time as the existing best (20.0), so `time_improved` was false and no write
happened; using a faster time (19.0) is required because splits are saved only with a new best.
(3) JSON object keys must be strings, so the decode/encode pair round-trips `int` checkpoint
numbers through `str`; the test asserts the int keys come back, guarding that conversion.
(4) Splits, near count and streak are now all durable; the three `load*()` calls each re-read and
re-decode the file in `LiveGame.__init__`, which is three locks at startup — correct but a natural
target for a single `load_all()` returning the whole `Records` dataclass.

## Twenty-seventh iteration: gameplay determinism verifier

**Feature.** New `verify_gameplay.py` drives two identical scripted races (using `demo.steer_around`)
and hashes **full internal state** — the public snapshot plus `current_trace`, `current_splits`,
`near_indices`, `hit_indices`, `best_times` and the streak counters. `play.py --verify-gameplay`
routes to it (added to the offline spec), with `--frames` and `--no-sprint` options.

**Evidence.** With the new test module added and no implementation, `Ran 136 tests ... FAILED
(ModuleNotFoundError: verify_gameplay)`; after implementation `Ran 141 tests in 9.663s / OK`,
exit 0. Side-by-side commands:

```text
python play.py --verify-determinism --frames 120
  "state": "ready",  "hash": "a0021293720afdf26da363a58fb0201e",  "ok": true
python play.py --verify-gameplay --frames 120
  "distance": 29.851, "hash": "78acb8e954c256f038cd93be01f2a6ba", "ok": true, "state": "racing"
```

All five project gates passed; the codebase map regenerated to include the new module.

**Findings from this iteration.** (1) This closes a gap I recorded in the very first findings
report: the engine's `--verify-determinism` passes while the game sits on the ready screen and
hashes only the public snapshot. The new check actually drives and covers hidden state. (2) The
verifier uses `hashlib.md5` over sorted JSON with `default=str` to handle `set`→sorted-list and
floats; the hash is a change detector, not a security primitive, so MD5 is acceptable here. (3) The
flag is intercepted in `play.py::main` before engine import, so it works without the Keystone
checkout's full CLI path for this one command — though `demo.py` and `verify_gameplay.py` still
import Keystone modules. (4) A `RaceStub` in the tests proves `full_state()` includes fields absent
from `snapshot()`, which guards against someone later trimming the hidden-state coverage.

## Twenty-eighth iteration: persistent last-session summary

**Feature.** The record file gained a `last` map with the most recent run's time, medal, hits,
near misses and best streak per course. `LiveGame` writes it on every finish (even when no best
improves) and restores it at startup; the ready screen shows `LAST GOLD 17.5s ...` for the selected
course. Old files load with empty summaries; a shared `_valid_last` validator rejects bad medals,
non-finite times and out-of-range counts.

**Evidence.** With three tests added and no implementation, `Ran 144 tests ... FAILED (failures=1,
errors=2)`; after implementation `Ran 144 tests in 8.249s / OK`, exit 0. Reload check:

```text
last sessions: {'hits': 0, 'medal': 'GOLD', 'near_misses': 2, 'streak': 3, 'time': 17.51...}
ready label: ['LAST GOLD 17.5s  0 HITS  2 NM  3x STREAK']
```

All five project gates passed.

**Findings from this iteration.** (1) Writing the summary had to move out of the
`improved_time or improved_near or improved_streak` guard — a last run is worth recording even when
it beats nothing. The guard now also fires when `last is not None`. (2) My test expected GOLD at
18.5 s, but the medal rule is `<18`, so it was SILVER; I used 17.5 s to match the intended case.
(3) `_valid_last` requires exactly the five expected keys, so an old or malformed summary is
quarantined rather than partially displayed — stricter than the per-field defaults used elsewhere.
(4) `record()` now has five optional arguments; the call site in `LiveGame` is positional and easy
to misalign. A future refactor should pass a small dataclass (e.g. `RunResult`) instead.

## Twenty-ninth iteration: lifetime totals + keyword-arg call

**Feature.** The record file gained a `totals` map with lifetime finishes and golds per course,
validated on decode and defaulted for old files. `LiveGame` increments it on every finish (a gold
adds to both counters), restores it at startup, and the ready screen shows
`LIFETIME N FINISHES  M GOLDS`. I also changed the `record()` call site to use keyword arguments
for all optional values, addressing the misalignment risk noted last iteration.

**Evidence.** With three tests added and no implementation, `Ran 147 tests ... FAILED (failures=1,
errors=2)`; after implementation `Ran 147 tests in 3.927s / OK`, exit 0. Two-finish reload check:

```text
totals: {'finishes': 2, 'golds': 2}
labels: ['LIFETIME 2 FINISHES  2 GOLDS', 'LAST GOLD 17.5s  0 HITS  0 NM  0x STREAK']
```

All five project gates passed.

**Findings from this iteration.** (1) Totals are derived from the in-memory value at finish and
written under the same lock as everything else; two sequential `LiveGame` instances in separate
processes would both read the current totals before incrementing, so under true concurrency one
finish could be lost. The lock protects the write but not the read-modify-write across instances —
a known limitation of updating aggregates from the client rather than inside `record()`. (2) The
`BrokenStore` test double needed `load_totals` and the extended `record` signature; with keyword
args the test double's parameter names now matter, which is a better contract than positional
order. (3) The ready-screen block is growing (best line, three course rows, LIFETIME, LAST); the
recent README ceiling change from 37,500 to 40,000 characters gives more documentation headroom,
but the on-screen layout still lacks a visual capture. (4) `record()` now has seven parameters; a
`RunResult` dataclass would be cleaner than either positional or keyword soup, and remains a
sensible future refactor.

## Thirtieth iteration: atomic finish_run fixes lost updates

**Feature.** `RecordStore.finish_run()` performs the entire finish update — best time, near count,
streak, splits, last summary and lifetime total increments — inside one lock and one atomic write,
returning the updated `Records`. `LiveGame` now uses it instead of computing totals from a
pre-lock read and then calling seven separate `load*()` methods.

**Evidence.** A failing-first two-process test launched two `finish_run` calls behind a barrier:
`Ran 148 tests ... FAILED (subprocess.CalledProcessError ... finish_run)`; after implementation
`Ran 148 tests in 4.130s / OK`, exit 0. The isolated concurrency test passed in 0.198 s with both
finishes counted (`finishes: 2, golds: 2`). Three sequential finishes gave
`times 17.51, totals {'finishes': 3, 'golds': 3}, last medal GOLD`. All five project gates passed.

**Findings from this iteration.** (1) This fixes the real defect I recorded last iteration: the
lock protected each write but not the client-side read-modify-write of aggregate totals across
instances. Moving the increment inside the lock makes concurrent finishes count correctly. (2) The
same change collapses seven lock/decode cycles per finish to one, addressing the efficiency note
from two earlier iterations. (3) `record()` is kept for backward compatibility with the older
tests and as a lower-level setter; having two write paths is a maintenance cost, and a future
cleanup should make `record()` delegate to a shared private writer. (4) The `BrokenStore` test
double needed a `finish_run` method; its parameter list is now `*args`, which keeps the failure
test focused on the warning path rather than mirroring a long signature. (5) The disk-space
preflight moved before the lock in `finish_run`, so a full disk fails fast instead of after
acquiring the lock — a small improvement over `record()`.

## Thirty-first iteration: unified record writer

**Feature.** Extracted a private `RecordStore._commit(saved)` that encodes, backs up and atomically
writes a `Records` object. Both `record()` and `finish_run()` now call it, so there is one canonical
durability sequence instead of two copies. Public signatures and behaviour are unchanged.

**Evidence.** A characterization test pinning the JSON keys of both paths was added before the
change (`Ran 149 tests ... OK`), then the write logic was deduplicated. The golden JSON captured
before and after the refactor is byte-identical for both paths (same keys, values, ordering).
`Ran 149 tests in 3.133s / OK`, exit 0; all five project gates passed; no README change was needed.

**Findings from this iteration.** (1) The two write paths had duplicated the same eight-line
encode/backup/write sequence; a future fix to atomicity now needs to be made once. (2) The disk
preflight remains in different places — before the lock in `finish_run`, inside the lock in
`record()` — because moving it would change failure timing; the shared writer intentionally does
not own that check. (3) A pure refactor like this is best verified by a golden-output comparison,
not only by tests that assert the same behaviour they always did; the byte-for-byte match is the
stronger evidence here. (4) No user-visible change means the project README stays valid, which the
guidelines gate confirmed.

## Cumulative state

- 149 passing tests, exit 0; 5/5 project gates green; codebase map fresh.
- All helper scripts and this report live in git-ignored `scratch/` and `reports/`.
- No secrets, credentials, commits or pushes were handled.
- These are targeted observations from iterative game work, not a full audit. A human playthrough and an OpenGL frame capture remain unverified; the growing HUD has no visual layout assertion at the minimum supported resolution.
