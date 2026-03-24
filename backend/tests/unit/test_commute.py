"""Unit tests for app/services/commute.py.

Tests the Haversine distance formula and the commute time estimator.
All tests are pure-function — no I/O, no database.
"""

import math

import pytest

from app.services.commute import calculate_commute_minutes, haversine_distance_km


# ── haversine_distance_km ─────────────────────────────────────────────────────

class TestHaversineDistanceKm:
    def test_same_point_returns_zero(self):
        assert haversine_distance_km(40.7128, -74.006, 40.7128, -74.006) == pytest.approx(0.0, abs=1e-6)

    def test_equator_vs_north_pole(self):
        # Quarter of Earth's circumference: ~10,007.5 km
        dist = haversine_distance_km(0.0, 0.0, 90.0, 0.0)
        assert dist == pytest.approx(10007.5, rel=0.005)

    def test_known_nyc_to_boston(self):
        # NYC (40.7128, -74.006) to Boston (42.3601, -71.0589)
        # Great-circle distance ~306 km
        dist = haversine_distance_km(40.7128, -74.006, 42.3601, -71.0589)
        assert 290 < dist < 320

    def test_known_nyc_to_brooklyn(self):
        # Downtown Brooklyn (40.6928, -73.9903) vs Manhattan (40.7580, -73.9855)
        dist = haversine_distance_km(40.758, -73.9855, 40.6928, -73.9903)
        assert 5 < dist < 10

    def test_symmetric(self):
        a = haversine_distance_km(40.7128, -74.006, 42.3601, -71.0589)
        b = haversine_distance_km(42.3601, -71.0589, 40.7128, -74.006)
        assert a == pytest.approx(b, rel=1e-9)

    def test_returns_float(self):
        result = haversine_distance_km(0.0, 0.0, 1.0, 0.0)
        assert isinstance(result, float)

    def test_antipodal_points(self):
        # Max possible distance ~20,015 km (half Earth circumference)
        dist = haversine_distance_km(0.0, 0.0, 0.0, 180.0)
        assert dist == pytest.approx(20015.0, rel=0.01)

    def test_negative_coordinates_work(self):
        # Sydney (-33.8688, 151.2093) to some point
        dist = haversine_distance_km(-33.8688, 151.2093, -33.8688, 151.2093)
        assert dist == pytest.approx(0.0, abs=1e-6)


# ── calculate_commute_minutes ─────────────────────────────────────────────────

class TestCalculateCommuteMinutes:
    """Uses a fixed short distance (same point offset) to keep math simple."""

    # NYC Midtown to ~ 1 km north — about 1 km distance
    APT = (40.7128, -74.006)
    # One degree of latitude ~ 111 km, so 0.009 deg ~ 1 km
    WORK_1KM_NORTH = (40.7218, -74.006)

    def _distance_1km(self) -> float:
        return haversine_distance_km(*self.APT, *self.WORK_1KM_NORTH)

    def test_drive_multiplier(self):
        dist = self._distance_1km()
        expected = max(1, round(dist * 1.3))
        result = calculate_commute_minutes(*self.APT, *self.WORK_1KM_NORTH, "drive")
        assert result == expected

    def test_transit_multiplier(self):
        dist = self._distance_1km()
        expected = max(1, round(dist * 1.8))
        result = calculate_commute_minutes(*self.APT, *self.WORK_1KM_NORTH, "transit")
        assert result == expected

    def test_bike_multiplier(self):
        dist = self._distance_1km()
        expected = max(1, round(dist * 2.5))
        result = calculate_commute_minutes(*self.APT, *self.WORK_1KM_NORTH, "bike")
        assert result == expected

    def test_unknown_method_defaults_to_transit(self):
        transit = calculate_commute_minutes(*self.APT, *self.WORK_1KM_NORTH, "transit")
        unknown = calculate_commute_minutes(*self.APT, *self.WORK_1KM_NORTH, "helicopter")
        assert transit == unknown

    def test_same_point_returns_minimum_one(self):
        # Distance = 0, so raw = 0, but minimum is 1
        result = calculate_commute_minutes(40.7128, -74.006, 40.7128, -74.006, "drive")
        assert result == 1

    def test_returns_integer(self):
        result = calculate_commute_minutes(*self.APT, *self.WORK_1KM_NORTH, "drive")
        assert isinstance(result, int)

    def test_drive_is_faster_than_transit(self):
        drive = calculate_commute_minutes(40.7128, -74.006, 42.3601, -71.0589, "drive")
        transit = calculate_commute_minutes(40.7128, -74.006, 42.3601, -71.0589, "transit")
        assert drive < transit

    def test_transit_is_faster_than_bike(self):
        transit = calculate_commute_minutes(40.7128, -74.006, 42.3601, -71.0589, "transit")
        bike = calculate_commute_minutes(40.7128, -74.006, 42.3601, -71.0589, "bike")
        assert transit < bike

    def test_long_distance_nyc_to_boston(self):
        # ~306 km * 1.3 (drive) = ~398 min; just verify it is a large integer
        result = calculate_commute_minutes(40.7128, -74.006, 42.3601, -71.0589, "drive")
        assert result > 100

    def test_result_never_below_one(self):
        # Arbitrarily tiny distance should still return >= 1
        result = calculate_commute_minutes(40.7128, -74.006, 40.71281, -74.006, "drive")
        assert result >= 1
