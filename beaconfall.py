"""Beaconfall: a compact downhill time trial for the Keystone engine."""
from __future__ import annotations

import math

from keystone.assets import AssetRegistry
from keystone.geometry import Material
from keystone.math3d import Quat, Vec3
from keystone.primitives import cone, cube, cylinder, plane, sphere
from keystone.scene import Node, Scene, Transform
from keystone.ui.font import text_width

FINISH = 400.0
START_TIME = 45.0
CHECKPOINT_BONUS = 12.0
GOLD_TIME = 18.0
GOLD_HITS = 0
SILVER_TIME = 25.0
SILVER_HITS = 2
BRONZE_TIME = SILVER_TIME
COURSES = ("classic", "mirror", "canyon")
ROCKS = tuple((float(z), float(x)) for z, x in [
    (35, 3.4), (50, -2), (70, 2), (90, 0), (120, -2), (145, 2), (170, 0),
    (195, -3.4), (205, 2), (225, -2), (250, 0), (280, 2), (315, -2), (340, 0), (375, 2),
])
CANYON_ROCKS = tuple((float(z), float(x)) for z, x in [
    (30, 0), (55, 3.2), (80, -3.2), (105, 1.6), (135, -1.6),
    (165, 0), (195, 3.4), (225, -3.4), (255, 1.8), (285, -1.8),
    (315, 0), (345, 3.0), (375, -3.0),
])
TRAIL_LENGTH = 12
SKID_LENGTH = 14
BURST_LENGTH = 12
CONFETTI_COUNT = 16
CONFETTI_DECAY = 2.0
SPEED_BARS = 8
SPEED_BAR_MAX = 30.0
SPEED_BAR_UNLIT = Material(color=Vec3(0.1, 0.12, 0.14))
SPEED_BAR_LIT = Material(color=Vec3(0.2, 1.0, 0.5), emissive=Vec3(0.05, 0.4, 0.15))
DRIFT_STEER = 0.8
DRIFT_SPEED = 15.0
BRAKE_LIGHT_SPEED = 5.0
MINIMAP_DEPTH = 80.0
MINIMAP_ROWS = 8
LOW_TIME = 10.0
LOW_BOOST = 1.0
HIGH_SPEED = 25.0
HIT_GAP = 1.15
NEAR_MISS_GAP = 1.7
PROXIMITY_DISTANCE = 20.0
PICKUP_STATIONS = (200.0, 280.0, 360.0)
PICKUP_DISTANCE = PICKUP_STATIONS[0]
PICKUP_X = 3.0
CAMERA_REF_SPEED = 30.0
GATE_MATERIAL = Material(color=Vec3(0.08, 0.75, 0.9))
BRAKE_MATERIAL = Material(color=Vec3(1.0, 0.1, 0.05), emissive=Vec3(0.8, 0.05, 0.02))
BOOST_LAMP_MATERIAL = Material(color=Vec3(1.0, 0.95, 0.6), emissive=Vec3(0.9, 0.8, 0.3))
GHOST_MATERIAL = Material(color=Vec3(0.25, 0.85, 1.0), emissive=Vec3(0.1, 0.35, 0.45))
GHOST_AHEAD_MATERIAL = Material(color=Vec3(0.2, 0.95, 0.45), emissive=Vec3(0.05, 0.4, 0.1))
GHOST_BEHIND_MATERIAL = Material(color=Vec3(1.0, 0.55, 0.15), emissive=Vec3(0.5, 0.2, 0.03))
CLEARED_GATE_MATERIAL = Material(color=Vec3(0.2, 0.95, 0.45), emissive=Vec3(0.05, 0.4, 0.1))
DAMAGE_MATERIAL = Material(color=Vec3(1.0, 0.15, 0.1), emissive=Vec3(0.65, 0.05, 0.02))


