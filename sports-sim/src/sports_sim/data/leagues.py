"""Known leagues and data availability per sport."""
from typing import Dict, List

LEAGUES: Dict[str, List[Dict[str, object]]] = {
    "soccer": [
        {"id": "mls", "name": "MLS", "roster_available": True, "venues": True, "source": "public"},
        {"id": "epl", "name": "English Premier League", "roster_available": True, "venues": True, "source": "public"},
        {"id": "la_liga", "name": "La Liga", "roster_available": False, "venues": True, "source": "public"},
        {"id": "ncaasoc", "name": "NCAA Soccer", "roster_available": False, "venues": False, "source": "public"},
        {"id": "overseas", "name": "Overseas/Other", "roster_available": False, "venues": False, "source": "mixed"},
    ],
    "basketball": [
        {"id": "nba", "name": "NBA", "roster_available": True, "venues": True, "source": "public"},
        {"id": "euro", "name": "EuroLeague", "roster_available": False, "venues": True, "source": "public"},
        {"id": "ncaab", "name": "NCAA Basketball", "roster_available": False, "venues": False, "source": "public"},
        {"id": "gleague", "name": "G League", "roster_available": False, "venues": False, "source": "public"},
    ],
    "baseball": [
        {"id": "mlb", "name": "MLB", "roster_available": True, "venues": True, "source": "public"},
        {"id": "npb", "name": "NPB (Japan)", "roster_available": False, "venues": True, "source": "public"},
        {"id": "kbo", "name": "KBO (Korea)", "roster_available": False, "venues": True, "source": "public"},
    ],
    "football": [
        {"id": "nfl", "name": "NFL", "roster_available": True, "venues": True, "source": "public"},
        {"id": "ncaa", "name": "NCAA Football", "roster_available": False, "venues": False, "source": "public"},
        {"id": "usfl", "name": "USFL", "roster_available": False, "venues": False, "source": "public"},
    ],
    "hockey": [
        {"id": "nhl", "name": "NHL", "roster_available": True, "venues": True, "source": "public"},
        {"id": "khl", "name": "KHL", "roster_available": False, "venues": True, "source": "public"},
        {"id": "ahc", "name": "AHL/College", "roster_available": False, "venues": False, "source": "mixed"},
    ],
    "tennis": [
        {"id": "atp", "name": "ATP", "roster_available": False, "venues": True, "source": "public"},
        {"id": "wta", "name": "WTA", "roster_available": False, "venues": True, "source": "public"},
        {"id": "itf", "name": "ITF/Challenger", "roster_available": False, "venues": False, "source": "public"},
    ],
    "golf": [
        {"id": "pga", "name": "PGA Tour", "roster_available": False, "venues": True, "source": "public"},
        {"id": "lpga", "name": "LPGA", "roster_available": False, "venues": True, "source": "public"},
    ],
    "cricket": [
        {"id": "ipl", "name": "IPL", "roster_available": False, "venues": True, "source": "public"},
        {"id": "t20", "name": "T20 Domestic", "roster_available": False, "venues": True, "source": "public"},
    ],
    "boxing": [
        {"id": "pro", "name": "Professional", "roster_available": False, "venues": True, "source": "public"},
        {"id": "amateur", "name": "Amateur", "roster_available": False, "venues": False, "source": "public"},
    ],
    "mma": [
        {"id": "ufc", "name": "UFC", "roster_available": False, "venues": True, "source": "public"},
        {"id": "bellator", "name": "Bellator", "roster_available": False, "venues": True, "source": "public"},
    ],
    "racing": [
        {"id": "f1", "name": "Formula 1", "roster_available": False, "venues": True, "source": "public"},
        {"id": "nascar", "name": "NASCAR", "roster_available": False, "venues": True, "source": "public"},
    ],
}


def get_leagues_for_sport(sport: str):
    return LEAGUES.get(sport, [])
