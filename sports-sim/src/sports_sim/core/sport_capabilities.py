"""Per-sport environment and gameplay capability mapping.

Defines which environmental controls, venue features, and gameplay mechanics
apply to each sport.  Used by the API (validation), frontend (conditional UI),
and engine (guard rails on effects).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from sports_sim.core.models import SportType, SurfaceType, VenueType


@dataclass(frozen=True)
class SportCapabilities:
    """Describes what environmental/venue/gameplay features a sport supports."""

    # --- venue / environment ---
    is_outdoor: bool = True
    weather_affected: bool = True
    temperature_affected: bool = True
    wind_affected: bool = True
    humidity_affected: bool = True
    altitude_affected: bool = True
    surface_affected: bool = True

    # --- gameplay ---
    uses_teams: bool = True
    players_per_side: int = 11
    has_bench: bool = True
    max_substitutions: int = 5
    has_timeouts: bool = False
    has_overtime: bool = True
    has_shootout: bool = False
    has_penalty: bool = True
    has_cards: bool = False

    # --- valid surface/venue types ---
    valid_surfaces: tuple[SurfaceType, ...] = (SurfaceType.NATURAL_GRASS,)
    valid_venue_types: tuple[VenueType, ...] = (VenueType.OPEN_AIR,)
    default_surface: SurfaceType = SurfaceType.NATURAL_GRASS
    default_venue_type: VenueType = VenueType.OPEN_AIR


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SPORT_CAPABILITIES: dict[SportType, SportCapabilities] = {
    SportType.SOCCER: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=True,
        players_per_side=11,
        has_bench=True,
        max_substitutions=5,
        has_timeouts=False,
        has_overtime=True,
        has_shootout=True,
        has_penalty=True,
        has_cards=True,
        valid_surfaces=(
            SurfaceType.NATURAL_GRASS, SurfaceType.ARTIFICIAL_TURF,
            SurfaceType.FIELDTURF, SurfaceType.HYBRID_GRASS,
        ),
        valid_venue_types=(VenueType.OPEN_AIR, VenueType.DOME, VenueType.RETRACTABLE_ROOF),
        default_surface=SurfaceType.NATURAL_GRASS,
        default_venue_type=VenueType.OPEN_AIR,
    ),
    SportType.BASKETBALL: SportCapabilities(
        is_outdoor=False,
        weather_affected=False,
        temperature_affected=False,
        wind_affected=False,
        humidity_affected=False,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=True,
        players_per_side=5,
        has_bench=True,
        max_substitutions=99,
        has_timeouts=True,
        has_overtime=True,
        has_shootout=False,
        has_penalty=True,
        has_cards=False,
        valid_surfaces=(SurfaceType.HARDWOOD,),
        valid_venue_types=(VenueType.INDOOR_ARENA,),
        default_surface=SurfaceType.HARDWOOD,
        default_venue_type=VenueType.INDOOR_ARENA,
    ),
    SportType.BASEBALL: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=True,
        players_per_side=9,
        has_bench=True,
        max_substitutions=99,
        has_timeouts=False,
        has_overtime=True,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(
            SurfaceType.NATURAL_GRASS, SurfaceType.ARTIFICIAL_TURF,
            SurfaceType.DIRT,
        ),
        valid_venue_types=(VenueType.OPEN_AIR, VenueType.DOME, VenueType.RETRACTABLE_ROOF),
        default_surface=SurfaceType.NATURAL_GRASS,
        default_venue_type=VenueType.OPEN_AIR,
    ),
    SportType.FOOTBALL: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=True,
        players_per_side=11,
        has_bench=True,
        max_substitutions=99,
        has_timeouts=True,
        has_overtime=True,
        has_shootout=False,
        has_penalty=True,
        has_cards=False,
        valid_surfaces=(
            SurfaceType.NATURAL_GRASS, SurfaceType.ARTIFICIAL_TURF,
            SurfaceType.FIELDTURF,
        ),
        valid_venue_types=(VenueType.OPEN_AIR, VenueType.DOME, VenueType.RETRACTABLE_ROOF),
        default_surface=SurfaceType.NATURAL_GRASS,
        default_venue_type=VenueType.OPEN_AIR,
    ),
    SportType.HOCKEY: SportCapabilities(
        is_outdoor=False,
        weather_affected=False,
        temperature_affected=False,
        wind_affected=False,
        humidity_affected=False,
        altitude_affected=False,
        surface_affected=True,
        uses_teams=True,
        players_per_side=6,
        has_bench=True,
        max_substitutions=99,
        has_timeouts=True,
        has_overtime=True,
        has_shootout=True,
        has_penalty=True,
        has_cards=False,
        valid_surfaces=(SurfaceType.ICE,),
        valid_venue_types=(VenueType.RINK, VenueType.INDOOR_ARENA),
        default_surface=SurfaceType.ICE,
        default_venue_type=VenueType.RINK,
    ),
    SportType.TENNIS: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=False,
        players_per_side=1,
        has_bench=False,
        max_substitutions=0,
        has_timeouts=False,
        has_overtime=False,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(
            SurfaceType.CLAY, SurfaceType.HARD_COURT, SurfaceType.GRASS_COURT,
        ),
        valid_venue_types=(VenueType.TENNIS_CENTER, VenueType.OPEN_AIR),
        default_surface=SurfaceType.HARD_COURT,
        default_venue_type=VenueType.TENNIS_CENTER,
    ),
    SportType.GOLF: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=False,
        players_per_side=1,
        has_bench=False,
        max_substitutions=0,
        has_timeouts=False,
        has_overtime=False,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(SurfaceType.NATURAL_GRASS,),
        valid_venue_types=(VenueType.GOLF_COURSE,),
        default_surface=SurfaceType.NATURAL_GRASS,
        default_venue_type=VenueType.GOLF_COURSE,
    ),
    SportType.CRICKET: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=True,
        players_per_side=11,
        has_bench=True,
        max_substitutions=1,
        has_timeouts=False,
        has_overtime=False,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(SurfaceType.NATURAL_GRASS,),
        valid_venue_types=(VenueType.CRICKET_GROUND, VenueType.OPEN_AIR),
        default_surface=SurfaceType.NATURAL_GRASS,
        default_venue_type=VenueType.CRICKET_GROUND,
    ),
    SportType.BOXING: SportCapabilities(
        is_outdoor=False,
        weather_affected=False,
        temperature_affected=False,
        wind_affected=False,
        humidity_affected=False,
        altitude_affected=True,
        surface_affected=False,
        uses_teams=False,
        players_per_side=1,
        has_bench=False,
        max_substitutions=0,
        has_timeouts=False,
        has_overtime=False,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(SurfaceType.CANVAS,),
        valid_venue_types=(VenueType.BOXING_ARENA, VenueType.INDOOR_ARENA),
        default_surface=SurfaceType.CANVAS,
        default_venue_type=VenueType.BOXING_ARENA,
    ),
    SportType.MMA: SportCapabilities(
        is_outdoor=False,
        weather_affected=False,
        temperature_affected=False,
        wind_affected=False,
        humidity_affected=False,
        altitude_affected=True,
        surface_affected=False,
        uses_teams=False,
        players_per_side=1,
        has_bench=False,
        max_substitutions=0,
        has_timeouts=False,
        has_overtime=False,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(SurfaceType.CANVAS,),
        valid_venue_types=(VenueType.OCTAGON, VenueType.INDOOR_ARENA),
        default_surface=SurfaceType.CANVAS,
        default_venue_type=VenueType.OCTAGON,
    ),
    SportType.RACING: SportCapabilities(
        is_outdoor=True,
        weather_affected=True,
        temperature_affected=True,
        wind_affected=True,
        humidity_affected=True,
        altitude_affected=True,
        surface_affected=True,
        uses_teams=False,
        players_per_side=1,
        has_bench=False,
        max_substitutions=0,
        has_timeouts=False,
        has_overtime=False,
        has_shootout=False,
        has_penalty=False,
        has_cards=False,
        valid_surfaces=(SurfaceType.ASPHALT,),
        valid_venue_types=(VenueType.RACE_TRACK,),
        default_surface=SurfaceType.ASPHALT,
        default_venue_type=VenueType.RACE_TRACK,
    ),
}


def get_capabilities(sport: SportType) -> SportCapabilities:
    """Return the capability profile for a sport."""
    return SPORT_CAPABILITIES[sport]