class Race:
    """Fixed-step driving simulation and Keystone game adapter."""
    name = "beaconfall"

    def __init__(self) -> None:
        self.assets = AssetRegistry()
        self.component_types = {}
        self.scene = None
        self.car = None
        self.ghost = None
        self.show_ghost = True
        self.pickup = None
        self.car_materials = []
        self.tail_lamps = []
        self.headlamps = []
        self.braking = False
        self.wheel_nodes = []
        self.wheel_specs = []
        self.finish_nodes = []
        self.trail_nodes = []
        self.trail = []
        self.skid_nodes = []
        self.skids = []
        self.burst_nodes = []
        self.burst = None
        self.confetti_nodes = []
        self.confetti = None
        self.speed_bars = []
        self.boosting = False
        self.camera_target = Vec3(0, 0, -8)
        self.rocks = []
        self.gates = []
        self.scenery = []
        self.markings = []
        self.course = "classic"
        self.best_times = dict.fromkeys(COURSES)
        self.best_splits = {course: {} for course in COURSES}
        self.best_traces = {course: [] for course in COURSES}
        self.best_nears = dict.fromkeys(COURSES, 0)
        self.best_streak_bests = dict.fromkeys(COURSES, 0)
        self.last_sessions = {course: {} for course in COURSES}
        self.lifetime_totals = {course: {"finishes": 0, "golds": 0} for course in COURSES}
        self.lifetime_distance = dict.fromkeys(COURSES, 0.0)
        self.best_medals = dict.fromkeys(COURSES, "")
        self.clean_finishes = dict.fromkeys(COURSES, 0)
        self.record_label = "SESSION BEST"
        self.reset()

    @property
    def course_rocks(self) -> tuple[tuple[float, float], ...]:
        if self.course == "mirror":
            return tuple((z, -x) for z, x in ROCKS)
        return CANYON_ROCKS if self.course == "canyon" else ROCKS

    @property
    def best_time(self) -> float | None:
        return self.best_times[self.course]

    def reset(self) -> None:
        self.distance = 0.0
        self.x = 0.0
        self.speed = 0.0
        self.steering = 0.0
        self.elapsed = 0.0
        self.remaining = START_TIME
        self.checkpoint = 0
        self.hits = 0
        self.checkpoint_bonus = 0.0
        self.collision_penalty = 0.0
        self.boost = 3.0
        self.state = "ready"
        self.hit_indices = set()
        self.collision_side = ""
        self.pickup_collected = False
        self.pickups_collected = 0
        self.pickup_station = 0
        self.near_indices = set()
        self.near_misses = 0
        self.near_streak = 0
        self.best_near_streak = 0
        self.current_splits = {}
        self.current_trace = []
        self.trail = []
        self.skids = []
        self.burst = None
        self.confetti = None
        self.boosting = False
        self.braking = False
        self.new_best = False
        self.finish_delta = None
        self.message = ""
        self.message_time = 0.0

    def bind_input(self, mapping: object) -> None:
        mapping.bind("restart", "r")
        mapping.bind("start", "space")
        mapping.bind("course", "f")
        mapping.bind("ghost", "g")
        for action, key in (("arrow_up", "up"), ("arrow_down", "down"),
                            ("arrow_left", "left"), ("arrow_right", "right")):
            mapping.bind(action, key)

    def actions(self) -> dict[str, object]:
        return {"axes": ["forward", "right"], "buttons": ["start", "restart", "course", "ghost", "sprint",
                "arrow_up", "arrow_down", "arrow_left", "arrow_right"]}

    def build_scene(self) -> Scene:
        scene = Scene()
        scene.camera.position = Vec3(0, 9, 14)
        scene.camera.look_at(self.camera_target)
        ground = Material(color=Vec3(0.11, 0.18, 0.20))
        road = Material(color=Vec3(0.19, 0.23, 0.26))
        snow = Material(color=Vec3(0.65, 0.78, 0.78))
        orange = Material(color=Vec3(0.95, 0.38, 0.08))
        red = Material(color=Vec3(0.9, 0.16, 0.1))
        pine = Material(color=Vec3(0.08, 0.34, 0.29))
        bark = Material(color=Vec3(0.30, 0.19, 0.12))
        rubber = Material(color=Vec3(0.035, 0.045, 0.055))
        glass = Material(color=Vec3(0.12, 0.32, 0.4))
        lamps = Material(color=Vec3(1.0, 0.82, 0.35))
        mesh = cube(1.0)
        foliage_mesh = cone(radius=0.8, height=2.8, segments=7)
        wheel_mesh = cylinder(radius=0.24, height=0.25, segments=12)
        boulder_mesh = sphere(radius=0.55, segments=8, rings=4)
        scene.add(Node("ground", mesh=plane(200), material=ground))

        def box(name: str, pos: Vec3, size: Vec3, material: Material) -> Node:
            return scene.add(Node(name, transform=Transform(position=pos, scale=size), mesh=mesh, material=material))

        box("road", Vec3(0, 0.04, -10), Vec3(9, 0.08, 80), road)
        for x in (-4.8, 4.8):
            box("snow bank", Vec3(x, 0.3, -10), Vec3(0.5, 0.6, 80), snow)
        self.scenery = []
        for index in range(14):
            for side in (-1, 1):
                x = side * (6 + (index % 3) * 1.5)
                tree = scene.add(Node("pine", transform=Transform(position=Vec3(x, 0, -index * 6))))
                tree.add_child(Node("trunk", transform=Transform(position=Vec3(0, 0.5, 0),
                               scale=Vec3(0.3, 1, 0.3)), mesh=mesh, material=bark))
                tree.add_child(Node("foliage", transform=Transform(position=Vec3(0, 2.0, 0)),
                               mesh=foliage_mesh, material=pine))
                self.scenery.append((tree, x, index * 6.0))
        self.markings = [box("road marking", Vec3(0, 0.10, -index * 6),
                             Vec3(0.12, 0.04, 2.5), snow) for index in range(10)]
        self.car = scene.add(Node("car", transform=Transform(position=Vec3(0, 0, 3))))
        self.car_materials = []
        self.tail_lamps = []
        def car_part(name: str, pos: Vec3, size: Vec3, material: Material) -> Node:
            node = Node(name, transform=Transform(position=pos, scale=size), mesh=mesh, material=material)
            self.car.add_child(node)
            self.car_materials.append((node, material))
            return node

        car_part("chassis", Vec3(0, 0.48, 0), Vec3(1.2, 0.42, 2), orange)
        car_part("hood", Vec3(0, 0.68, -0.6), Vec3(1.1, 0.2, 0.65), orange)
        car_part("cabin", Vec3(0, 0.87, 0.25), Vec3(0.95, 0.45, 0.85), glass)
        car_part("roof", Vec3(0, 1.12, 0.25), Vec3(1, 0.1, 0.9), orange)
        for x in (-0.63, 0.63):
            for z in (-0.65, 0.65):
                rotation = Quat.from_axis_angle(Vec3(0, 0, 1), 1.5707963267948966)
                wheel = Node("wheel", transform=Transform(position=Vec3(x, 0.3, z),
                             rotation=rotation), mesh=wheel_mesh, material=rubber)
                self.car.add_child(wheel)
                self.car_materials.append((wheel, rubber))
                self.wheel_nodes.append(wheel)
                self.wheel_specs.append((Vec3(x, 0.3, z), rotation))
            headlamp = car_part("headlamp", Vec3(x * 0.7, 0.53, -1.02), Vec3(0.25, 0.15, 0.05), lamps)
            self.headlamps.append(headlamp)
            lamp = car_part("tail lamp", Vec3(x * 0.7, 0.53, 1.02), Vec3(0.25, 0.15, 0.05), red)
            self.tail_lamps.append(lamp)
        self.rocks = [scene.add(Node("boulder", transform=Transform(position=Vec3(x, 0.55, -100)),
                                     mesh=boulder_mesh, material=red)) for _, x in ROCKS]
        pickup_material = Material(color=Vec3(1.0, 0.9, 0.2), emissive=Vec3(0.7, 0.6, 0.05))
        self.pickup = scene.add(Node("boost pickup", transform=Transform(position=Vec3(PICKUP_X, 0.9, -100),
                               scale=Vec3(0.5, 0.5, 0.5)), mesh=boulder_mesh, material=pickup_material))
        self.gates = []
        for _ in range(4):
            left = box("gate left", Vec3(-4, 1.3, -100), Vec3(0.3, 2.6, 0.3), GATE_MATERIAL)
            right = box("gate right", Vec3(4, 1.3, -100), Vec3(0.3, 2.6, 0.3), GATE_MATERIAL)
            self.gates.append((left, right))
        white = Material(color=Vec3(0.92, 0.94, 0.96))
        black = Material(color=Vec3(0.05, 0.05, 0.06))
        self.finish_nodes = []
        for x in (-4.0, 4.0):
            size = Vec3(0.35, 4.0, 0.35)
            node = box("finish post", Vec3(x, 2.0, -100), size, black)
            self.finish_nodes.append((node, x, 2.0, size))
        for index in range(11):
            x = -3.5 + index * 0.7
            size = Vec3(0.7, 0.7, 0.2)
            node = box("finish flag", Vec3(x, 3.6, -100), size, white if index % 2 == 0 else black)
            self.finish_nodes.append((node, x, 3.6, size))
        self.ghost = scene.add(Node("ghost", transform=Transform(position=Vec3(0, 0.5, -100),
                                   scale=Vec3(1.2, 1.0, 2.0)), mesh=mesh, material=GHOST_MATERIAL))
        self.ghost.visible = False
        trail_material = Material(color=Vec3(1.0, 0.55, 0.15), emissive=Vec3(0.8, 0.3, 0.05))
        self.trail_nodes = []
        for _ in range(TRAIL_LENGTH):
            node = Node("boost trail", transform=Transform(position=Vec3(0, 0.4, -100),
                        scale=Vec3(0.1, 0.1, 0.1)), mesh=mesh, material=trail_material)
            node.visible = False
            scene.add(node)
            self.trail_nodes.append(node)
        skid_material = Material(color=Vec3(0.06, 0.06, 0.07))
        self.skid_nodes = []
        for _ in range(SKID_LENGTH):
            node = Node("skid", transform=Transform(position=Vec3(0, 0.05, -100),
                        scale=Vec3(0.18, 0.02, 0.4)), mesh=mesh, material=skid_material)
            node.visible = False
            scene.add(node)
            self.skid_nodes.append(node)
        burst_material = Material(color=Vec3(0.5, 1.0, 0.7), emissive=Vec3(0.2, 0.6, 0.3))
        self.burst_nodes = []
        for _ in range(BURST_LENGTH):
            node = Node("checkpoint burst", transform=Transform(position=Vec3(0, 1.3, -100),
                        scale=Vec3(0.2, 0.2, 0.2)), mesh=mesh, material=burst_material)
            node.visible = False
            scene.add(node)
            self.burst_nodes.append(node)
        self.confetti_nodes = []
        confetti_colors = (
            Material(color=Vec3(1.0, 0.4, 0.4)),
            Material(color=Vec3(0.4, 0.7, 1.0)),
            Material(color=Vec3(1.0, 0.9, 0.3)),
        )
        for index in range(CONFETTI_COUNT):
            node = Node("confetti", transform=Transform(position=Vec3(0, 0.5, -100),
                        scale=Vec3(0.15, 0.15, 0.05)), mesh=mesh,
                        material=confetti_colors[index % len(confetti_colors)])
            node.visible = False
            scene.add(node)
            self.confetti_nodes.append(node)
        self.speed_bars = []
        for index in range(SPEED_BARS):
            node = Node("speed bar", transform=Transform(
                position=Vec3(0, 1.2, -100),
                scale=Vec3(0.1, 0.1 + index * 0.02, 0.05)), mesh=mesh, material=SPEED_BAR_UNLIT)
            node.visible = False
            scene.add(node)
            self.speed_bars.append(node)
        self.scene = scene
        self._sync_scene()
        return scene

    def _sync_scene(self) -> None:
        if self.car is None:
            return
        self.car.transform = Transform(position=Vec3(self.x, 0, 3),
                                       rotation=Quat.from_axis_angle(Vec3(0, 1, 0), -0.24 * self.steering))
        if self.scene is not None:
            ratio = min(1.0, max(0.0, self.speed) / CAMERA_REF_SPEED)
            camera = self.scene.camera
            shake = 0.0
            if self.message == "COLLISION -2 SEC" and self.message_time > 0:
                shake = 0.25 * min(1.0, self.message_time / 2.0)
            camera.position = Vec3(
                shake * math.cos(self.message_time * 20.0),
                9 + ratio * 2.0 + shake * math.sin(self.message_time * 17.0),
                14 + ratio * 5.0)
            camera.fov_y = 60.0 + ratio * 10.0
            camera.look_at(self.camera_target)
        if self.burst is None:
            for node in self.burst_nodes:
                node.visible = False
        else:
            burst_index, burst_life = self.burst
            burst_z = 3 - (burst_index * 100.0 - self.distance)
            radius = 0.6 + (1.0 - burst_life) * 2.2
            for index, node in enumerate(self.burst_nodes):
                angle = index * (2 * 3.141592653589793 / BURST_LENGTH)
                node.visible = -45 < burst_z < 8
                size = 0.05 + 0.18 * burst_life
                node.transform = Transform(
                    position=Vec3(radius * math.cos(angle), 1.3 + radius * math.sin(angle), burst_z),
                    scale=Vec3(size, size, size))
        if self.confetti is None:
            for node in self.confetti_nodes:
                node.visible = False
        else:
            life = self.confetti
            spread = (1.0 - life) * 3.0
            for index, node in enumerate(self.confetti_nodes):
                angle = index * (2 * 3.141592653589793 / CONFETTI_COUNT)
                node.visible = True
                node.transform = Transform(
                    position=Vec3(spread * math.cos(angle), 0.5 + spread * math.sin(angle), 3),
                    scale=Vec3(0.15 * life, 0.15 * life, 0.05))
        spin = Quat.from_axis_angle(Vec3(1, 0, 0), self.distance / 0.24)
        for node, (position, base) in zip(self.wheel_nodes, self.wheel_specs):
            node.transform = Transform(position=position, rotation=spin * base)
        damaged = self.message == "COLLISION -2 SEC" and self.message_time > 0
        for node, material in self.car_materials:
            node.material = DAMAGE_MATERIAL if damaged else material
        for node in self.tail_lamps:
            if self.braking and not damaged:
                node.material = BRAKE_MATERIAL
        for node in self.headlamps:
            if self.boosting and not damaged:
                node.material = BOOST_LAMP_MATERIAL
        lit = self.lit_speed_bars()
        for index, node in enumerate(self.speed_bars):
            node.visible = index < lit
            node.material = SPEED_BAR_LIT if index < lit else SPEED_BAR_UNLIT
            node.transform = Transform(
                position=Vec3(self.x - 0.45 + index * 0.13, 1.2, 1.98),
                scale=Vec3(0.1, 0.1 + index * 0.02, 0.05))
        for index, node in enumerate(self.markings):
            z = 9 - ((index * 6 - self.distance) % 60)
            node.transform = Transform(position=Vec3(0, 0.10, z), scale=Vec3(0.12, 0.04, 2.5))
        for node, x, offset in self.scenery:
            z = 5 - ((offset - self.distance) % 84)
            node.visible = z > -45
            node.transform = Transform(position=Vec3(x, 0, z))
        for node, (distance, x) in zip(self.rocks, self.course_rocks):
            z = 3 - (distance - self.distance)
            node.visible = -45 < z < 8 and distance > self.distance - 2
            node.transform = Transform(position=Vec3(x, 0.55, z))
        finish_z = 3 - (FINISH - self.distance)
        for node, x, y, size in self.finish_nodes:
            node.visible = -45 < finish_z < 8
            node.transform = Transform(position=Vec3(x, y, finish_z), scale=size)
        pulse = self.burst[1] if self.burst and self.burst[0] else 0.0
        for index, pair in enumerate(self.gates, 1):
            z = 3 - (index * 100 - self.distance)
            cleared = index <= self.checkpoint or (index == 4 and self.state == "finished")
            material = CLEARED_GATE_MATERIAL if cleared else GATE_MATERIAL
            gate_pulse = pulse if self.burst and self.burst[0] == index else 0.0
            scale = Vec3(0.3 * (1 + gate_pulse * 0.5), 2.6 * (1 + gate_pulse * 0.5), 0.3)
            for x, node in zip((-4.0, 4.0), pair):
                node.visible = -45 < z < 8
                node.transform = Transform(position=Vec3(x, 1.3, z), scale=scale)
                node.material = material
        if self.pickup is not None:
            active = self.pickup_station < len(PICKUP_STATIONS)
            self.pickup.visible = False
            if active:
                pickup_z = 3 - (PICKUP_STATIONS[self.pickup_station] - self.distance)
                self.pickup.visible = -45 < pickup_z < 8
                self.pickup.transform = Transform(position=Vec3(PICKUP_X, 0.9, pickup_z),
                                                  scale=Vec3(0.5, 0.5, 0.5))
        if self.ghost is not None:
            ghost = self.ghost_state()
            self.ghost.visible = self.show_ghost and ghost is not None
            pace = self.pace_delta() if ghost is not None else None
            self.ghost.material = (GHOST_MATERIAL if pace is None
                                   else GHOST_AHEAD_MATERIAL if pace < 0
                                   else GHOST_BEHIND_MATERIAL)
            if ghost is not None:
                ghost_x, ghost_distance = ghost
                self.ghost.transform = Transform(
                    position=Vec3(ghost_x, 0.5, 3 - (ghost_distance - self.distance)))
        for index, node in enumerate(self.trail_nodes):
            if index >= len(self.trail):
                node.visible = False
                continue
            x, distance, life = self.trail[index]
            size = 0.08 + 0.14 * life
            node.visible = True
            node.transform = Transform(position=Vec3(x, 0.4, 4 - (distance - self.distance)),
                                       scale=Vec3(size, size, size))
        for index, node in enumerate(self.skid_nodes):
            if index >= len(self.skids):
                node.visible = False
                continue
            x, distance, _, life = self.skids[index]
            node.visible = True
            node.transform = Transform(position=Vec3(x, 0.05, 3 - (distance - self.distance)),
                                       scale=Vec3(0.18, 0.02, 0.3 + 0.2 * life))

    def ghost_state(self) -> tuple[float, float] | None:
        """Interpolate the best run's (x, distance) at the current elapsed time."""
        trace = self.best_traces[self.course]
        if self.state != "racing" or not trace:
            return None
        if self.elapsed <= trace[0][0]:
            return trace[0][1], trace[0][2]
        for index in range(1, len(trace)):
            before, after = trace[index - 1], trace[index]
            if self.elapsed <= after[0]:
                span = after[0] - before[0]
                fraction = (self.elapsed - before[0]) / span if span else 1.0
                return (before[1] + (after[1] - before[1]) * fraction,
                        before[2] + (after[2] - before[2]) * fraction)
        return trace[-1][1], trace[-1][2]

    def pace_delta(self) -> float | None:
        """Seconds slower (+) or faster (-) than the best run at this distance."""
        trace = self.best_traces[self.course]
        if len(trace) < 2:
            return None
        if self.distance <= trace[0][2]:
            best_elapsed = trace[0][0]
        elif self.distance >= trace[-1][2]:
            best_elapsed = trace[-1][0]
        else:
            best_elapsed = trace[-1][0]
            for index in range(1, len(trace)):
                before, after = trace[index - 1], trace[index]
                if before[2] <= self.distance <= after[2]:
                    span = after[2] - before[2]
                    fraction = (self.distance - before[2]) / span if span else 1.0
                    best_elapsed = before[0] + (after[0] - before[0]) * fraction
                    break
        return self.elapsed - best_elapsed

    def _finish(self) -> None:
        previous = self.best_time
        self.state = "finished"
        self.confetti = 1.0
        self.finish_delta = self.elapsed - previous if previous is not None else None
        if previous is None or self.elapsed < previous:
            self.best_times[self.course] = self.elapsed
            self.best_splits[self.course] = dict(self.current_splits)
            self.best_traces[self.course] = list(self.current_trace)
            self.new_best = True
        self._sync_scene()

    def update(self, dt: float, actions: object) -> None:
        if "restart" in actions.pressed:
            self.reset()
            self._sync_scene()
            return
        if "ghost" in actions.pressed:
            self.show_ghost = not self.show_ghost
            self._sync_scene()
            return
        if self.state == "ready" and "course" in actions.pressed:
            self.course = COURSES[(COURSES.index(self.course) + 1) % len(COURSES)]
            self._sync_scene()
            return
        if self.state == "ready" and "start" in actions.pressed:
            self.state = "racing"
            return
        if self.state in ("finished", "failed") and "start" in actions.pressed:
            # A time trial is a retry loop: restart the same course in one key
            # while keeping the session record and the selected layout.
            self.reset()
            self.state = "racing"
            self._sync_scene()
            return
        if self.state != "racing":
            if self.confetti is not None:
                life = self.confetti - dt * CONFETTI_DECAY
                self.confetti = life if life > 0 else None
                self._sync_scene()
            return
        if not self.current_trace or self.elapsed - self.current_trace[-1][0] >= 0.05:
            self.current_trace.append((self.elapsed, self.x, self.distance))
        # A frame may extend past the deadline. Never move the car through the
        # remainder of that frame after time has expired.
        requested_dt = max(0.0, dt)
        dt = min(requested_dt, max(0.0, self.remaining))
        self.message_time = max(0.0, self.message_time - dt)
        if not self.message_time:
            self.message = ""
        if self.burst is not None:
            life = self.burst[1] - dt * 2.0
            self.burst = (self.burst[0], life) if life > 0 else None
        self.elapsed += dt
        throttle = max(-1.0, min(1.0, actions.forward + float("arrow_up" in actions.held)
                                  - float("arrow_down" in actions.held)))
        boosting = "sprint" in actions.held and throttle > 0 and self.boost > 0
        boost_time = min(dt, self.boost) if boosting else 0.0
        if boosting:
            self.boost -= boost_time
        elif "sprint" not in actions.held:
            self.boost = min(3.0, self.boost + dt * 0.25)
        acceleration = (8.0 * throttle + 1.0 - 0.12 * self.speed) * dt + 7.0 * boost_time
        speed_limit = 30.0 if boosting else max(24.0, self.speed - 4.0 * dt)
        self.speed = max(0.0, min(speed_limit, self.speed + acceleration))
        self.steering = max(-1.0, min(1.0, actions.right + float("arrow_right" in actions.held)
                                      - float("arrow_left" in actions.held)))
        previous_x = self.x
        self.x = max(-3.8, min(3.8, self.x + self.steering * min(5.0, 1.5 + self.speed * 0.2) * dt))
        previous = self.distance
        projected = self.distance + self.speed * dt
        self.distance = min(FINISH, projected)
        self.boosting = boosting
        self.skids = [(x, distance, side, life - dt * 1.2)
                      for x, distance, side, life in self.skids if life - dt * 1.2 > 0]
        self.braking = throttle < 0 and self.speed > BRAKE_LIGHT_SPEED
        braking = self.braking
        drifting = abs(self.steering) >= DRIFT_STEER and self.speed > DRIFT_SPEED
        if braking or drifting:
            self.skids.append((self.x - 0.63, self.distance, -0.63, 1.0))
            self.skids.append((self.x + 0.63, self.distance, 0.63, 1.0))
            if len(self.skids) > SKID_LENGTH:
                self.skids = self.skids[-SKID_LENGTH:]
        self.trail = [(x, distance, life - dt * 1.5)
                      for x, distance, life in self.trail if life - dt * 1.5 > 0]
        if boosting:
            self.trail.append((self.x, self.distance, 1.0))
            if len(self.trail) > TRAIL_LENGTH:
                self.trail = self.trail[-TRAIL_LENGTH:]
        # Resolve crossings in course order so a checkpoint cannot revive a
        # car after a fatal impact, or be skipped when reached before one.
        crossings = []
        travel = projected - previous
        for index, (distance, x) in enumerate(self.course_rocks):
            if index not in self.hit_indices and previous < distance <= self.distance:
                crossing_x = previous_x + (self.x - previous_x) * ((distance - previous) / travel)
                gap = abs(crossing_x - x)
                if gap < HIT_GAP:
                    crossings.append((distance, 0, index))
                elif index not in self.near_indices and gap < NEAR_MISS_GAP:
                    crossings.append((distance, 3, index))
        for number in range(self.checkpoint + 1, 4):
            distance = number * 100.0
            if previous < distance <= self.distance:
                crossings.append((distance, 1, number))
        if self.pickup_station < len(PICKUP_STATIONS):
            station = PICKUP_STATIONS[self.pickup_station]
            if previous < station <= self.distance:
                crossing_x = previous_x + (self.x - previous_x) * ((station - previous) / travel)
                if abs(crossing_x - PICKUP_X) < 1.2:
                    crossings.append((station, 4, 0))
        if previous < FINISH <= self.distance:
            crossings.append((FINISH, 2, 0))
        spent = 0.0
        for distance, kind, index in sorted(crossings):
            event_time = dt * (distance - previous) / travel
            interval = event_time - spent
            if self.remaining <= interval:
                stop_time = spent + self.remaining
                self.distance = previous + travel * (stop_time / dt) if dt else previous
                self.x = previous_x + (self.x - previous_x) * (stop_time / dt) if dt else previous_x
                self.elapsed -= dt - stop_time
                self.remaining = 0.0
                self.state = "failed"
                self._sync_scene()
                return
            self.remaining -= interval
            spent = event_time
            if kind == 0:
                self.hit_indices.add(index)
                self.hits += 1
                rock_x = self.course_rocks[index][1]
                hit_x = previous_x + (self.x - previous_x) * ((distance - previous) / travel) if travel else previous_x
                self.collision_side = "RIGHT" if hit_x >= rock_x else "LEFT"
                self.near_streak = 0
                self.speed *= 0.4
                self.remaining -= 2.0
                self.collision_penalty += 2.0
                self.message = "COLLISION -2 SEC"
                self.message_time = 2.0
                if self.remaining <= 0:
                    self.distance = distance
                    self.x = previous_x + (self.x - previous_x) * (spent / dt) if dt else previous_x
                    self.elapsed -= dt - spent
                    self.remaining = 0.0
                    self.state = "failed"
                    self._sync_scene()
                    return
            elif kind == 1:
                self.remaining += CHECKPOINT_BONUS
                self.checkpoint_bonus += CHECKPOINT_BONUS
                self.checkpoint = index
                self.burst = (index, 1.0)
                # The crossing can happen part-way through the frame; compare
                # split times at the crossing, not at the end of the frame.
                split = self.elapsed - dt + event_time
                self.current_splits[index] = split
                reference = self.best_splits[self.course].get(index)
                self.message = f"CHECKPOINT +{CHECKPOINT_BONUS:.0f} SEC"
                if reference is not None:
                    delta = split - reference
                    sign = "+" if delta >= 0 else "-"
                    self.message = f"CHECKPOINT +{CHECKPOINT_BONUS:.0f} SEC  {sign}{abs(delta):.1f}s"
                self.message_time = 2.0
            elif kind == 3:
                self.near_indices.add(index)
                self.near_misses += 1
                self.near_streak += 1
                self.best_near_streak = max(self.best_near_streak, self.near_streak)
                self.message = ("NEAR MISS" if self.near_streak == 1
                                else f"{self.near_streak}x NEAR MISS STREAK")
                self.message_time = 1.2
            elif kind == 4:
                self.pickup_collected = True
                self.pickups_collected += 1
                self.pickup_station += 1
                self.boost = 3.0
                self.message = "BOOST REFILLED"
                self.message_time = 1.5
            else:
                self.elapsed -= dt - spent
                self.x = previous_x + (self.x - previous_x) * (spent / dt) if dt else previous_x
                self._finish()
                return
        self.remaining -= dt - spent
        if self.remaining <= 0:
            self.remaining = 0.0
            self.state = "failed"
            self._sync_scene()
        elif self.distance >= FINISH:
            self._finish()
        else:
            self._sync_scene()
        if self.state == "racing" and requested_dt > dt:
            # A checkpoint extended the deadline during this frame. Consume the
            # remaining time with held input, without repeating button edges.
            self.update(requested_dt - dt, actions.without_pressed())

    def achievements(self) -> list[tuple[str, bool]]:
        """Milestones derived from already-tracked per-course records."""
        finishes = sum(self.lifetime_totals[course]["finishes"] for course in COURSES)
        golds = sum(self.lifetime_totals[course]["golds"] for course in COURSES)
        streak = max(self.best_streak_bests.values(), default=0)
        return [
            ("FIRST FINISH", finishes >= 1),
            ("GOLD MEDAL", golds >= 1),
            ("ALL COURSES", all(self.best_times[course] is not None for course in COURSES)),
            ("NEAR MISS PRO", streak >= 3),
        ]

    def trophy_count(self) -> int:
        return sum(earned for _, earned in self.achievements())

    def next_grade_target(self) -> str:
        """What is needed for the next better medal, or '' before a finish."""
        if self.state != "finished":
            return ""
        grade = self.medal()
        if grade == "GOLD":
            return "BEST POSSIBLE"
        if grade == "SILVER":
            return f"NEXT GRADE: UNDER {GOLD_TIME:.0f}s AND {GOLD_HITS} HITS"
        return f"NEXT GRADE: UNDER {SILVER_TIME:.0f}s AND {SILVER_HITS} HITS"

    def low_time(self) -> bool:
        """True when a live race is within the low-time warning threshold."""
        return self.state == "racing" and self.remaining <= LOW_TIME

    def high_speed(self) -> bool:
        """True when a live race is in the high-speed warning band."""
        return self.state == "racing" and self.speed > HIGH_SPEED

    def low_boost(self) -> bool:
        """True when a live race has a nearly depleted boost charge."""
        return self.state == "racing" and self.boost < LOW_BOOST

    def medal(self) -> str:
        """Grade completed runs; unfinished runs do not receive a medal."""
        if self.state != "finished":
            return ""
        if self.elapsed < GOLD_TIME and self.hits <= GOLD_HITS:
            return "GOLD"
        if self.elapsed < SILVER_TIME and self.hits <= SILVER_HITS:
            return "SILVER"
        return "BRONZE"

    def next_marker(self) -> float:
        """Distance remaining to the next checkpoint, or to the finish line."""
        for number in range(self.checkpoint + 1, 4):
            marker = number * 100.0
            if marker > self.distance:
                return marker - self.distance
        return max(0.0, FINISH - self.distance)

    def split_summary(self) -> list[str]:
        """One label per recorded checkpoint, with a signed delta when a best exists."""
        lines = []
        for number in sorted(self.current_splits):
            split = self.current_splits[number]
            label = f"CP{number} {split:.1f}s"
            reference = self.best_splits[self.course].get(number)
            if reference is not None:
                delta = split - reference
                sign = "+" if delta >= 0 else "-"
                label += f"  {sign}{abs(delta):.1f}s VS BEST"
            lines.append(label)
        return lines

    def steering_hint(self) -> str:
        """A lane hint for the next nearby boulder, or '' when none is close."""
        upcoming = next(((distance, x) for distance, x in self.course_rocks
                         if distance > self.distance), None)
        if upcoming is None or upcoming[0] - self.distance > 25:
            return ""
        lanes = (-3.6, 0.0, 3.6)
        safe = [lane for lane in lanes if abs(lane - upcoming[1]) > 1.5]
        if not safe:
            return ""
        target = min(safe, key=lambda lane: abs(lane - self.x))
        if target - self.x > 0.5:
            return "RIGHT"
        if target - self.x < -0.5:
            return "LEFT"
        return "CENTER"

    @property
    def speed_lit_material(self) -> Material:
        return SPEED_BAR_LIT

    def lit_speed_bars(self) -> int:
        return min(SPEED_BARS, int(self.speed / SPEED_BAR_MAX * SPEED_BARS))

    def ghost_distance(self) -> float | None:
        """Best-run distance at the current elapsed time, or None if no trace."""
        trace = self.best_traces[self.course]
        if not trace:
            return None
        for index in range(1, len(trace)):
            before, after = trace[index - 1], trace[index]
            if before[0] <= self.elapsed <= after[0]:
                span = after[0] - before[0]
                fraction = (self.elapsed - before[0]) / span if span else 1.0
                return before[2] + (after[2] - before[2]) * fraction
        return trace[-1][2]

    def boulder_proximity(self) -> bool:
        """True when the next boulder is close ahead and the car's gap is in the near-miss band."""
        upcoming = next(((distance, x) for distance, x in self.course_rocks
                         if distance > self.distance), None)
        if upcoming is None or upcoming[0] - self.distance > PROXIMITY_DISTANCE:
            return False
        return abs(self.x - upcoming[1]) < NEAR_MISS_GAP

    def minimap_rows(self) -> list[str]:
        """Render the next MINIMAP_DEPTH metres as rows of lane characters."""
        rows = [[" " for _ in range(5)] for _ in range(MINIMAP_ROWS)]
        step = MINIMAP_DEPTH / MINIMAP_ROWS

        def lane_index(x: float) -> int:
            return max(0, min(4, int((x + 3.8) / 7.6 * 5)))

        def row_index(distance: float) -> int | None:
            offset = distance - self.distance
            if 0 <= offset < MINIMAP_DEPTH:
                return min(MINIMAP_ROWS - 1, int(offset / step))
            return None

        for rock_distance, rock_x in self.course_rocks:
            index = row_index(rock_distance)
            if index is not None:
                rows[index][lane_index(rock_x)] = "X"
        for number in range(self.checkpoint + 1, 4):
            index = row_index(number * 100.0)
            if index is not None:
                rows[index][2] = "="
        if self.pickup_station < len(PICKUP_STATIONS):
            index = row_index(PICKUP_STATIONS[self.pickup_station])
            if index is not None:
                rows[index][lane_index(PICKUP_X)] = "P"
        ghost_distance = self.ghost_distance()
        if ghost_distance is not None:
            index = row_index(ghost_distance)
            if index is not None:
                rows[index][2] = "G"
        rows[0][lane_index(self.x)] = "C"
        return ["|" + "".join(row) + "|" for row in rows]

    def checkpoints_remaining(self) -> int:
        return max(0, 3 - self.checkpoint)

    def pickups_remaining(self) -> int:
        return max(0, len(PICKUP_STATIONS) - self.pickups_collected)

    def time_bar(self, width: int = 20) -> str:
        filled = max(0, min(width, round(self.remaining / START_TIME * width)))
        return "[" + "#" * filled + " " * (width - filled) + "]"

    def progress_bar(self, width: int = 20) -> str:
        cells = ["-"] * width
        for number in (1, 2, 3):
            cells[int(number * 100 / FINISH * width)] = "|"
        for index in range(min(int(self.distance / FINISH * width), width)):
            cells[index] = "#"
        return "[" + "".join(cells) + "]"

    def snapshot(self) -> dict[str, object]:
        return {"state": self.state, "course": self.course, "distance": round(self.distance, 3), "speed": round(self.speed, 3),
                "x": round(self.x, 3), "time": round(self.elapsed, 3), "remaining": round(self.remaining, 3),
                "checkpoint": self.checkpoint, "hits": self.hits, "near_misses": self.near_misses,
                "near_streak": self.near_streak, "best_near_streak": self.best_near_streak,
                "pickup_collected": self.pickup_collected, "show_ghost": self.show_ghost,
                "collision_side": self.collision_side,
                "pickups_collected": self.pickups_collected, "pickup_station": self.pickup_station,
                "checkpoint_bonus": self.checkpoint_bonus, "collision_penalty": self.collision_penalty,
                "message": self.message,
                "boost": round(self.boost, 3), "steering": round(self.steering, 3), "medal": self.medal(),
                "best_time": round(self.best_time, 3) if self.best_time is not None else None,
                "finish_delta": round(self.finish_delta, 3) if self.finish_delta is not None else None}

    def status(self) -> str:
        return f"{self.state} | {self.distance:.0f}/400m | {self.remaining:.1f}s"

    def draw_ui(self, canvas: object, state: object) -> None:
        center = int(state.width) // 2
        def label(y: int, text: str, scale: int = 2, colour: tuple = (0.95, 0.96, 1.0, 1.0)) -> None:
            canvas.text(center - text_width(text, scale) // 2, y, text, colour, scale)
        warning = self.low_time()
        fast = self.high_speed()
        label(15, f"TIME {self.remaining:.1f}   SPEED {self.speed:.0f}   "
              f"{self.time_bar()}",
              colour=(1.0, 0.35, 0.2, 1.0) if (warning or fast) else (0.95, 0.96, 1.0, 1.0))
        if warning:
            label(88, "TIME LOW", 2, (1.0, 0.35, 0.2, 1.0))
        if fast:
            label(100, "TOO FAST", 2, (1.0, 0.6, 0.2, 1.0))
        marker = (f"FINISH {self.next_marker():.0f} M" if self.checkpoint >= 3
                  else f"{self.next_marker():.0f} M")
        label(40, f"{self.distance:.0f} / 400 M   CHECKPOINTS {self.checkpoints_remaining()} LEFT   "
              f"BOOST {self.boost:.1f}S   NEXT {marker}  {self.progress_bar()}", 1)
        if self.state == "racing" and self.message:
            label(70, self.message, 2)
            if self.message == "COLLISION -2 SEC" and self.collision_side:
                label(84, f"HIT {self.collision_side} SIDE", 1, (1.0, 0.55, 0.3, 1.0))
        if self.state == "racing":
            delta = self.pace_delta()
            if delta is not None:
                sign = "+" if delta >= 0 else "-"
                label(58, f"PACE {sign}{abs(delta):.1f}s VS BEST", 1)
            if self.low_boost():
                label(112, "BOOST LOW", 2, (1.0, 0.6, 0.2, 1.0))
            hint = self.steering_hint()
            if hint:
                label(124, f"STEER {hint}", 1, (0.7, 0.95, 1.0, 1.0))
            if self.boulder_proximity():
                label(136, "TOO CLOSE", 1, (1.0, 0.4, 0.3, 1.0))
            if self.pickups_remaining():
                label(148, f"{self.pickups_remaining()} PICKUPS LEFT", 1, (1.0, 0.9, 0.3, 1.0))
            right = int(state.width) - 12
            canvas.text(right - text_width("COURSE AHEAD", 1), 15, "COURSE AHEAD",
                        (0.7, 0.85, 1.0, 1.0), 1)
            for index, row in enumerate(self.minimap_rows()):
                canvas.text(right - text_width(row, 1), 30 + index * 12, row,
                            (0.7, 0.85, 1.0, 1.0), 1)
        label(int(state.height) - 85, "WASD OR ARROWS DRIVE  SHIFT BOOST  G GHOST  P PAUSE  R RESTART", 1)
        if self.state == "ready":
            label(int(state.height) // 2 - 30, "BEACONFALL", 4)
            label(int(state.height) // 2 + 20, "PRESS SPACE TO START", 2)
            label(int(state.height) // 2 + 40,
                  f"{START_TIME:.0f} START  +{CHECKPOINT_BONUS:.0f} PER CHECKPOINT  4 GATES", 1)
            label(int(state.height) // 2 + 80, f"COURSE {self.course.upper()}  -  F TO CHANGE", 1)
            if self.best_time is not None:
                label(int(state.height) // 2 + 50, f"{self.record_label} {self.best_time:.1f} SEC", 2)
            for offset, course in enumerate(COURSES):
                best = self.best_times[course]
                value = f"{best:.1f} SEC" if best is not None else "--"
                if self.best_nears[course]:
                    value += f"  {self.best_nears[course]} NM"
                if self.best_streak_bests[course]:
                    value += f"  {self.best_streak_bests[course]}x"
                if self.best_medals[course]:
                    value += f"  {self.best_medals[course][0]}"
                if self.clean_finishes[course]:
                    value += f"  {self.clean_finishes[course]}CL"
                pointer = ">" if course == self.course else " "
                label(int(state.height) // 2 + 110 + offset * 18,
                      f"{pointer} {course.upper():<8} {value}", 1)
            totals = self.lifetime_totals[self.course]
            label(int(state.height) // 2 + 165,
                  f"LIFETIME {totals['finishes']} FINISHES  {totals['golds']} GOLDS", 1)
            last = self.last_sessions[self.course]
            if last:
                label(int(state.height) // 2 + 185,
                      f"LAST {last['medal']} {last['time']:.1f}s  {last['hits']} HITS  "
                      f"{last['near_misses']} NM  {last['streak']}x STREAK", 1)
            label(int(state.height) // 2 + 203,
                  f"TROPHIES {self.trophy_count()}/{len(self.achievements())}", 1)
            total_km = sum(self.lifetime_distance.values()) / 1000.0
            label(int(state.height) // 2 + 219, f"LIFETIME DISTANCE {total_km:.1f} KM", 1)
        elif self.state != "racing":
            label(int(state.height) // 2, "FINISH!" if self.state == "finished" else "TIME UP", 4)
            label(int(state.height) // 2 + 45, f"{self.elapsed:.1f} SEC  {self.hits} HITS  {self.near_misses} NEAR MISSES  -  SPACE RETRY  R MENU", 2)
            if self.state == "finished":
                if self.new_best:
                    label(int(state.height) // 2 - 45, "NEW RECORD", 3, (1.0, 0.85, 0.25, 1.0))
                banner = "  NEW BEST!" if self.new_best else ""
                label(int(state.height) // 2 + 75, f"{self.medal()} MEDAL{banner}", 2)
                label(int(state.height) // 2 + 100, f"{self.record_label} {self.best_time:.1f} SEC", 2)
                if self.finish_delta is not None:
                    direction = "FASTER" if self.finish_delta < 0 else "SLOWER"
                    label(int(state.height) // 2 + 125,
                          f"{abs(self.finish_delta):.1f} SEC {direction} THAN BEST", 1)
                label(int(state.height) // 2 + 145,
                      f"BONUS +{self.checkpoint_bonus:.0f}s  PENALTY -{self.collision_penalty:.0f}s", 1)
                target = self.next_grade_target()
                if target and target != "BEST POSSIBLE":
                    label(int(state.height) // 2 + 158, target, 1, (1.0, 0.85, 0.3, 1.0))
                for offset, line in enumerate(self.split_summary()):
                    label(int(state.height) // 2 + 176 + offset * 16, line, 1)


Game = Race
