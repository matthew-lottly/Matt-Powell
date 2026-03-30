"""Sample IPL (cricket) stadiums (minimal set)."""
from __future__ import annotations

from sports_sim.core.models import SurfaceType, Venue, VenueType


IPL_VENUES: dict[str, Venue] = {
    "MI": Venue(name="Wankhede Stadium", city="Mumbai", state="", capacity=33100,
                 venue_type=VenueType.OPEN_AIR, surface=SurfaceType.NATURAL_GRASS,
                 altitude_m=14, latitude=18.9388, longitude=72.8258, weather_exposed=True),
    "RCB": Venue(name="M Chinnaswamy Stadium", city="Bangalore", state="", capacity=38000,
                  venue_type=VenueType.OPEN_AIR, surface=SurfaceType.NATURAL_GRASS,
                  altitude_m=920, latitude=12.9980, longitude=77.5966, weather_exposed=True),
}
