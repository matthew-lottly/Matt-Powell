"""Benchmark the sample 3D-VP-LCP pipeline run."""

from __future__ import annotations

from pathlib import Path

from vp_lcp.config import PipelineConfig
from vp_lcp.pipeline import run_pipeline


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    sample_path = project_root / "data" / "sample_lidar.las"
    output_dir = project_root / "outputs" / "sample-benchmark"
    config = PipelineConfig()
    config.output.output_dir = str(output_dir)
    config.output.export_surface = True
    result = run_pipeline(sample_path, config)
    print(f"Benchmark complete in {result.runtime_seconds:.3f}s")
    print(f"Path voxels: {result.path_voxel_count}")
    print(f"Output: {result.output_dir}")


if __name__ == "__main__":
    main()
