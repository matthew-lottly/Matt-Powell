import json

import numpy as np

from bobcat_corridor_lab.config import BarrierCosts, DemoScenario, SuitabilityWeights
from bobcat_corridor_lab.corridor import corridor_mask, cumulative_cost_distance, least_cost_path
from bobcat_corridor_lab.io import load_array
from bobcat_corridor_lab.workflow import run_demo_workflow, run_multipatch_workflow, run_real_workflow


def test_cumulative_cost_and_path_on_simple_grid():
    cost = np.ones((5, 5), dtype=float)
    source = (0, 0)
    target = (4, 4)

    cumulative = cumulative_cost_distance(cost, source)
    path = least_cost_path(cumulative, source, target)

    assert path[0] == source
    assert path[-1] == target
    assert len(path) >= 5


def test_corridor_mask_quantile_returns_boolean_grid():
    cumulative = np.arange(25, dtype=float).reshape(5, 5)
    mask = corridor_mask(cumulative, 0.2)
    assert mask.dtype == bool
    assert int(mask.sum()) >= 1


def test_run_demo_workflow_writes_artifacts(tmp_path):
    scenario = DemoScenario(
        raster_shape=(50, 60),
        random_seed=10,
        suitability_weights=SuitabilityWeights(0.4, 0.2, 0.15, 0.15, 0.1),
        barrier_costs=BarrierCosts(10.0, 8.0, 3.0),
        corridor_quantile=0.1,
    )

    summary = run_demo_workflow(scenario, tmp_path)

    assert "corridor_cells" in summary
    assert (tmp_path / "suitability.npy").exists()
    assert (tmp_path / "resistance.npy").exists()
    assert (tmp_path / "cumulative_cost.npy").exists()
    assert (tmp_path / "least_cost_path.csv").exists()

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["rows"] == 50
    assert payload["cols"] == 60


def test_load_array_reads_npy(tmp_path):
    arr = np.arange(9, dtype=float).reshape(3, 3)
    path = tmp_path / "grid.npy"
    np.save(path, arr)

    loaded = load_array(path)
    np.testing.assert_allclose(loaded, arr)


def test_load_array_reads_npz(tmp_path):
    arr = np.arange(6, dtype=float).reshape(2, 3)
    path = tmp_path / "grid.npz"
    np.savez(path, main=arr)

    loaded = load_array(path)
    np.testing.assert_allclose(loaded, arr)


def test_run_real_workflow_writes_artifacts(tmp_path):
    scenario = DemoScenario(
        raster_shape=(20, 30),
        random_seed=10,
        suitability_weights=SuitabilityWeights(0.4, 0.2, 0.15, 0.15, 0.1),
        barrier_costs=BarrierCosts(10.0, 8.0, 3.0),
        corridor_quantile=0.1,
    )

    layer_dir = tmp_path / "layers"
    layer_dir.mkdir()

    shape = (20, 30)
    np.save(layer_dir / "land_cover.npy", np.random.default_rng(1).random(shape))
    np.save(layer_dir / "water.npy", np.random.default_rng(2).random(shape))
    np.save(layer_dir / "slope.npy", np.random.default_rng(3).random(shape))
    np.save(layer_dir / "human.npy", np.random.default_rng(4).random(shape))
    np.save(layer_dir / "prey.npy", np.random.default_rng(5).random(shape))

    road = np.zeros(shape, dtype=np.uint8)
    road[:, 10] = 1
    urban = np.zeros(shape, dtype=np.uint8)
    urban[3:8, 20:26] = 1
    ag = np.zeros(shape, dtype=np.uint8)
    ag[10:16, 3:9] = 1

    np.save(layer_dir / "road.npy", road)
    np.save(layer_dir / "urban.npy", urban)
    np.save(layer_dir / "ag.npy", ag)

    summary = run_real_workflow(
        scenario=scenario,
        output_dir=tmp_path / "out",
        layer_paths={
            "land_cover": layer_dir / "land_cover.npy",
            "water_distance": layer_dir / "water.npy",
            "slope": layer_dir / "slope.npy",
            "human_footprint": layer_dir / "human.npy",
            "prey": layer_dir / "prey.npy",
        },
        barrier_paths={
            "road": layer_dir / "road.npy",
            "urban": layer_dir / "urban.npy",
            "agriculture": layer_dir / "ag.npy",
        },
        source=(1, 1),
        target=(18, 27),
    )

    assert summary["mode"] == "real"
    assert (tmp_path / "out" / "summary.json").exists()
    assert (tmp_path / "out" / "cumulative_cost.npy").exists()


def test_run_multipatch_workflow_generates_pair_outputs(tmp_path):
    scenario = DemoScenario(
        raster_shape=(20, 20),
        random_seed=20,
        suitability_weights=SuitabilityWeights(0.4, 0.2, 0.15, 0.15, 0.1),
        barrier_costs=BarrierCosts(10.0, 8.0, 3.0),
        corridor_quantile=0.1,
    )

    layer_dir = tmp_path / "layers"
    layer_dir.mkdir()
    shape = (20, 20)
    rng = np.random.default_rng(12)

    np.save(layer_dir / "land_cover.npy", rng.random(shape))
    np.save(layer_dir / "water.npy", rng.random(shape))
    np.save(layer_dir / "slope.npy", rng.random(shape))
    np.save(layer_dir / "human.npy", rng.random(shape))

    np.save(layer_dir / "road.npy", np.zeros(shape, dtype=np.uint8))
    np.save(layer_dir / "urban.npy", np.zeros(shape, dtype=np.uint8))
    np.save(layer_dir / "ag.npy", np.zeros(shape, dtype=np.uint8))

    patches = np.zeros(shape, dtype=np.int32)
    patches[2:4, 2:4] = 1
    patches[8:10, 8:10] = 2
    patches[15:17, 15:17] = 3
    np.save(layer_dir / "patches.npy", patches)

    summary = run_multipatch_workflow(
        scenario=scenario,
        output_dir=tmp_path / "multi_out",
        layer_paths={
            "land_cover": layer_dir / "land_cover.npy",
            "water_distance": layer_dir / "water.npy",
            "slope": layer_dir / "slope.npy",
            "human_footprint": layer_dir / "human.npy",
        },
        barrier_paths={
            "road": layer_dir / "road.npy",
            "urban": layer_dir / "urban.npy",
            "agriculture": layer_dir / "ag.npy",
        },
        patch_raster_path=layer_dir / "patches.npy",
    )

    assert summary["mode"] == "multipatch"
    assert summary["pair_count"] == 3
    assert (tmp_path / "multi_out" / "multipatch_summary.json").exists()
    assert (tmp_path / "multi_out" / "patch_1_to_2" / "summary.json").exists()
