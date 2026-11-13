import random
import pygame
from config import *

# Speed is in pixels per second
VEHICLE_TYPES = {
    "car":   {"length": 40, "width": 22, "speed": 150, "weight": 55},
    "bike":  {"length": 24, "width": 12, "speed": 180, "weight": 20},
    "bus":   {"length": 70, "width": 26, "speed": 120, "weight": 15},
    "truck": {"length": 60, "width": 26, "speed": 110, "weight": 10},
}
KIND_COLORS = {
    "car": [(200, 40, 40), (40, 90, 200), (230, 230, 230), (30, 30, 30)],
    "bike": [(150, 80, 220)],
    "bus": [(240, 140, 30)],
    "truck": [(120, 90, 60)],
}

# Emergency vehicles are NOT in VEHICLE_TYPES, so they never spawn randomly.
EMERGENCY_TYPES = {
    "ambulance": {"length": 48, "width": 24, "speed": 170, "color": (245, 245, 245)},
    "firetruck": {"length": 72, "width": 26, "speed": 140, "color": (200, 30, 30)},
    "police":    {"length": 42, "width": 22, "speed": 190, "color": (40, 70, 170)},
}

MIN_GAP = 12   # smallest allowed space between two vehicles

STOP_PROGRESS = {
    "NORTH": STOP_LINE["NORTH"],
    "SOUTH": -STOP_LINE["SOUTH"],
    "WEST": STOP_LINE["WEST"],
    "EAST": -STOP_LINE["EAST"],
}


class Vehicle:
    def __init__(self, road, kind):
        info = ROAD_INFO[road]
        spec = VEHICLE_TYPES.get(kind) or EMERGENCY_TYPES[kind]
        self.road = road
        self.kind = kind
        self.is_emergency = kind in EMERGENCY_TYPES
        self.dx, self.dy = info["dx"], info["dy"]
        self.x, self.y = info["x"], info["y"]
        self.length = spec["length"]
        self.width = spec["width"]
        self.speed = spec["speed"]
        if self.is_emergency:
            self.color = spec["color"]
        else:
            self.color = random.choice(KIND_COLORS[kind])

    def progress(self):
        """How far along its direction of travel the vehicle is (bigger = further ahead)."""
        return self.x * self.dx + self.y * self.dy

    def before_stop_line(self):
        """True while the front of the vehicle has not yet crossed the stop line."""
        front = self.progress() + self.length / 2
        return STOP_PROGRESS[self.road] - front >= -1

    def update(self, signal_state, ahead, dt):
        step = self.speed * dt

        # Rule 1: stop at the stop line if the signal is not green
        front = self.progress() + self.length / 2
        if signal_state != "GREEN":
            dist = STOP_PROGRESS[self.road] - front
            if dist >= -1:
                step = min(step, max(dist, 0))

        # Rule 2: keep a gap from the vehicle in front
        if ahead is not None:
            gap = (ahead.progress() - ahead.length / 2) - front
            step = min(step, max(gap - MIN_GAP, 0))

        self.x += self.dx * step
        self.y += self.dy * step

    def is_off_screen(self):
        return self.x < -100 or self.x > WIDTH + 100 or self.y < -100 or self.y > HEIGHT + 100

    def draw(self, screen):
        if self.dx != 0:
            w, h = self.length, self.width
        else:
            w, h = self.width, self.length
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (self.x, self.y)
        pygame.draw.rect(screen, self.color, rect, border_radius=5)

        if self.is_emergency:
            # Flashing light: switches between red and blue every 0.2 seconds
            flash = (pygame.time.get_ticks() // 200) % 2
            light = (255, 0, 0) if flash else (0, 120, 255)
            pygame.draw.rect(screen, BLACK, rect, 2, border_radius=5)
            pygame.draw.circle(screen, light, rect.center, 7)


def try_spawn(lane, road):
    """Add a new normal vehicle to this road, unless there's no room at the entrance."""
    kinds = list(VEHICLE_TYPES)
    weights = [VEHICLE_TYPES[k]["weight"] for k in kinds]
    new = Vehicle(road, random.choices(kinds, weights=weights)[0])

    for v in lane:
        if abs(v.progress() - new.progress()) < 110:
            return
    lane.append(new)


def spawn_emergency(lane, road, kind):
    """Add an emergency vehicle. Returns the vehicle, or None if the entrance is blocked."""
    new = Vehicle(road, kind)
    for v in lane:
        needed = (new.length + v.length) / 2 + MIN_GAP
        if abs(v.progress() - new.progress()) < needed:
            return None
    lane.append(new)
    return new