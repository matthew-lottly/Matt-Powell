import geoprompt.compare as compare
import time


def test_comparison_report_registers_441_520_benchmarks() -> None:
    original_benchmark = compare._benchmark
    compare._benchmark = lambda operation, func, repeats=20: ({"operation": operation, "repeats": 1}, None)
    try:
        report = compare.build_comparison_report()
    finally:
        compare._benchmark = original_benchmark

    benchmark_ops = {
        str(benchmark["operation"])
        for dataset in report["datasets"]
        for benchmark in dataset["benchmarks"]
    }

    assert "sample.geoprompt.spatial_elastic_net" in benchmark_ops
    assert "sample.geoprompt.spatial_dbscan_clustering" in benchmark_ops
    assert "sample.geoprompt.spatial_hdbscan" in benchmark_ops
    assert "sample.geoprompt.spatial_optimal_transport" in benchmark_ops
    assert "sample.geoprompt.spatial_conformal_predictor" in benchmark_ops


def test_comparison_report_441_520_benchmark_budgets() -> None:
    target_operations = {
        "sample.geoprompt.spatial_elastic_net",
        "sample.geoprompt.spatial_dbscan_clustering",
        "sample.geoprompt.spatial_hdbscan",
        "sample.geoprompt.spatial_optimal_transport",
        "sample.geoprompt.spatial_conformal_predictor",
    }

    def single_run_benchmark(operation, func, repeats=20):
        started_at = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - started_at
        return (
            {
                "operation": operation,
                "median_seconds": elapsed,
                "min_seconds": elapsed,
                "max_seconds": elapsed,
                "repeats": 1,
            },
            result,
        )

    original_benchmark = compare._benchmark
    compare._benchmark = single_run_benchmark
    try:
        report = compare.build_comparison_report(
            benchmark_filter=lambda operation: operation in target_operations,
        )
    finally:
        compare._benchmark = original_benchmark

    benchmark_timings = {
        str(benchmark["operation"]): float(benchmark.get("median_seconds", 0.0) or 0.0)
        for dataset in report["datasets"]
        for benchmark in dataset["benchmarks"]
    }

    assert set(benchmark_timings) == target_operations
    assert benchmark_timings["sample.geoprompt.spatial_elastic_net"] < 0.02
    assert benchmark_timings["sample.geoprompt.spatial_dbscan_clustering"] < 0.01
    assert benchmark_timings["sample.geoprompt.spatial_hdbscan"] < 0.01
    assert benchmark_timings["sample.geoprompt.spatial_optimal_transport"] < 0.02
    assert benchmark_timings["sample.geoprompt.spatial_conformal_predictor"] < 0.02