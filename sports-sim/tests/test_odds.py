from sports_sim.odds.odds import decimal_to_implied_prob, normalize_market


def test_decimal_to_implied_prob():
    assert abs(decimal_to_implied_prob(2.0) - 0.5) < 1e-6


def test_normalize_market():
    odds = {"a": 2.0, "b": 3.0}
    norm = normalize_market(odds)
    assert abs(sum(norm.values()) - 1.0) < 1e-6
