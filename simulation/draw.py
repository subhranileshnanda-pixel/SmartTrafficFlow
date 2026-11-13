import math
import pygame
from config import *


def draw_roads(screen):
    screen.fill(GRASS)

    # The two roads
    pygame.draw.rect(screen, ROAD, (CX - HALF_ROAD, 0, ROAD_WIDTH, HEIGHT))
    pygame.draw.rect(screen, ROAD, (0, CY - HALF_ROAD, WIDTH, ROAD_WIDTH))

    # Dashed centre lines (skipped inside the junction box)
    for p in range(0, HEIGHT, 30):
        if p + 15 < CY - HALF_ROAD or p > CY + HALF_ROAD:
            pygame.draw.line(screen, LINE_YELLOW, (CX, p), (CX, p + 15), 2)
    for p in range(0, WIDTH, 30):
        if p + 15 < CX - HALF_ROAD or p > CX + HALF_ROAD:
            pygame.draw.line(screen, LINE_YELLOW, (p, CY), (p + 15, CY), 2)

    # Stop lines (only across the incoming lane of each road)
    pygame.draw.line(screen, WHITE, (CX, STOP_LINE["NORTH"]), (CX + LANE_WIDTH, STOP_LINE["NORTH"]), 4)
    pygame.draw.line(screen, WHITE, (CX - LANE_WIDTH, STOP_LINE["SOUTH"]), (CX, STOP_LINE["SOUTH"]), 4)
    pygame.draw.line(screen, WHITE, (STOP_LINE["WEST"], CY - LANE_WIDTH), (STOP_LINE["WEST"], CY), 4)
    pygame.draw.line(screen, WHITE, (STOP_LINE["EAST"], CY), (STOP_LINE["EAST"], CY + LANE_WIDTH), 4)


SIGNAL_POS = {
    "NORTH": (CX + HALF_ROAD + 20, STOP_LINE["NORTH"]),
    "SOUTH": (CX - HALF_ROAD - 20, STOP_LINE["SOUTH"]),
    "WEST": (STOP_LINE["WEST"], CY - HALF_ROAD - 20),
    "EAST": (STOP_LINE["EAST"], CY + HALF_ROAD + 20),
}
LABEL_OFFSET = {"NORTH": (45, 0), "SOUTH": (-45, 0), "WEST": (0, -28), "EAST": (0, 28)}
STATE_COLOR = {"RED": RED, "YELLOW": YELLOW, "GREEN": GREEN}


def draw_signals(screen, controller, font):
    for road, pos in SIGNAL_POS.items():
        state = controller.get_state(road)
        pygame.draw.circle(screen, BLACK, pos, 16)
        pygame.draw.circle(screen, STATE_COLOR[state], pos, 12)

        text = road[0]  # N, E, S or W
        if road == controller.current_road() and controller.phase != "ALL_RED":
            if controller.emergency_mode:
                text += " EMG"
            else:
                text += f" {math.ceil(controller.timer)}"   # countdown
        label = font.render(text, True, WHITE)
        offset = LABEL_OFFSET[road]
        rect = label.get_rect(center=(pos[0] + offset[0], pos[1] + offset[1]))
        screen.blit(label, rect)


LEVEL_COLOR = {"LOW": (80, 200, 100), "MEDIUM": (240, 190, 40), "HIGH": (230, 70, 60)}
PANEL_POS = {
    "NORTH": (CX + 130, 20),
    "EAST": (WIDTH - 190, CY + 130),
    "SOUTH": (CX - 320, HEIGHT - 80),
    "WEST": (20, CY - 200),
}


def draw_density(screen, densities, font):
    for road, info in densities.items():
        x, y = PANEL_POS[road]
        box = pygame.Rect(x, y, 170, 60)
        pygame.draw.rect(screen, (30, 30, 30), box, border_radius=6)
        pygame.draw.rect(screen, LEVEL_COLOR[info["level"]], box, 3, border_radius=6)

        line1 = font.render(f"{road}: {info['level']}", True, LEVEL_COLOR[info["level"]])
        line2 = font.render(f"Vehicles: {info['count']}  Score: {info['score']}", True, WHITE)
        screen.blit(line1, (x + 8, y + 6))
        screen.blit(line2, (x + 8, y + 32))


def draw_info(screen, controller, font):
    text = f"{controller.current_road()}: {controller.phase}  |  green time: {controller.green_time:.0f}s"
    label = font.render(text, True, WHITE)
    screen.blit(label, (10, 10))

    if controller.emergency_mode:
        msg = f"EMERGENCY PRIORITY: {controller.current_road()}"
    elif controller.emergency_queue:
        msg = f"EMERGENCY ON {controller.emergency_queue[0]} - clearing junction..."
    else:
        return
    warn = font.render(msg, True, (255, 90, 90))
    screen.blit(warn, (10, 38))