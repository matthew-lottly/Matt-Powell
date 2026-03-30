"""Sample MLS venues (minimal set)."""
from __future__ import annotations

from sports_sim.core.models import SurfaceType, Venue, VenueType


MLS_VENUES: dict[str, Venue] = {
    "ATL": Venue(name="Mercedes-Benz Stadium", city="Atlanta", state="GA", capacity=71000,
                  venue_type=VenueType.RETRACTABLE_ROOF, surface=SurfaceType.NATURAL_GRASS,
                  altitude_m=300, latitude=33.7550, longitude=-84.4008, weather_exposed=True),
    "NYC": Venue(name="Yankee Stadium", city="New York", state="NY", capacity=47000,
                  venue_type=VenueType.OPEN_AIR, surface=SurfaceType.NATURAL_GRASS,
                  altitude_m=10, latitude=40.8296, longitude=-73.9262, weather_exposed=True),
    "LAFC": Venue(name="BMO Stadium", city="Los Angeles", state="CA", capacity=22000,
                  venue_type=VenueType.OPEN_AIR, surface=SurfaceType.NATURAL_GRASS,
                  altitude_m=30, latitude=34.0079, longitude=-118.2390, weather_exposed=True),
}
