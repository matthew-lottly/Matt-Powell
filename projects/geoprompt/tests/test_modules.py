"""Tests for validation, config, plugins, normalization, and sensitivity modules."""

from __future__ import annotations

import pytest

from geoprompt.config import GeoPromptConfig, load_config
from geoprompt.exceptions import CRSError, ConfigError, PluginError, ValidationError
from geoprompt.normalization import (
    apply_negative_weight_policy,
    normalize,
    normalize_min_max,
    normalize_robust,
    normalize_z_score,
)
from geoprompt.plugins import (
    exponential_decay,
    gaussian_decay,
    get_decay,
    get_kernel,
    inverse_power_decay,
    linear_decay,
    list_decay_functions,
    list_kernels,
    register_decay,
    register_kernel,
)
from geoprompt.sensitivity import confidence_score, parameter_sweep, rank_with_confidence
from geoprompt.validation import (
    SCHEMA_VERSION,
    add_schema_version,
    safe_weight,
    validate_crs,
    validate_distance_method_crs,
    validate_non_empty_features,
    validate_required_columns,
)


class TestValidation:
    def test_schema_version_present(self) -> None:
        assert isinstance(SCHEMA_VERSION, str)
        assert len(SCHEMA_VERSION.split(".")) == 3

    def test_add_schema_version(self) -> None:
        result = add_schema_version({"key": "value"})
        assert result["schema_version"] == SCHEMA_VERSION

    def test_safe_weight_none(self) -> None:
        assert safe_weight(None) == 0.0

    def test_safe_weight_value(self) -> None:
        assert safe_weight(3.14) == 3.14

    def test_validate_crs_missing_required(self) -> None:
        from geoprompt.exceptions import CRSError
        with pytest.raises(CRSError, match="not set"):
            validate_crs(None, require=True)

    def test_validate_crs_empty(self) -> None:
        from geoprompt.exceptions import CRSError
        with pytest.raises(CRSError, match="non-empty"):
            validate_crs("", require=False)

    def test_validate_distance_method_crs_requires_4326_for_haversine(self) -> None:
        with pytest.raises(CRSError, match="EPSG:4326"):
            validate_distance_method_crs("haversine", "EPSG:3857")

    def test_validate_distance_method_crs_requires_crs_for_haversine(self) -> None:
        with pytest.raises(CRSError, match="requires CRS"):
            validate_distance_method_crs("haversine", None)

    def test_validate_distance_method_crs_accepts_haversine_for_4326(self) -> None:
        validate_distance_method_crs("haversine", "EPSG:4326")


class TestConfig:
    def test_default_config(self) -> None:
        config = GeoPromptConfig()
        assert config.crs == "EPSG:4326"
        assert config.top_n == 5

    def test_load_missing_config_returns_default(self) -> None:
        config = load_config()
        assert isinstance(config, GeoPromptConfig)

    def test_load_nonexistent_file_raises(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_config("/nonexistent/path/geoprompt.toml")

    def test_load_config_from_toml(self, tmp_path) -> None:
        config_path = tmp_path / "geoprompt.toml"
        config_path.write_text('[geoprompt]\nscale = 0.25\ntop_n = 10\n', encoding="utf-8")
        config = load_config(config_path)
        assert config.scale == 0.25
        assert config.top_n == 10


class TestNormalization:
    def test_min_max_basic(self) -> None:
        result = normalize_min_max([1.0, 2.0, 3.0])
        assert result[0] == 0.0
        assert result[-1] == 1.0

    def test_min_max_constant(self) -> None:
        result = normalize_min_max([5.0, 5.0, 5.0])
        assert all(v == 0.5 for v in result)

    def test_z_score_basic(self) -> None:
        result = normalize_z_score([1.0, 2.0, 3.0])
        assert abs(sum(result)) < 1e-9  # Mean should be ~0

    def test_robust_basic(self) -> None:
        result = normalize_robust([1.0, 2.0, 3.0, 4.0, 5.0, 100.0])
        assert isinstance(result, list)

    def test_unknown_method_raises(self) -> None:
        with pytest.raises(ValidationError, match="Unknown"):
            normalize([1.0], method="unknown")

    def test_negative_reject(self) -> None:
        with pytest.raises(ValidationError, match="Negative"):
            apply_negative_weight_policy([-1.0, 1.0], policy="reject")

    def test_negative_clip(self) -> None:
        result = apply_negative_weight_policy([-1.0, 1.0], policy="clip")
        assert result == [0.0, 1.0]

    def test_negative_allow(self) -> None:
        result = apply_negative_weight_policy([-1.0, 1.0], policy="allow")
        assert result == [-1.0, 1.0]

    def test_empty_values(self) -> None:
        assert normalize_min_max([]) == []
        assert normalize_z_score([]) == []
        assert normalize_robust([]) == []


class TestPlugins:
    def test_inverse_power_decay(self) -> None:
        result = inverse_power_decay(0.0, scale=1.0, power=2.0)
        assert result == 1.0

    def test_gaussian_decay(self) -> None:
        result = gaussian_decay(0.0)
        assert result == 1.0

    def test_exponential_decay(self) -> None:
        result = exponential_decay(0.0)
        assert result == 1.0

    def test_linear_decay_at_scale(self) -> None:
        result = linear_decay(1.0, scale=1.0)
        assert result == 0.0

    def test_linear_decay_beyond_scale(self) -> None:
        result = linear_decay(2.0, scale=1.0)
        assert result == 0.0

    def test_get_decay(self) -> None:
        fn = get_decay("inverse_power")
        assert callable(fn)

    def test_get_unknown_decay_raises(self) -> None:
        with pytest.raises(PluginError, match="Unknown"):
            get_decay("nonexistent")

    def test_list_decay_functions(self) -> None:
        names = list_decay_functions()
        assert "inverse_power" in names
        assert "gaussian" in names

    def test_list_kernels(self) -> None:
        names = list_kernels()
        assert "weighted" in names


class TestSensitivity:
    def test_confidence_score_max(self) -> None:
        assert confidence_score(1.0, 1.0) == 1.0

    def test_confidence_score_zero(self) -> None:
        assert confidence_score(0.0, 1.0) == 0.0

    def test_confidence_score_zero_max(self) -> None:
        assert confidence_score(1.0, 0.0) == 0.0

    def test_rank_with_confidence(self) -> None:
        items = [{"interaction": 10.0}, {"interaction": 5.0}, {"interaction": 2.0}]
        ranked = rank_with_confidence(items)
        assert ranked[0]["rank"] == 1
        assert ranked[0]["confidence"] == 1.0
        assert ranked[1]["confidence"] == 0.5

    def test_parameter_sweep(self) -> None:
        def compute(scale: float, power: float) -> list[float]:
            from geoprompt.equations import prompt_decay
            return [prompt_decay(d, scale=scale, power=power) for d in [0.1, 0.5, 1.0]]

        results = parameter_sweep(compute, {"scale": [0.1, 0.5], "power": [1.0, 2.0]})
        assert len(results) == 4
        assert all(r.metric_summary["count"] == 3.0 for r in results)
