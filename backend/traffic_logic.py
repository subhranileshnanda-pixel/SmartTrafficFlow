from forecast import Forecaster

# ---------- Timing (seconds) ----------
YELLOW_TIME = 3
ALL_RED_TIME = 2
MIN_GREEN = 6                    # CHANGED (was 8)
MAX_GREEN = 20                   # CHANGED (was 25)
SECONDS_PER_SCORE = 0.8          # CHANGED (was 1.5)
EMERGENCY_CLEAR_TIME = 3
EMERGENCY_MAX_HOLD = 20
FIXED_GREEN = 10                 # CHANGED: the baseline uses the best fixed timer we measured

GAP_MIN_GREEN = 5                # NEW: a green always lasts at least this long before it can end early
GAP_EMPTY_TIME = 1.0             # NEW: road must have been empty this long before the green ends early

SIGNAL_ORDER = ["NORTH", "EAST", "SOUTH", "WEST"]
MODES = ("fixed", "adaptive", "predictive")
DEFAULT_MODE = "adaptive"


def calculate_green_time(score):
    """More traffic = longer green, but always between MIN_GREEN and MAX_GREEN."""
    green = MIN_GREEN + score * SECONDS_PER_SCORE
    return max(MIN_GREEN, min(MAX_GREEN, green))


class SignalController:
    """One road at a time: GREEN -> YELLOW -> ALL_RED -> next road.
    Emergency priority only changes WHO is next and HOW SOON the green ends.
    The control mode and gap-out only change HOW LONG a green lasts.
    Nothing here skips yellow or all-red."""

    def __init__(self, order):
        self.order = order
        self.index = 0
        self.phase = "GREEN"
        self.green_time = MIN_GREEN
        self.timer = MIN_GREEN
        self.emergency_queue = []
        self.emergency_mode = False
        self.hold_time = 0
        self.mode = DEFAULT_MODE
        self.forecaster = Forecaster(order)
        self.empty_for = 0.0                                     # NEW

    def current_road(self):
        return self.order[self.index]

    def request_emergency(self, road):
        already_served = self.emergency_mode and self.current_road() == road
        if road not in self.emergency_queue and not already_served:
            self.emergency_queue.append(road)
            print(f"EMERGENCY requested on {road}")

    def choose_next(self, densities):
        n = len(self.order)
        for step in range(1, n + 1):
            i = (self.index + step) % n
            if densities[self.order[i]]["count"] > 0:
                return i
        return (self.index + 1) % n

    def update(self, dt, densities, emergency_roads):
        self.forecaster.update(dt, densities)

        # --- NEW: gap-out. End a normal green early once the road has been empty for a moment ---
        if (self.mode != "fixed" and self.phase == "GREEN"
                and not self.emergency_mode and not self.emergency_queue):
            if densities[self.current_road()]["count"] == 0:
                self.empty_for += dt
            else:
                self.empty_for = 0.0
            if (self.green_time - self.timer >= GAP_MIN_GREEN
                    and self.empty_for >= GAP_EMPTY_TIME):
                self.timer = 0.0                 # the normal path below then moves to YELLOW
                self.empty_for = 0.0
                print(f"{self.current_road()}: queue cleared, ending green early")
        else:
            self.empty_for = 0.0

        # --- Step 1: holding a green for an emergency vehicle ---
        if self.emergency_mode and self.phase == "GREEN":
            self.hold_time += dt
            if self.current_road() in emergency_roads and self.hold_time < EMERGENCY_MAX_HOLD:
                return
            self.emergency_mode = False
            self.timer = EMERGENCY_CLEAR_TIME
            print(f"EMERGENCY cleared on {self.current_road()} - back to normal control")

        # --- Step 2: an emergency is waiting and we are in a normal green ---
        if self.emergency_queue and self.phase == "GREEN" and not self.emergency_mode:
            target = self.emergency_queue[0]
            if target == self.current_road():
                self.emergency_queue.pop(0)
                self.emergency_mode = True
                self.hold_time = 0
                print(f"EMERGENCY: {target} is already green - holding")
                return
            self.phase = "YELLOW"
            self.timer = YELLOW_TIME
            print(f"EMERGENCY: ending green on {self.current_road()} -> YELLOW")
            return

        # --- Step 3: normal timer and phase changes ---
        self.timer -= dt
        if self.timer > 0:
            return

        if self.phase == "GREEN":
            self.phase = "YELLOW"
            self.timer = YELLOW_TIME
        elif self.phase == "YELLOW":
            self.phase = "ALL_RED"
            self.timer = ALL_RED_TIME
        else:
            if self.emergency_queue:
                road = self.emergency_queue.pop(0)
                self.index = self.order.index(road)
                self.emergency_mode = True
                self.hold_time = 0
                self.green_time = EMERGENCY_CLEAR_TIME
                self.timer = EMERGENCY_CLEAR_TIME
                self.phase = "GREEN"
                print(f"EMERGENCY GREEN: {road}")
            else:
                self._start_normal_green(densities)

    def _start_normal_green(self, densities):
        if self.mode == "fixed":
            self.index = (self.index + 1) % len(self.order)
            road = self.current_road()
            score = used = densities[road]["score"]
            self.green_time = FIXED_GREEN
        else:
            self.index = self.choose_next(densities)
            road = self.current_road()
            score = densities[road]["score"]
            if self.mode == "predictive":
                used = self.forecaster.effective_score(road, score)
            else:
                used = score
            self.green_time = calculate_green_time(used)

        self.phase = "GREEN"
        self.timer = self.green_time
        self.empty_for = 0.0
        print(f"{road} [{self.mode}]: score={score} used={used:.1f} -> green {self.green_time:.1f}s")

    def get_state(self, road):
        if road != self.current_road():
            return "RED"
        if self.phase == "ALL_RED":
            return "RED"
        return self.phase