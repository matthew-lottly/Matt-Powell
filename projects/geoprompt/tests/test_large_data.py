from __future__ import annotations

from pathlib import Path

import pytest

from geoprompt.io import read_features_chunked


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_chunked_reader_yields_expected_chunks() -> None:
    chunks = list(read_features_chunked(PROJECT_ROOT / "data" / "sample_features.json", chunk_size=2, crs="EPSG:4326"))
    assert [len(chunk) for chunk in chunks] == [2, 2, 2]
    assert all(chunk.crs == "EPSG:4326" for chunk in chunks)


def test_chunked_reader_rejects_non_positive_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        list(read_features_chunked(PROJECT_ROOT / "data" / "sample_features.json", chunk_size=0))