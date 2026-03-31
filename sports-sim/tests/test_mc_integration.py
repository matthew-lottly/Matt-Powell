from sports_sim.mc.integration import EngineEvaluator


def test_engine_evaluator_runs_quick():
    ev = EngineEvaluator()
    params = {"attack_factor": 1.0, "defense_factor": 1.0}
    score = ev.evaluate(params, n_sims=1, sport="soccer")
    assert isinstance(score, float)
