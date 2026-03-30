"""ELO and Glicko-2 rating system for teams and players.

Updates ratings after each completed simulation based on actual vs expected outcome.
"""

from __future__ import annotations

import math

from sports_sim.core.models import GameState, Team


def expected_score(rating_a: float, rating_b: float) -> float:
    """ELO expected score for player A vs player B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def update_elo(
    winner: Team,
    loser: Team,
    draw: bool = False,
    k_factor: float | None = None,
) -> tuple[float, float]:
    """Update ELO ratings for two teams after a match.

    Returns the new (winner_elo, loser_elo) ratings.
    """
    k_w = k_factor or winner.elo_k_factor
    k_l = k_factor or loser.elo_k_factor

    e_w = expected_score(winner.elo_rating, loser.elo_rating)
    e_l = 1.0 - e_w

    if draw:
        s_w, s_l = 0.5, 0.5
    else:
        s_w, s_l = 1.0, 0.0

    new_w = winner.elo_rating + k_w * (s_w - e_w)
    new_l = loser.elo_rating + k_l * (s_l - e_l)

    winner.elo_rating = round(new_w, 1)
    loser.elo_rating = round(new_l, 1)

    return winner.elo_rating, loser.elo_rating


def update_elo_from_state(state: GameState) -> tuple[float, float]:
    """Convenience: update ELO ratings from a finished GameState."""
    home = state.home_team
    away = state.away_team

    if home.score > away.score:
        return update_elo(home, away, draw=False)
    elif away.score > home.score:
        return update_elo(away, home, draw=False)
    else:
        return update_elo(home, away, draw=True)


def margin_of_victory_multiplier(winner_score: int, loser_score: int) -> float:
    """Scale K-factor by margin of victory (log-based to prevent blowout inflation)."""
    diff = abs(winner_score - loser_score)
    if diff == 0:
        return 1.0
    return math.log(max(diff, 1) + 1) * (2.2 / ((winner_score - loser_score) * 0.001 + 2.2))


def update_elo_with_mov(state: GameState) -> tuple[float, float]:
    """Update ELO with margin-of-victory scaling."""
    home = state.home_team
    away = state.away_team
    mov = margin_of_victory_multiplier(
        max(home.score, away.score),
        min(home.score, away.score),
    )
    k = 32.0 * mov

    if home.score > away.score:
        return update_elo(home, away, draw=False, k_factor=k)
    elif away.score > home.score:
        return update_elo(away, home, draw=False, k_factor=k)
    else:
        return update_elo(home, away, draw=True, k_factor=k)


def update_form(team: Team, result: str) -> None:
    """Update team form rating based on recent results.

    result: "W", "L", or "D"
    """
    team.stats.last_5.append(result)
    if len(team.stats.last_5) > 5:
        team.stats.last_5 = team.stats.last_5[-5:]

    # Compute form from last 5 results
    form_map = {"W": 1.0, "D": 0.4, "L": 0.0}
    if team.stats.last_5:
        total = sum(form_map.get(r, 0.0) for r in team.stats.last_5)
        team.form_rating = total / len(team.stats.last_5)

    # Update streak
    if result == "W":
        team.stats.streak = max(1, team.stats.streak + 1) if team.stats.streak >= 0 else 1
    elif result == "L":
        team.stats.streak = min(-1, team.stats.streak - 1) if team.stats.streak <= 0 else -1
    else:
        team.stats.streak = 0


def update_team_stats_from_state(state: GameState) -> None:
    """Update TeamStats for both teams after a finished game."""
    home = state.home_team
    away = state.away_team

    home.stats.goals_for += home.score
    home.stats.goals_against += away.score
    away.stats.goals_for += away.score
    away.stats.goals_against += home.score

    if home.score > away.score:
        home.stats.wins += 1
        home.stats.home_wins += 1
        away.stats.losses += 1
        update_form(home, "W")
        update_form(away, "L")
    elif away.score > home.score:
        away.stats.wins += 1
        away.stats.away_wins += 1
        home.stats.losses += 1
        update_form(home, "L")
        update_form(away, "W")
    else:
        home.stats.draws += 1
        away.stats.draws += 1
        update_form(home, "D")
        update_form(away, "D")
