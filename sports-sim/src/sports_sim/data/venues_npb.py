"""Sample NPB stadiums (minimal set)."""
from __future__ import annotations

from sports_sim.core.models import SurfaceType, Venue, VenueType


NPB_VENUES: dict[str, Venue] = {
    "TOK": Venue(name="Tokyo Dome", city="Tokyo", state="", capacity=55000,
                  venue_type=VenueType.DOME, surface=SurfaceType.MIXED, altitude_m=40,
                  latitude=35.7056, longitude=139.7514, weather_exposed=False),
    "OSK": Venue(name="Kyocera Dome", city="Osaka", state="", capacity=36500,
                  venue_type=VenueType.DOME, surface=SurfaceType.MIXED, altitude_m=20,
                  latitude=34.6544, longitude=135.4886, weather_exposed=False),
}
