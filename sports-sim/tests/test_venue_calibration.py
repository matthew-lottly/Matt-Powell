"""Tests for venue calibration application."""

from typing import Any

import pytest
from sports_sim.core.models import Venue, SurfaceType, VenueType


class TestVenueCalibration:
    def _calibrate(self, **kwargs: Any):
        from sports_sim.realism.venue_calibration import calibrate_venue
        venue = Venue(
            name="Test", city="City", venue_type=VenueType.OPEN_AIR,
            surface=SurfaceType.NATURAL_GRASS, capacity=50000,
        )
        venue = venue.model_copy(update=kwargs)
        return calibrate_venue(venue)

    def test_low_altitude_zero_drain(self):
        cal = self._calibrate(altitude_m=500.0)
        assert cal.altitude_endurance_drain == 0.0
        assert cal.altitude_ball_velocity_bonus == 0.0

    def test_high_altitude_positive_drain(self):
        cal = self._calibrate(altitude_m=2500.0)
        assert cal.altitude_endurance_drain > 0.0
        assert cal.altitude_ball_velocity_bonus > 0.0

    def test_altitude_drain_capped(self):
        cal = self._calibrate(altitude_m=10000.0)
        assert cal.altitude_endurance_drain <= 0.15
        assert cal.altitude_ball_velocity_bonus <= 0.05

    def test_artificial_turf_speed_boost(self):
        cal = self._calibrate(surface=SurfaceType.ARTIFICIAL_TURF)
        assert cal.surface_speed_modifier > 0.0

    def test_poor_surface_increases_injury(self):
        cal = self._calibrate(surface_quality=0.5)
        assert cal.surface_injury_modifier > 1.0

    def test_good_surface_no_extra_injury(self):
        cal = self._calibrate(surface_quality=1.0)
        assert cal.surface_injury_modifier <= 1.0 or cal.surface_injury_modifier == pytest.approx(1.0, abs=0.01)

    def test_climate_controlled_no_weather_factors(self):
        cal = self._calibrate(
            venue_type=VenueType.DOME,
            climate_controlled=True,
            latitude=5.0,  # would be tropical
        )
        assert cal.heat_fatigue_modifier == 0.0
        assert cal.cold_speed_penalty == 0.0

    def test_large_capacity_higher_crowd(self):
        small = self._calibrate(capacity=10000, noise_factor=0.5)
        large = self._calibrate(capacity=80000, noise_factor=0.8)
        assert large.crowd_morale_boost >= small.crowd_morale_boost
