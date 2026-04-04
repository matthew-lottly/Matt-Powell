# Future Work And Outputs

This backlog lists concrete next steps and the artifacts each step should produce. The goal is to keep the project oriented toward measurable 3D connectivity quality, cross-site robustness, and decision-useful outputs.

Current status update:
- Item 39 is now implemented by [src/vp_lcp/scripts/reproduce_recommended_baseline.py](../src/vp_lcp/scripts/reproduce_recommended_baseline.py).
- Item 41 is now implemented by [.github/workflows/benchmark-smoke.yml](../.github/workflows/benchmark-smoke.yml).
- Item 42 is now implemented by [tests/test_three_d_summary_golden.py](../tests/test_three_d_summary_golden.py) and [tests/golden/three_d_summary_expected/three_d_summary.json](../tests/golden/three_d_summary_expected/three_d_summary.json).
- Item 43 is now implemented by [src/vp_lcp/scripts/check_performance_thresholds.py](../src/vp_lcp/scripts/check_performance_thresholds.py), [configs/smoke_performance_thresholds.json](../configs/smoke_performance_thresholds.json), and CI wiring in [.github/workflows/benchmark-smoke.yml](../.github/workflows/benchmark-smoke.yml).

## Backlog

1. Add a larger East Coast baseline site. Output: one new public tile manifest and one benchmark result set.
2. Add a Pacific Northwest baseline site. Output: one new manifest and one cross-site comparison row.
3. Add a desert or sparse-canopy baseline site. Output: one benchmark root showing failure and recovery behavior.
4. Add a mountainous site with strong elevation gradients. Output: one stress-test summary focused on vertical spread.
5. Add a wetland or riparian site. Output: one ecological contrast benchmark package.
6. Build a curated benchmark registry. Output: one markdown index of all supported public datasets.
7. Record dataset provenance more explicitly. Output: one machine-readable dataset catalog with source metadata.
8. Validate manifests with a schema. Output: one manifest validation command and tests.
9. Add checksum refresh tooling. Output: one script that recomputes or verifies manifest hashes.
10. Support multi-tile mosaics. Output: one merged-input benchmark example and report.
11. Add clipped AOI benchmarking. Output: one benchmark mode that uses polygon boundaries consistently.
12. Add terrain-normalized height options. Output: one comparison report showing canopy-relative vs raw height behavior.
13. Compare more voxel sizes around the new default. Output: one sensitivity table for `2.5`, `3.0`, and `3.5` meter voxels.
14. Compare `dijkstra` and `astar` under strict gating on more sites. Output: one algorithm tradeoff summary.
15. Explore additional neighborhood definitions. Output: one benchmark extension and one ranking report.
16. Add automated parameter sweeps around species thresholds. Output: one species-threshold sensitivity matrix.
17. Calibrate stratum weights with real scenes. Output: one stratum-weight ablation report.
18. Add richer resistance normalization options. Output: one normalization comparison artifact.
19. Track graph density metrics across runs. Output: one CSV with node, edge, and density summaries.
20. Add corridor tortuosity metrics. Output: one report with straight-line ratio and path complexity.
21. Add vertical transition counts. Output: one summary showing upward, downward, and flat steps per run.
22. Add corridor width statistics by segment. Output: one width-profile CSV and plot-ready export.
23. Add patch separation distance reporting. Output: one source-target geometry summary per run.
24. Add corridor volume estimates. Output: one voxel-volume summary artifact.
25. Add per-height-band resistance summaries. Output: one table linking corridor resistance to height strata.
26. Add ecological confidence tiers. Output: one run label such as low, moderate, or high confidence.
27. Add benchmark stability scoring across reruns. Output: one reproducibility report with variance metrics.
28. Add bootstrap or resampling analysis for corridor robustness. Output: one uncertainty summary per site.
29. Add a benchmark leaderboard markdown page. Output: one human-readable ranked report across all sites.
30. Add a site-level scorecard template. Output: one reusable markdown scorecard for each dataset.
31. Generate plan-view corridor maps automatically. Output: one image per run with source, target, and corridor overlay.
32. Generate vertical profile figures automatically. Output: one profile image per informative run.
33. Generate XY plus Z small-multiple figures. Output: one compact visual bundle for each benchmark root.
34. Add height-band stacked bar charts. Output: one plot-ready CSV and one rendered figure.
35. Add run-to-run delta reports. Output: one markdown diff summary comparing candidate config changes to baseline.
36. Add JSON schema for `run_report.json`. Output: one schema file and validation tests.
37. Add JSON schema for `three_d_summary.json`. Output: one schema file and validation tests.
38. Build a consolidated artifact manifest for each output root. Output: one `artifacts.json` file per benchmark root.
39. Add a one-command baseline reproduction script. Output: one script that downloads, runs, and summarizes the preferred baseline set.
40. Add a one-command cross-site ranking script. Output: one reproducible pipeline wrapper for benchmark aggregation.
41. Add CI smoke tests for benchmarking scripts. Output: one lightweight automation job covering core CLI flows.
42. Add golden-file tests for summary outputs. Output: one set of stable expected summary fixtures.
43. Add performance regression thresholds. Output: one automated check that flags slower-than-baseline runs.
44. Add memory-usage reporting. Output: one runtime resource summary in each run report.
45. Add packaging for result bundles. Output: one zipped or structured export format for sharing outputs.
46. Add a dashboard view for benchmark outputs. Output: one interactive app page for site summaries and comparisons.
47. Add notebook-based exploratory analysis examples. Output: one tutorial notebook using real benchmark artifacts.
48. Write a methods note for the strict 3D gate. Output: one markdown explainer describing thresholds and rationale.
49. Write a public-facing results summary. Output: one polished markdown or PDF-ready narrative of baseline findings.
50. Define the criteria for promoting a new default config. Output: one governance document for future baseline updates.

## Recommended near-term order

Start with items `1`, `2`, `10`, `13`, `21`, `31`, `39`, `41`, `48`, and `50`. Together they expand geographic coverage, improve interpretability, and make the current baseline easier to reproduce and defend.

## Phased roadmap

Phase 1: Baseline hardening
- Items `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `39`, `41`, `42`
- Output bundle: expanded baseline dataset registry, validated manifests, reproducible baseline command, and CI smoke checks.

Phase 2: Modeling sensitivity and ecological realism
- Items `11`, `12`, `13`, `14`, `15`, `16`, `17`, `18`, `19`, `20`, `21`, `22`, `23`, `24`, `25`, `26`, `27`, `28`
- Output bundle: sensitivity matrices, ecological confidence tiers, and robustness/uncertainty summaries.

Phase 3: Reporting and interpretability artifacts
- Items `29`, `30`, `31`, `32`, `33`, `34`, `35`, `36`, `37`, `38`, `43`, `44`, `45`, `46`, `47`, `48`, `49`, `50`
- Output bundle: decision-ready scorecards, visual artifact packs, governance criteria, and public-facing narrative reports.