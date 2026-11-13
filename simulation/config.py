# ---------- Window ----------
WIDTH, HEIGHT = 800, 800
FPS = 60
CX, CY = WIDTH // 2, HEIGHT // 2      # centre of the intersection

# ---------- Road geometry ----------
ROAD_WIDTH = 100
HALF_ROAD = ROAD_WIDTH // 2
LANE_WIDTH = ROAD_WIDTH // 2           # one incoming lane + one outgoing lane
STOP_GAP = 15                          # stop line distance from the junction box

# ---------- Colours ----------
GRASS = (60, 140, 60)
ROAD = (60, 60, 60)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LINE_YELLOW = (240, 200, 0)
RED = (220, 40, 40)
YELLOW = (240, 200, 0)
GREEN = (40, 200, 70)

# ---------- Signal timing (seconds) ----------
GREEN_TIME = 10
YELLOW_TIME = 3
ALL_RED_TIME = 2

# The order in which roads get their turn
SIGNAL_ORDER = ["NORTH", "EAST", "SOUTH", "WEST"]

# Position of each road's stop line
STOP_LINE = {
    "NORTH": CY - HALF_ROAD - STOP_GAP,
    "SOUTH": CY + HALF_ROAD + STOP_GAP,
    "WEST": CX - HALF_ROAD - STOP_GAP,
    "EAST": CX + HALF_ROAD + STOP_GAP,
}

# Direction of travel (dx, dy) and where vehicles appear.
ROAD_INFO = {
    "NORTH": {"dx": 0, "dy": 1,  "x": CX + LANE_WIDTH // 2, "y": -60},
    "SOUTH": {"dx": 0, "dy": -1, "x": CX - LANE_WIDTH // 2, "y": HEIGHT + 60},
    "WEST":  {"dx": 1, "dy": 0,  "x": -60, "y": CY - LANE_WIDTH // 2},
    "EAST":  {"dx": -1, "dy": 0, "x": WIDTH + 60, "y": CY + LANE_WIDTH // 2},
}

# ---------- Traffic density ----------
DETECTION_ZONE = 300        # how many pixels before the stop line we look at
DENSITY_LOW_MAX = 3         # score <= 3  -> LOW
DENSITY_MEDIUM_MAX = 7      # score <= 7  -> MEDIUM, above -> HIGH

VEHICLE_WEIGHT = {"bike": 0.5, "car": 1, "truck": 2, "bus": 2,
                  "ambulance": 1, "firetruck": 2, "police": 1}

# ---------- Adaptive signal timing ----------
MIN_GREEN = 8               # seconds
MAX_GREEN = 25              # seconds
SECONDS_PER_SCORE = 1.5     # extra green seconds per density point

# ---------- Emergency priority ----------
EMERGENCY_CLEAR_TIME = 3    # seconds of green kept after the emergency vehicle crosses the line
EMERGENCY_MAX_HOLD = 20     # safety limit: never hold an emergency green longer than this