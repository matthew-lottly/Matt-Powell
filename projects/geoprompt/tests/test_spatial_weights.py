"""Tests for SpatialWeights class (P4)."""
from __future__ import annotations

import pytest
from geoprompt import GeoPromptFrame, SpatialWeights


def _line_frame(n: int = 10) -> GeoPromptFrame:
    return GeoPromptFrame.from_records([
        {"site_id": f"p{i}", "geometry": {"type": "Point", "coordinates": (float(i), 0.0)}}
        for i in range(n)
    ])


class TestSpatialWeightsKNN:
    def test_basic_knn(self):
        frame = _line_frame(5)
        w = SpatialWeights.from_knn(frame, k=2)
        assert w.n == 5
        nbs = w.neighbors_of(0)
        assert len(nbs) == 2
        assert nbs[0][0] == 1  # closest neighbor of p0 is p1

    def test_k_exceeds_n(self):
        frame = _line_frame(3)
        w = SpatialWeights.from_knn(frame, k=10)
        assert len(w.neighbors_of(0)) == 2  # only 2 others

    def test_repr(self):
        w = SpatialWeights.from_knn(_line_frame(4), k=2)
        assert "SpatialWeights" in repr(w)
        assert "n=4" in repr(w)


class TestSpatialWeightsDistanceBand:
    def test_basic_band(self):
        frame = _line_frame(5)
        w = SpatialWeights.from_distance_band(frame, max_distance=1.5)
        nbs0 = w.neighbors_of(0)
        assert len(nbs0) == 1  # only p1 within 1.5
        nbs2 = w.neighbors_of(2)
        assert len(nbs2) == 2  # p1 and p3 within 1.5

    def test_large_band_gets_all(self):
        frame = _line_frame(4)
        w = SpatialWeights.from_distance_band(frame, max_distance=100)
        assert len(w.neighbors_of(0)) == 3


class TestSpatialWeightsTransform:
    def test_row_standardize(self):
        w = SpatialWeights.from_knn(_line_frame(5), k=2)
        wr = w.transform("R")
        for i in range(5):
            total = sum(wt for _, wt in wr.neighbors_of(i))
            assert total == pytest.approx(1.0, abs=1e-9)

    def test_binary(self):
        w = SpatialWeights.from_knn(_line_frame(5), k=2)
        wb = w.transform("B")
        for i in range(5):
            for _, wt in wb.neighbors_of(i):
                assert wt == 1.0

    def test_inverse_distance(self):
        w = SpatialWeights.from_knn(_line_frame(5), k=2)
        wd = w.transform("D")
        nbs = wd.neighbors_of(0)
        assert nbs[0][1] == pytest.approx(1.0)  # 1/1.0
        assert nbs[1][1] == pytest.approx(0.5)  # 1/2.0

    def test_invalid_mode(self):
        w = SpatialWeights.from_knn(_line_frame(3), k=1)
        with pytest.raises(ValueError):
            w.transform("X")


class TestSpatialWeightsDense:
    def test_to_dense(self):
        w = SpatialWeights.from_knn(_line_frame(3), k=1)
        mat = w.to_dense()
        assert len(mat) == 3
        assert len(mat[0]) == 3

    def test_to_dict(self):
        w = SpatialWeights.from_knn(_line_frame(3), k=1)
        d = w.to_dict()
        assert isinstance(d, dict)
        assert 0 in d
