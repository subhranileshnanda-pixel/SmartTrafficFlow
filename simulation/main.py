import random
import pygame
from config import *
from draw import draw_roads, draw_signals, draw_density, draw_info
from vehicle import try_spawn, spawn_emergency
from density import measure_all
from api_client import BackendClient, RemoteSignals

EMERGENCY_KEYS = {
    pygame.K_a: "ambulance",
    pygame.K_f: "firetruck",
    pygame.K_p: "police",
}

INTENSITY_KEYS = {
    pygame.K_1: ("LOW", (2.0, 3.5)),
    pygame.K_2: ("MEDIUM", (0.8, 1.8)),
    pygame.K_3: ("HIGH", (0.25, 0.6)),
}
ARROW_ROADS = {
    pygame.K_UP: "NORTH",
    pygame.K_RIGHT: "EAST",
    pygame.K_DOWN: "SOUTH",
    pygame.K_LEFT: "WEST",
}

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SmartFlow | Traffic: MEDIUM | A/F/P = Emergency | 1/2/3 = Intensity")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 20, bold=True)
small_font = pygame.font.SysFont("arial", 15, bold=True)

client = BackendClient()
controller = RemoteSignals(client)
vehicles = {road: [] for road in SIGNAL_ORDER}
densities = measure_all(vehicles)
spawn_timer = 0
intensity_name, spawn_range = "MEDIUM", (0.8, 1.8)
road_bias = {road: 1 for road in SIGNAL_ORDER}


def spawn_emergency_anywhere(kind):                      # CHANGED: one function for keys AND dashboard
    """Spawns an emergency vehicle on the first road with free space, then asks for priority."""
    roads = SIGNAL_ORDER[:]
    random.shuffle(roads)
    for road in roads:
        v = spawn_emergency(vehicles[road], road, kind)
        if v:
            print(f"{v.kind.upper()} spawned on {road}")
            client.send_emergency(road, v.kind)
            return True
    print("All four roads are full right now, try again")
    return False


running = True
while running:
    dt = clock.tick(FPS) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN and event.key in EMERGENCY_KEYS:
            spawn_emergency_anywhere(EMERGENCY_KEYS[event.key])      # CHANGED

        elif event.type == pygame.KEYDOWN and event.key in INTENSITY_KEYS:
            intensity_name, spawn_range = INTENSITY_KEYS[event.key]
            print(f"Traffic intensity: {intensity_name}")
            pygame.display.set_caption(
                f"SmartFlow | Traffic: {intensity_name} | A/F/P = Emergency | 1/2/3 = Intensity")

        elif event.type == pygame.KEYDOWN and event.key in ARROW_ROADS:
            r = ARROW_ROADS[event.key]
            road_bias[r] = 1 if road_bias[r] > 1 else 6
            print(f"{r} is now {'EXTRA BUSY' if road_bias[r] > 1 else 'normal'}")

    # CHANGED: commands sent from the dashboard
    for cmd in client.pop_commands():
        if cmd.get("type") == "spawn_emergency":
            print(f"Dashboard command: send {cmd['kind']}")
            spawn_emergency_anywhere(cmd["kind"])

    emergency_roads = {
        road for road, lane in vehicles.items()
        if any(v.is_emergency and v.before_stop_line() for v in lane)
    }

    # 1. Send our data to the backend; signal decisions come back from it
    client.set_snapshot(densities, emergency_roads)

    # SAFETY CHECK: at most one road may be non-red at any moment
    active = [r for r in SIGNAL_ORDER if controller.get_state(r) != "RED"]
    assert len(active) <= 1, f"SAFETY VIOLATION: conflicting signals {active}"

    # 2. Spawn normal vehicles
    spawn_timer -= dt
    if spawn_timer <= 0:
        road = random.choices(SIGNAL_ORDER, weights=[road_bias[r] for r in SIGNAL_ORDER])[0]
        try_spawn(vehicles[road], road)
        spawn_timer = random.uniform(*spawn_range)

    # 3. Move vehicles
    for road, lane in vehicles.items():
        lane.sort(key=lambda v: v.progress(), reverse=True)
        state = controller.get_state(road)
        for i, v in enumerate(lane):
            ahead = lane[i - 1] if i > 0 else None
            v.update(state, ahead, dt)
        lane[:] = [v for v in lane if not v.is_off_screen()]

    # 3b. Measure density
    densities = measure_all(vehicles)

    # 4. Draw
    draw_roads(screen)
    for lane in vehicles.values():
        for v in lane:
            v.draw(screen)
    draw_signals(screen, controller, font)
    draw_density(screen, densities, small_font)
    draw_info(screen, controller, font)
    if not client.is_online():
        warn = font.render("BACKEND OFFLINE - all signals red", True, (255, 200, 0))
        screen.blit(warn, (10, 66))
    pygame.display.flip()

pygame.quit()