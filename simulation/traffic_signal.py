from config import *


def calculate_green_time(score):
    """More traffic = longer green, but always between MIN_GREEN and MAX_GREEN."""
    green = MIN_GREEN + score * SECONDS_PER_SCORE
    return max(MIN_GREEN, min(MAX_GREEN, green))


class SignalController:
    """One road at a time: GREEN -> YELLOW -> ALL_RED -> next road.
    Emergency priority only changes WHO is next and HOW SOON the green ends.
    It never skips yellow or all-red."""

    def __init__(self, order):
        self.order = order
        self.index = 0
        self.phase = "GREEN"
        self.green_time = MIN_GREEN
        self.timer = MIN_GREEN
        self.emergency_queue = []       # roads waiting for emergency priority
        self.emergency_mode = False     # True while an emergency road holds the green
        self.hold_time = 0              # how long the emergency green has been held

    def current_road(self):
        return self.order[self.index]

    def request_emergency(self, road):
        """Called when an emergency vehicle needs priority on this road."""
        already_served = self.emergency_mode and self.current_road() == road
        if road not in self.emergency_queue and not already_served:
            self.emergency_queue.append(road)
            print(f"EMERGENCY requested on {road}")

    def choose_next(self, densities):
        """Next road in order that has vehicles waiting. Skips empty roads."""
        n = len(self.order)
        for step in range(1, n + 1):
            i = (self.index + step) % n
            if densities[self.order[i]]["count"] > 0:
                return i
        return (self.index + 1) % n

    def update(self, dt, densities, emergency_roads):
        """emergency_roads = roads that have an emergency vehicle still before the stop line."""

        # --- Step 1: holding a green for an emergency vehicle ---
        if self.emergency_mode and self.phase == "GREEN":
            self.hold_time += dt
            if self.current_road() in emergency_roads and self.hold_time < EMERGENCY_MAX_HOLD:
                return                              # keep the green on
            self.emergency_mode = False             # vehicle has passed (or timeout)
            self.timer = EMERGENCY_CLEAR_TIME       # a few more seconds to clear the junction
            print(f"EMERGENCY cleared on {self.current_road()} - back to normal control")

        # --- Step 2: an emergency is waiting and we are in a normal green ---
        if self.emergency_queue and self.phase == "GREEN" and not self.emergency_mode:
            target = self.emergency_queue[0]
            if target == self.current_road():
                self.emergency_queue.pop(0)         # already green: just hold it
                self.emergency_mode = True
                self.hold_time = 0
                print(f"EMERGENCY: {target} is already green - holding")
                return
            self.phase = "YELLOW"                   # cut the green short, but SAFELY
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
        else:  # ALL_RED finished: choose who goes next
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
                self.index = self.choose_next(densities)
                road = self.current_road()
                score = densities[road]["score"]
                self.green_time = calculate_green_time(score)
                self.phase = "GREEN"
                self.timer = self.green_time
                print(f"{road}: score={score} level={densities[road]['level']} -> green {self.green_time:.1f}s")

    def get_state(self, road):
        """Returns 'GREEN', 'YELLOW' or 'RED' for the given road."""
        if road != self.current_road():
            return "RED"
        if self.phase == "ALL_RED":
            return "RED"
        return self.phase