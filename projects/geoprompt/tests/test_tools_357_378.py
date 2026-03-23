"""Tests for tools 357-378."""

import pytest
from geoprompt import GeoPromptFrame

# ── helpers ──────────────────────────────────────────────────────────

def _col(n, name="v", vals=None):
    rows = []
    for i in range(n):
        rows.append({
            "geometry": {"type": "Point", "coordinates": (float(i), float(i % 3))},
            name: vals[i] if vals else float(i),
        })
    return GeoPromptFrame(rows)


def _grid_frame(side=4, col="elev"):
    """side×side grid with elevation = x + y."""
    rows = []
    for y in range(side):
        for x in range(side):
            rows.append({
                "geometry": {"type": "Point", "coordinates": (float(x), float(y))},
                col: float(x + y),
            })
    return GeoPromptFrame(rows)


def _cat_frame(n=20):
    rows = []
    for i in range(n):
        rows.append({
            "geometry": {"type": "Point", "coordinates": (float(i), float(i % 5))},
            "cat": "A" if i % 3 == 0 else "B",
        })
    return GeoPromptFrame(rows)


def _regression_frame(n=20):
    rows = []
    for i in range(n):
        x = float(i)
        y = 2.0 * x + 1.0 + (i % 3) * 0.1
        rows.append({
            "geometry": {"type": "Point", "coordinates": (float(i), float(i % 4))},
            "x1": x,
            "y_val": y,
        })
    return GeoPromptFrame(rows)


# ── tests ────────────────────────────────────────────────────────────

class TestTool357JoinCountReview:
    def test_basic(self):
        gf = _cat_frame()
        out = gf.join_count_review("cat")
        r = out.to_records()[0]
        assert "bb_directed_jcrev" in r
        assert "bw_undirected_jcrev" in r
        assert r["k_jcrev"] == 5


class TestTool358LoshReview:
    def test_basic(self):
        gf = _col(15)
        out = gf.losh_review("v")
        r = out.to_records()[0]
        assert "losh_lrev" in r
        assert "heteroscedastic_lrev" in r


class TestTool359BivariateMoranReview:
    def test_basic(self):
        gf = _regression_frame()
        out = gf.bivariate_moran_review("x1", "y_val")
        r = out.to_records()[0]
        assert "biv_moran_bmrev" in r
        assert "pearson_bmrev" in r


class TestTool360SpatialLagReview:
    def test_basic(self):
        gf = _regression_frame()
        out = gf.spatial_lag_review("y_val", "x1")
        r = out.to_records()[0]
        assert "rho_slrev" in r
        assert "spatial_dependence_slrev" in r


class TestTool361GwrReview:
    def test_basic(self):
        gf = _regression_frame()
        out = gf.gwr_review("y_val", "x1")
        r = out.to_records()[0]
        assert "local_r2_gwrev" in r
        assert "intercept_gwrev" in r


class TestTool362ModelComparisonReview:
    def test_basic(self):
        gf = _regression_frame()
        out = gf.model_comparison_review("y_val", "x1")
        r = out.to_records()[0]
        assert "aic_mcrev" in r
        assert "bic_mcrev" in r
        assert r["n_predictors_mcrev"] == 1


class TestTool363UniversalKrigingReview:
    def test_basic(self):
        gf = _grid_frame()
        out = gf.universal_kriging_review("elev")
        r = out.to_records()[0]
        assert "trend_r2_ukrev" in r
        assert "drift_significant_ukrev" in r


class TestTool364CokrigingReview:
    def test_basic(self):
        rows = []
        for i in range(15):
            rows.append({
                "geometry": {"type": "Point", "coordinates": (float(i), float(i % 3))},
                "primary": float(i),
                "secondary": float(i * 0.5 + 1),
            })
        gf = GeoPromptFrame(rows)
        out = gf.cokriging_review("primary", "secondary")
        r = out.to_records()[0]
        assert "cross_gamma_ckrev" in r
        assert "cross_corr_ckrev" in r


class TestTool365EbkReview:
    def test_basic(self):
        gf = _col(20)
        out = gf.ebk_review("v")
        r = out.to_records()[0]
        assert "subset_var_ebkrev" in r
        assert "var_of_means_ebkrev" in r


class TestTool366ContourReview:
    def test_basic(self):
        gf = _grid_frame()
        out = gf.contour_review("elev")
        r = out.to_records()[0]
        assert "n_contours_ctrev" in r
        assert r["n_levels_ctrev"] == 5


class TestTool367FlowDirectionReview:
    def test_basic(self):
        gf = _grid_frame()
        out = gf.flow_direction_review("elev")
        r = out.to_records()[0]
        assert "valid_d8_fdrev" in r
        assert "pit_count_fdrev" in r


class TestTool368AccumulationReview:
    def test_basic(self):
        gf = _grid_frame()
        out = gf.accumulation_review("elev")
        r = out.to_records()[0]
        assert "max_accumulation_accrev" in r
        assert "n_outlets_accrev" in r


class TestTool369WatershedReview:
    def test_basic(self):
        gf = _grid_frame()
        out = gf.watershed_review("elev")
        r = out.to_records()[0]
        assert "n_basins_wsrev" in r
        assert "coverage_pct_wsrev" in r


class TestTool370StreamOrderReview:
    def test_basic(self):
        gf = _grid_frame(side=5)
        out = gf.stream_order_review("elev", threshold=2)
        r = out.to_records()[0]
        assert "max_order_sorev" in r
        assert "n_stream_cells_sorev" in r


class TestTool371TwiLsHandReview:
    def test_basic(self):
        gf = _grid_frame()
        out = gf.twi_ls_hand_review("elev")
        r = out.to_records()[0]
        assert "twi_min_tlhrev" in r
        assert "hand_max_tlhrev" in r


class TestTool372BoundingShapeReview:
    def test_basic(self):
        gf = _col(10)
        out = gf.bounding_shape_review()
        r = out.to_records()[0]
        assert "envelope_area_bsrev" in r
        assert "hull_area_bsrev" in r


class TestTool373HausdorffReview:
    def test_basic(self):
        gf = _col(10)
        out = gf.hausdorff_review()
        r = out.to_records()[0]
        assert "hausdorff_hdrev" in r
        assert r["hausdorff_hdrev"] >= 0


class TestTool374FormatFidelityReview:
    def test_basic(self):
        gf = _col(5)
        out = gf.format_fidelity_review()
        r = out.to_records()[0]
        assert r["roundtrip_pct_ffrev"] > 0


class TestTool375MethodChainAudit:
    def test_basic(self):
        gf = _col(5)
        out = gf.method_chain_audit("v")
        r = out.to_records()[0]
        assert r["chain_ok_mca"] == 1


class TestTool376StructuredLog:
    def test_basic(self):
        gf = _col(3)
        out = gf.structured_log("test message")
        r = out.to_records()[0]
        assert r["log_msg_slog"] == "test message"
        assert r["log_level_slog"] == "info"


class TestTool377ProgressCallback:
    def test_basic(self):
        gf = _col(1)
        out = gf.progress_callback("test_op", n_steps=5)
        recs = out.to_records()
        assert len(recs) == 5
        assert recs[-1]["status_prog"] == "complete"


class TestTool378ExceptionEnriched:
    def test_basic(self):
        gf = _col(5)
        out = gf.exception_enriched()
        r = out.to_records()[0]
        assert "health_exc" in r
        assert r["n_rows_exc"] == 5
