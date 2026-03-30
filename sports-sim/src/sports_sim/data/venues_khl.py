"""Sample KHL arenas (minimal set)."""
from __future__ import annotations

from sports_sim.core.models import SurfaceType, Venue, VenueType


KHL_VENUES: dict[str, Venue] = {
    "MCK": Venue(name="Megasport Arena", city="Moscow", state="", capacity=13500,
                  venue_type=VenueType.INDOOR_ARENA, surface=SurfaceType.ICE,
                  altitude_m=156, latitude=55.8214, longitude=37.5555, weather_exposed=False),
    "SPB": Venue(name="Ice Palace", city="St Petersburg", state="", capacity=12300,
                  venue_type=VenueType.INDOOR_ARENA, surface=SurfaceType.ICE,
                  altitude_m=5, latitude=59.9721, longitude=30.2219, weather_exposed=False),
}
