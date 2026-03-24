import math


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance using Haversine formula. Returns kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


_MULTIPLIERS = {"drive": 1.3, "transit": 1.8, "bike": 2.5}


def calculate_commute_minutes(
    apt_lat: float, apt_lon: float,
    work_lat: float, work_lon: float,
    method: str,
) -> int:
    """Estimate one-way commute in minutes using mode-specific min/km multiplier.

    Multipliers: drive=1.3, transit=1.8, bike=2.5 min/km.
    Defaults to transit for unknown methods. Minimum 1 minute.
    """
    km = haversine_distance_km(apt_lat, apt_lon, work_lat, work_lon)
    multiplier = _MULTIPLIERS.get(method, _MULTIPLIERS["transit"])
    return max(1, round(km * multiplier))
