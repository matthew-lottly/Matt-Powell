"""Comparison and property tests for tools 441-520."""

import random

import numpy as np
import pytest

from geoprompt import GeoPromptFrame


def _pt_frame(coords, **extra):
    rows = []
    for index, (x_coord, y_coord) in enumerate(coords):
        record = {
            "site_id": f"p{index}",
            "geometry": {"type": "Point", "coordinates": [float(x_coord), float(y_coord)]},
        }
        for key, values in extra.items():
            record[key] = values[index]
        rows.append(record)
    return GeoPromptFrame.from_records(rows, crs="EPSG:4326")


def _make_regression_frame(n_points: int = 80, seed: int = 42):
    rng = random.Random(seed)
    records = []
    for _ in range(n_points):
        x_coord = rng.uniform(-4.0, 4.0)
        y_coord = rng.uniform(-4.0, 4.0)
        f1 = x_coord + rng.gauss(0.0, 0.15)
        f2 = y_coord + rng.gauss(0.0, 0.15)
        f3 = 0.5 * x_coord - 0.25 * y_coord + rng.gauss(0.0, 0.1)
        target = 4.0 * f1 - 2.5 * f2 + 1.75 * f3 + rng.gauss(0.0, 0.2)
        records.append({
            "geometry": {"type": "Point", "coordinates": [x_coord, y_coord]},
            "f1": round(f1, 6),
            "f2": round(f2, 6),
            "f3": round(f3, 6),
            "target": round(target, 6),
        })
    frame = GeoPromptFrame.from_records(records, crs="EPSG:4326")
    return frame, records


class TestSpatialElasticNetComparison:

    def test_predictions_track_sklearn(self):
        sklearn = pytest.importorskip("sklearn")
        from sklearn.linear_model import ElasticNet
        from sklearn.metrics import r2_score

        frame, records = _make_regression_frame(90, seed=7)
        features = ["f1", "f2", "f3"]
        x_matrix = np.array([[float(record[col]) for col in features] for record in records])
        targets = np.array([float(record["target"]) for record in records])

        result = frame.spatial_elastic_net(features, "target", alpha=0.05, l1_ratio=0.4, epochs=400)
        our_predictions = np.array(result["predicted_sen"])

        reference = ElasticNet(alpha=0.05, l1_ratio=0.4, fit_intercept=True, max_iter=5000, tol=1e-6)
        reference.fit(x_matrix, targets)
        ref_predictions = reference.predict(x_matrix)

        assert r2_score(targets, our_predictions) > 0.95
        corr = float(np.corrcoef(our_predictions, ref_predictions)[0, 1])
        assert corr > 0.98, f"ElasticNet prediction correlation = {corr:.3f}"


class TestSpatialDBSCANComparison:

    def test_cluster_assignment_parity(self):
        sklearn = pytest.importorskip("sklearn")
        from sklearn.cluster import DBSCAN as SkDBSCAN

        rng = np.random.default_rng(21)
        cluster_a = rng.normal(loc=[0.0, 0.0], scale=0.35, size=(18, 2))
        cluster_b = rng.normal(loc=[5.0, 5.0], scale=0.45, size=(18, 2))
        all_points = np.vstack([cluster_a, cluster_b])
        coords = [(float(point[0]), float(point[1])) for point in all_points]

        frame = _pt_frame(coords)
        result = frame.spatial_dbscan_clustering(epsilon=1.1, min_points=4)
        our_labels = result["cluster_dbs"]

        ref_labels = SkDBSCAN(eps=1.1, min_samples=4).fit(all_points).labels_

        our_clusters = {label for label in our_labels if label != -1}
        ref_clusters = {int(label) for label in ref_labels if int(label) != -1}
        assert len(our_clusters) == len(ref_clusters)
        for left in range(len(coords)):
            for right in range(left + 1, len(coords)):
                our_same = our_labels[left] == our_labels[right] and our_labels[left] != -1
                ref_same = int(ref_labels[left]) == int(ref_labels[right]) and int(ref_labels[left]) != -1
                assert our_same == ref_same, f"DBSCAN mismatch at ({left}, {right})"


class TestSpatialConformalPredictor:

    def test_empirical_coverage_is_reasonable(self):
        frame, records = _make_regression_frame(96, seed=19)
        result = frame.spatial_conformal_predictor(
            ["f1", "f2", "f3"],
            "target",
            calibration_fraction=0.25,
            k_neighbors=6,
            alpha=0.2,
        )
        lowers = result["lower_scp"]
        uppers = result["upper_scp"]
        actuals = [float(record["target"]) for record in records]
        covered = [lower <= actual <= upper for lower, upper, actual in zip(lowers, uppers, actuals)]
        coverage = sum(covered) / len(covered)
        assert coverage >= 0.72, f"Coverage too low: {coverage:.3f}"
        widths = result["interval_width_scp"]
        assert all(width >= 0 for width in widths)
        assert sum(widths) / len(widths) > 0


class TestSpatialOptimalTransport:

    def test_transport_preserves_mass(self):
        coords = [(0.0, 0.0), (1.0, 0.5), (2.0, 0.0), (3.0, 0.5)]
        masses = [1.0, 2.0, 3.0, 4.0]
        frame = _pt_frame(coords, mass=masses)

        result = frame.spatial_optimal_transport("mass", reg=0.8, n_iterations=50)
        transport_mass = result["transport_mass_sot"]
        total_mass = sum(masses)
        expected = [mass / total_mass for mass in masses]

        for observed, target in zip(transport_mass, expected):
            assert abs(observed - target) < 1e-4, f"Transport mass mismatch: {observed} vs {target}"
        assert abs(sum(transport_mass) - 1.0) < 1e-4


class TestSpatialHDBSCAN:

    def test_variable_density_clusters_remain_separate(self):
        rng = np.random.default_rng(123)
        dense = rng.normal(loc=[0.0, 0.0], scale=0.12, size=(12, 2))
        sparse = rng.normal(loc=[4.5, 4.5], scale=0.55, size=(12, 2))
        noise = np.array([[10.0, 10.0], [11.0, 10.5], [9.5, 11.0]])
        all_points = np.vstack([dense, sparse, noise])
        coords = [(float(point[0]), float(point[1])) for point in all_points]

        frame = _pt_frame(coords)
        result = frame.spatial_hdbscan(min_cluster_size=4, min_samples=3)
        labels = result["cluster_hdb"]

        dense_labels = [labels[index] for index in range(12)]
        sparse_labels = [labels[index] for index in range(12, 24)]

        dense_main = max((label for label in set(dense_labels) if label != -1), key=dense_labels.count)
        sparse_main = max((label for label in set(sparse_labels) if label != -1), key=sparse_labels.count)

        assert dense_main != sparse_main
        assert dense_labels.count(dense_main) >= 10
        assert sparse_labels.count(sparse_main) >= 9