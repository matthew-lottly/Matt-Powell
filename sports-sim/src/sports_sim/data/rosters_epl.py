"""Minimal EPL roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team
try:
    from sports_sim.data.venues_epl import EPL_VENUES
except Exception:
    EPL_VENUES = {}


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.7, strength=0.6, accuracy=0.75,
                                               endurance=0.75, skill=0.8, decision_making=0.75,
                                               aggression=0.6, composure=0.7))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="4-3-3",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.6, motivation=0.7))


MAN = _team("Man United", "Manchester", "MUN", "Erik Ten Hag", [
    _p("Rashford", 10, "LW"), _p("Martial", 9, "CF"), _p("Varane", 5, "CB"),
    _p("De Gea", 1, "GK"), _p("Sancho", 11, "RW"), _p("Bruno", 8, "CM"),
    _p("Shaw", 23, "LB"), _p("Casemiro", 18, "DM"), _p("Fernandes", 20, "AM"),
    _p("Maguire", 2, "CB"), _p("Henderson", 14, "CM"),
])

MCI = _team("Man City", "Manchester", "MCI", "Pep Guardiola", [
    _p("De Bruyne", 17, "CM"), _p("Haaland", 9, "CF"), _p("Foden", 47, "RW"),
    _p("Ederson", 31, "GK"), _p("Grealish", 10, "LW"), _p("Rodri", 16, "DM"),
    _p("Walker", 2, "RB"), _p("Cancelo", 27, "LB"), _p("Mahrez", 26, "RW"),
    _p("Stones", 5, "CB"), _p("KDB", 8, "AM"),
])

LIV = _team("Liverpool", "Liverpool", "LIV", "Jurgen Klopp", [
    _p("Salah", 11, "RW"), _p("Diaz", 7, "LW"), _p("Henderson", 14, "CM"),
    _p("Alisson", 1, "GK"), _p("Van Dijk", 4, "CB"), _p("Alexander-Arnold", 66, "RB"),
    _p("Gakpo", 18, "CF"), _p("Salah2", 10, "AM"), _p("Jota", 20, "FW"),
    _p("Matip", 32, "CB"), _p("Fabinho", 3, "DM"),
])

ARS = _team("Arsenal", "London", "ARS", "Mikel Arteta", [
    _p("Saka", 7, "RW"), _p("Ødegaard", 11, "AM"), _p("Jesus", 9, "CF"),
    _p("Ramsdale", 1, "GK"), _p("White", 4, "RB"), _p("Saliba", 12, "CB"),
    _p("Rice", 41, "DM"), _p("Martinelli", 35, "LW"), _p("Partey", 5, "CM"),
    _p("Gabriel", 6, "CB"), _p("Øde", 10, "AM"),
])

CHE = _team("Chelsea", "London", "CHE", "P. Tuchel", [
    _p("Mendy", 16, "GK"), _p("Kovacic", 8, "CM"), _p("Mount", 19, "AM"),
    _p("Sterling", 7, "LW"), _p("Kepa", 1, "GK"), _p("Chilwell", 21, "LB"),
    _p("Kante", 13, "DM"), _p("Silva", 22, "CB"), _p("Pulisic", 10, "LW"),
    _p("Havertz", 29, "CF"), _p("James", 24, "RB"),
])

TOT = _team("Tottenham", "London", "TOT", "Antonio Conte", [
    _p("Kane", 10, "CF"), _p("Son", 7, "LW"), _p("Hojbjerg", 5, "CM"),
    _p("Lloris", 1, "GK"), _p("Reguilon", 3, "LB"), _p("Richarlison", 9, "CF"),
    _p("Perisic", 44, "LW"), _p("Dier", 15, "CB"), _p("Bissouma", 8, "DM"),
    _p("Sessegnon", 2, "RB"), _p("Rodon", 6, "CB"),
])

NEW = _team("Newcastle", "Newcastle", "NEW", "Eddie Howe", [
    _p("Wilson", 9, "CF"), _p("Saint-Maximin", 10, "LW"), _p("Trippier", 12, "RB"),
    _p("Schar", 3, "CB"), _p("Guimaraes", 41, "CM"), _p("Dubravka", 1, "GK"),
    _p("Joelinton", 7, "CM"), _p("Almiron", 11, "RW"), _p("Gilmour", 30, "DM"),
    _p("Burn", 2, "LB"), _p("Krafth", 21, "RB"),
])

WHU = _team("West Ham", "London", "WHU", "David Moyes", [
    _p("Bowen", 20, "RW"), _p("Benrahma", 21, "AM"), _p("Fabianski", 1, "GK"),
    _p("Soucek", 28, "CM"), _p("Coufal", 24, "RB"), _p("Rice", 41, "DM"),
    _p("Antonio", 9, "CF"), _p("Ogbonna", 23, "CB"), _p("Johnson", 5, "LB"),
    _p("Noble", 16, "CM"), _p("Fornals", 8, "AM"),
])

BRE = _team("Brentford", "London", "BRE", "Thomas Frank", [
    _p("Mbeumo", 19, "RW"), _p("Toney", 9, "CF"), _p("Dasilva", 24, "CM"),
    _p("Raya", 1, "GK"), _p("Janelt", 6, "DM"), _p("Norgaard", 2, "CM"),
    _p("Roerslev", 29, "RB"), _p("Benrahma2", 11, "AM"), _p("Wissa", 17, "CF"),
    _p("Hurt", 4, "CB"), _p("Henry", 5, "CB"),
])

LEI = _team("Leicester", "Leicester", "LEI", "Enzo Maresca", [
    _p("Vardy", 9, "CF"), _p("Ndidi", 25, "DM"), _p("Fofana", 3, "CB"),
    _p("Schmeichel", 1, "GK"), _p("Pereira", 10, "AM"), _p("James", 23, "RB"),
    _p("Tielemans", 8, "CM"), _p("Albrighton", 11, "RW"), _p("Dewsbury-Hall", 16, "CM"),
    _p("Evans", 6, "CB"), _p("Justin", 2, "RB"),
])


def get_all_epl_teams() -> dict[str, Team]:
    teams = {
        "MUN": MAN, "MCI": MCI, "LIV": LIV, "ARS": ARS, "CHE": CHE,
        "TOT": TOT, "NEW": NEW, "WHU": WHU, "BRE": BRE, "LEI": LEI,
    }
    # Attach venue objects when available
    for abbr, t in teams.items():
        if abbr in EPL_VENUES:
            t.venue = EPL_VENUES[abbr]
    return teams


def get_epl_team(abbr: str) -> Team | None:
    return get_all_epl_teams().get(abbr)
