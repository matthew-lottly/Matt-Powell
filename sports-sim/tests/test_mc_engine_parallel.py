from sports_sim.mc.integration import EngineEvaluator


def test_engine_evaluator_parallel_quick():
    ev = EngineEvaluator()
    params = {"attack_factor": 1.0, "defense_factor": 1.0}
    # run 2 sims in parallel workers=2 to smoke test worker process path
    score = ev.evaluate(params, n_sims=2, sport="soccer")
    assert isinstance(score, float)
