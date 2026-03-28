import sys
import os

sys.path.insert(0, os.path.abspath("_strata_temp/src"))

from hetero_conformal.meta_calibrator import MetaCalibrator
from hetero_conformal.advanced_calibrators import AttentionCalibrator


def test_meta_calibrator_import_and_api():
    mc = MetaCalibrator(alpha=0.1)
    assert hasattr(mc, "calibrate")
    assert hasattr(mc, "predict")


def test_attention_calibrator_import_and_api():
    ac = AttentionCalibrator(alpha=0.1)
    # AttentionCalibrator follows the same API: calibrate() then predict()
    assert hasattr(ac, "calibrate")
    assert hasattr(ac, "predict")
