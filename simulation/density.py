from config import *
from vehicle import STOP_PROGRESS


def in_detection_zone(vehicle):
    """True if the vehicle is before the stop line and within DETECTION_ZONE of it."""
    front = vehicle.progress() + vehicle.length / 2
    dist = STOP_PROGRESS[vehicle.road] - front     # distance still to go to the stop line
    return -1 <= dist <= DETECTION_ZONE


def density_level(score):
    if score <= DENSITY_LOW_MAX:
        return "LOW"
    if score <= DENSITY_MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def measure_road(lane):
    """Returns the vehicle count, density score and level for one road."""
    zone = [v for v in lane if in_detection_zone(v)]
    score = sum(VEHICLE_WEIGHT[v.kind] for v in zone)
    return {
        "count": len(zone),
        "score": score,
        "level": density_level(score),
    }


def measure_all(vehicles):
    """vehicles is the dict {road: [Vehicle, ...]}. Returns results for every road."""
    return {road: measure_road(lane) for road, lane in vehicles.items()}