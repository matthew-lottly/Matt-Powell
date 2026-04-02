from sports_sim.data.rosters_mlb import get_all_mlb_teams
from sports_sim.data.rosters_nba import get_all_nba_teams
from sports_sim.data.rosters_nhl import get_nhl_team
from sports_sim.sports.hockey import _attack_profile, _defense_profile, _power_play_multiplier


def test_nba_teams_have_rotation_depth_and_profiles() -> None:
    teams = get_all_nba_teams()

    assert len(teams) == 5

    for team in teams.values():
        assert len(team.players) == 5
        assert len(team.bench) == 8
        assert team.overall_offense > 0.6
        assert team.overall_defense > 0.55
        assert team.overall_special_teams > 0.55
        assert team.depth_rating > 0.5


def test_mlb_teams_have_bench_bats_and_pitching_depth() -> None:
    teams = get_all_mlb_teams()

    assert len(teams) == 4

    for team in teams.values():
        assert len(team.players) == 9
        assert len(team.bench) == 9
        assert sum(1 for player in team.bench if player.position == "P") >= 4
        assert team.overall_offense > 0.6
        assert team.overall_defense > 0.58
        assert team.overall_special_teams > 0.55
        assert team.depth_rating > 0.5


def test_nhl_real_depth_snapshot_populates_known_bench_player() -> None:
    ducks = get_nhl_team("ANA")

    assert ducks is not None
    assert any(player.name == "Leo Carlsson" for player in ducks.bench)


def test_hockey_profiles_reflect_team_strength_and_special_teams() -> None:
    oilers = get_nhl_team("EDM")
    blackhawks = get_nhl_team("CHI")

    assert oilers is not None
    assert blackhawks is not None

    assert _attack_profile(oilers) > _attack_profile(blackhawks)
    assert _defense_profile(oilers) > 0.5
    assert _power_play_multiplier(oilers) > _power_play_multiplier(blackhawks)
