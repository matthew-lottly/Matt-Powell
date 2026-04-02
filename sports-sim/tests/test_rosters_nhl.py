from sports_sim.data.rosters_nhl import get_all_nhl_teams, get_nhl_team


def test_all_nhl_teams_have_depth_bench() -> None:
    teams = get_all_nhl_teams()

    assert len(teams) == 32

    for team in teams.values():
        assert len(team.players) == 6
        assert len(team.bench) == 12
        assert any(player.position == "G" for player in team.players)
        assert any(player.position == "G" for player in team.bench)


def test_nhl_players_include_extended_ratings() -> None:
    oilers = get_nhl_team("EDM")
    assert oilers is not None

    mcdavid = next(player for player in oilers.players if player.name == "Connor McDavid")

    assert mcdavid.attributes.awareness >= 0.8
    assert mcdavid.attributes.clutch >= 0.8
    assert mcdavid.attributes.durability >= 0.65


def test_nhl_team_strengths_reflect_roster_quality() -> None:
    oilers = get_nhl_team("EDM")
    blackhawks = get_nhl_team("CHI")

    assert oilers is not None
    assert blackhawks is not None

    assert oilers.overall_offense > blackhawks.overall_offense
    assert oilers.overall_special_teams > blackhawks.overall_special_teams
    assert oilers.depth_rating > 0.5
