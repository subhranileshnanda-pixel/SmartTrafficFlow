"""Short-term traffic forecasting using Holt's linear exponential smoothing."""

SAMPLE_EVERY = 1.0        # take one sample per second
ALPHA = 0.4               # how quickly the level follows new data (0 to 1)
BETA = 0.2                # how quickly the trend follows new data (0 to 1)
CONTROL_HORIZON = 10      # seconds ahead used for green-time decisions
DISPLAY_HORIZON = 30      # seconds ahead shown on the dashboard
MAX_SCORE = 20            # forecasts are capped, so one spike can't dominate

LOW_MAX = 3               # same thresholds as the simulation's density levels
MEDIUM_MAX = 7


def level_of(score):
    if score <= LOW_MAX:
        return "LOW"
    if score <= MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


class Forecaster:
    def __init__(self, roads):
        self.roads = list(roads)
        self.state = {r: None for r in self.roads}    # road -> (level, trend per second)
        self.acc = 0.0

    def update(self, dt, densities):
        """Called every frame. Takes a sample once per second."""
        self.acc += dt
        if self.acc < SAMPLE_EVERY - 1e-9:
            return
        self.acc = 0.0
        for road in self.roads:
            x = float(densities[road]["score"])
            st = self.state[road]
            if st is None:
                self.state[road] = (x, 0.0)
                continue
            level, trend = st
            new_level = ALPHA * x + (1 - ALPHA) * (level + trend)
            new_trend = BETA * (new_level - level) + (1 - BETA) * trend
            self.state[road] = (new_level, new_trend)

    def forecast(self, road, seconds_ahead):
        st = self.state[road]
        if st is None:
            return 0.0
        level, trend = st
        return max(0.0, min(MAX_SCORE, level + trend * seconds_ahead))

    def effective_score(self, road, current_score):
        """The score used to size a green: never lower than what is waiting now."""
        return max(float(current_score), self.forecast(road, CONTROL_HORIZON))

    def snapshot(self):
        """What the dashboard shows for each road."""
        out = {}
        for road in self.roads:
            st = self.state[road]
            if st is None:
                out[road] = {"predicted_score": 0, "predicted_level": "LOW", "trend": "steady"}
                continue
            pred = self.forecast(road, DISPLAY_HORIZON)
            trend = st[1]
            label = "rising" if trend > 0.05 else "falling" if trend < -0.05 else "steady"
            out[road] = {
                "predicted_score": round(pred, 1),
                "predicted_level": level_of(pred),
                "trend": label,
            }
        return out