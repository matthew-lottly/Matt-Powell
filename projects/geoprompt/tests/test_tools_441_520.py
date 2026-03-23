"""Smoke tests for tools 441-520."""

import pytest

from geoprompt import GeoPromptFrame


@pytest.fixture()
def sample_frame():
    records = []
    for index in range(12):
        x_coord = float(index % 4)
        y_coord = float(index // 4)
        value = 2.5 * x_coord + 3.0 * y_coord + (index % 3)
        records.append({
            "geometry": {"type": "Point", "coordinates": [x_coord, y_coord]},
            "val": value,
            "other": value * 0.4 + y_coord,
            "mass": 1.0 + index,
            "demand": 2.0 + (index % 5),
            "supply": 3.0 + (index % 4),
            "group": "A" if x_coord < 2 else "B",
            "state": "S1" if index % 3 == 0 else ("S2" if index % 3 == 1 else "S3"),
            "ord": "low" if value < 5 else ("mid" if value < 9 else "high"),
            "treatment": index % 2 == 0,
            "outcome": value + (2.0 if index % 2 == 0 else -1.0),
            "time": float(index),
            "speed": 1.0 + 0.1 * index,
            "source": index in (0, 5),
            "f1": x_coord + 0.2 * index,
            "f2": y_coord + 0.1 * index,
            "f3": value * 0.3,
        })
    return GeoPromptFrame.from_records(records, crs="EPSG:4326")


TOOL_CASES = [
    {"method": "gravity_flow_model", "args": ("mass",), "kwargs": {"beta": 1.5}, "cols": ["inflow_gfm"], "len": 12},
    {"method": "diffusion_kernel_smooth", "args": ("val",), "kwargs": {"time_steps": 3, "k_neighbors": 3}, "cols": ["smoothed_dks"], "len": 12},
    {"method": "topological_persistence", "args": ("val",), "kwargs": {}, "cols": ["persistence_tph"], "len": 12},
    {"method": "levy_flight_optimizer", "args": ("val",), "kwargs": {"n_walkers": 3, "n_steps": 5, "seed": 1}, "cols": ["optimal_value_lfo"], "len": 1},
    {"method": "spectral_graph_partition", "args": (), "kwargs": {"k_neighbors": 3, "n_clusters": 2, "n_iterations": 8, "seed": 1}, "cols": ["cluster_sgp"], "len": 12},
    {"method": "spatial_wavelet_decompose", "args": ("val",), "kwargs": {"n_scales": 2, "grid_resolution": 4}, "cols": ["scale_0_swv"], "len": 16},
    {"method": "spatial_information_entropy", "args": ("val",), "kwargs": {"n_bins": 4}, "cols": ["entropy_sie"], "len": 12},
    {"method": "ant_colony_path_finder", "args": ("val",), "kwargs": {"n_ants": 3, "n_iterations": 4, "seed": 1}, "cols": ["visit_order_aco"], "len": 12},
    {"method": "fractal_dimension_estimator", "args": (), "kwargs": {"n_scales": 4}, "cols": ["dimension_fde"], "len": 1},
    {"method": "reaction_diffusion_pattern", "args": (), "kwargs": {"grid_resolution": 4, "n_steps": 3, "seed": 1}, "cols": ["pattern_rdp"], "len": 16},
    {"method": "spatial_pagerank", "args": (), "kwargs": {"k_neighbors": 3, "n_iterations": 8}, "cols": ["pagerank_spr"], "len": 12},
    {"method": "cellular_automata_simulator", "args": ("val",), "kwargs": {"grid_resolution": 4, "n_steps": 3, "threshold": 0.4, "seed": 1}, "cols": ["state_cas"], "len": 16},
    {"method": "spatial_label_propagation", "args": ("group",), "kwargs": {"k_neighbors": 3, "n_iterations": 4, "seed": 1}, "cols": ["label_slp"], "len": 12},
    {"method": "optimal_facility_locator", "args": ("demand",), "kwargs": {"n_facilities": 2, "n_iterations": 6, "seed": 1}, "cols": ["facility_ofl"], "len": 12},
    {"method": "spatial_outlier_ensemble", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["outlier_score_soe"], "len": 12},
    {"method": "spatial_reservoir_computer", "args": ("val", "time"), "kwargs": {"reservoir_size": 8, "seed": 1}, "cols": ["predicted_src"], "len": 12},
    {"method": "spatial_contour_tree", "args": ("val",), "kwargs": {}, "cols": ["tree_depth_sct"], "len": 12},
    {"method": "multi_scale_geographically_weighted", "args": (["f1", "f2", "f3"], "val"), "kwargs": {}, "cols": ["predicted_mgw"], "len": 12},
    {"method": "spatial_markov_chain", "args": ("state",), "kwargs": {"n_steps": 3, "k_neighbors": 3, "seed": 1}, "cols": ["final_state_smc"], "len": 12},
    {"method": "spatial_homology_betti", "args": (), "kwargs": {}, "cols": ["beta0_shb"], "len": 1},
    {"method": "spatial_potential_field", "args": ("val",), "kwargs": {"grid_resolution": 4}, "cols": ["potential_spf"], "len": 16},
    {"method": "particle_swarm_cluster", "args": ("val",), "kwargs": {"n_clusters": 2, "n_particles": 4, "n_iterations": 6, "seed": 1}, "cols": ["cluster_psc"], "len": 12},
    {"method": "spatial_elastic_net", "args": (["f1", "f2", "f3"], "val"), "kwargs": {"epochs": 30}, "cols": ["predicted_sen"], "len": 12},
    {"method": "spatial_dbscan_clustering", "args": (), "kwargs": {"epsilon": 1.5, "min_points": 2}, "cols": ["cluster_dbs"], "len": 12},
    {"method": "spatial_mean_shift", "args": (), "kwargs": {"bandwidth": 1.5, "n_iterations": 5}, "cols": ["cluster_sms"], "len": 12},
    {"method": "spatial_gradient_field", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["slope_sgf"], "len": 12},
    {"method": "spatial_hdbscan", "args": (), "kwargs": {"min_cluster_size": 2, "min_samples": 2}, "cols": ["cluster_hdb"], "len": 12},
    {"method": "spatial_copula_dependence", "args": ("val", "other"), "kwargs": {}, "cols": ["local_tau_scp"], "len": 12},
    {"method": "spatial_loess_regression", "args": (["f1", "f2", "f3"], "val"), "kwargs": {"span": 0.5}, "cols": ["predicted_lss"], "len": 12},
    {"method": "spatial_flow_accumulation", "args": ("val",), "kwargs": {}, "cols": ["accumulation_sfa"], "len": 12},
    {"method": "spatial_cross_k_function", "args": ("group", "A", "B"), "kwargs": {"n_bins": 4}, "cols": ["k_cross_ckf"], "len": 4},
    {"method": "harmonic_regression_spatial", "args": ("val", "time"), "kwargs": {"n_harmonics": 2}, "cols": ["predicted_hrs"], "len": 12},
    {"method": "spatial_bootstrap_confidence", "args": ("val",), "kwargs": {"n_bootstrap": 10, "seed": 1}, "cols": ["ci_lower_sbc"], "len": 12},
    {"method": "spatial_variogram_cloud", "args": ("val",), "kwargs": {}, "cols": ["semivariance_svc"], "min_len": 10},
    {"method": "spatial_permutation_test", "args": ("val",), "kwargs": {"n_permutations": 10, "seed": 1, "k_neighbors": 3}, "cols": ["p_value_spt"], "len": 12},
    {"method": "spatial_random_walk_diffusion", "args": ("val",), "kwargs": {"n_steps": 4, "k_neighbors": 3, "n_walkers": 8, "seed": 1}, "cols": ["accessibility_rwd"], "len": 12},
    {"method": "adaptive_spatial_scan_statistic", "args": ("val",), "kwargs": {"n_radius_steps": 4}, "cols": ["scan_llr_sss"], "len": 12},
    {"method": "spatial_silhouette_score", "args": ("group",), "kwargs": {}, "cols": ["silhouette_sil"], "len": 12},
    {"method": "spatial_curvature_estimator", "args": ("val",), "kwargs": {"k_neighbors": 4}, "cols": ["mean_curvature_sce"], "len": 12},
    {"method": "spatial_causal_inference", "args": ("treatment", "outcome"), "kwargs": {"k_neighbors": 3}, "cols": ["ate_sci"], "len": 12},
    {"method": "spatial_optimal_transport", "args": ("mass",), "kwargs": {"reg": 0.8, "n_iterations": 8}, "cols": ["transport_cost_sot"], "len": 12},
    {"method": "graph_neural_spatial_smoother", "args": ("val",), "kwargs": {"k_neighbors": 3, "n_layers": 2}, "cols": ["smoothed_gns"], "len": 12},
    {"method": "anisotropic_diffusion_surface", "args": ("val",), "kwargs": {"k_neighbors": 3, "n_steps": 4}, "cols": ["diffused_ads"], "len": 12},
    {"method": "persistent_hotspot_tracker", "args": ("val",), "kwargs": {"n_thresholds": 5, "k_neighbors": 3}, "cols": ["persistence_pht"], "len": 12},
    {"method": "spatial_conformal_predictor", "args": (["f1", "f2", "f3"], "val"), "kwargs": {"calibration_fraction": 0.25, "k_neighbors": 3}, "cols": ["lower_scp"], "len": 12},
    {"method": "geodesic_medoid_clustering", "args": (), "kwargs": {"n_clusters": 2, "k_neighbors": 3, "n_iterations": 4, "seed": 1}, "cols": ["cluster_gmc"], "len": 12},
    {"method": "spatial_sinkhorn_barycenter", "args": ("mass",), "kwargs": {"n_iterations": 8}, "cols": ["barycenter_x_skb"], "len": 1},
    {"method": "multi_agent_coverage", "args": ("demand",), "kwargs": {"n_agents": 3}, "cols": ["agent_mac"], "len": 12},
    {"method": "manifold_alignment_spatial", "args": (["f1", "f2", "f3"],), "kwargs": {"n_components": 2, "k_neighbors": 3, "n_iterations": 5, "seed": 1}, "cols": ["component_0_mas"], "len": 12},
    {"method": "spatial_stochastic_blockmodel", "args": (), "kwargs": {"n_blocks": 3, "k_neighbors": 3, "n_iterations": 4, "seed": 1}, "cols": ["block_ssb"], "len": 12},
    {"method": "adaptive_mesh_refinement_surface", "args": ("val",), "kwargs": {"base_resolution": 4, "max_level": 1, "error_threshold": 0.1}, "cols": ["level_amr"], "min_len": 1},
    {"method": "spatial_koopman_forecaster", "args": ("val", "time"), "kwargs": {}, "cols": ["predicted_next_skf"], "len": 12},
    {"method": "barycentric_spatial_interpolator", "args": ("val",), "kwargs": {"grid_resolution": 4}, "cols": ["predicted_bsi"], "len": 16},
    {"method": "topological_skeleton_extractor", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["is_skeleton_tsk"], "len": 12},
    {"method": "spatial_contrastive_embedding", "args": (["f1", "f2", "f3"],), "kwargs": {"n_components": 2, "n_iterations": 5, "seed": 1}, "cols": ["embed_0_sce"], "len": 12},
    {"method": "uncertainty_aware_idw", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["uncertainty_uidw"], "len": 12},
    {"method": "spatial_federated_clusterer", "args": (["f1", "f2", "f3"],), "kwargs": {"n_clusters": 3}, "cols": ["cluster_sfc"], "len": 12},
    {"method": "graph_wave_propagation", "args": ("val",), "kwargs": {"k_neighbors": 3, "n_steps": 4}, "cols": ["amplitude_gwp"], "len": 12},
    {"method": "spatial_morse_smale_partition", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["basin_sms"], "len": 12},
    {"method": "optimal_transport_clustering", "args": ("mass",), "kwargs": {"n_clusters": 2, "n_iterations": 4, "seed": 1}, "cols": ["cluster_otc"], "len": 12},
    {"method": "game_theoretic_location_equilibrium", "args": ("demand",), "kwargs": {"n_players": 2, "n_iterations": 4, "seed": 1}, "cols": ["player_gle"], "len": 12},
    {"method": "spatial_ordinal_regression", "args": (["f1", "f2", "f3"], "ord"), "kwargs": {"epochs": 20}, "cols": ["predicted_sor"], "len": 12},
    {"method": "graph_total_variation_denoise", "args": ("val",), "kwargs": {"k_neighbors": 3, "n_steps": 5}, "cols": ["denoised_gtv"], "len": 12},
    {"method": "spatial_nystrom_kernel_map", "args": (["f1", "f2", "f3"],), "kwargs": {"n_components": 2, "n_landmarks": 4, "seed": 1}, "cols": ["component_0_nyk"], "len": 12},
    {"method": "terrain_ridge_detector", "args": ("val",), "kwargs": {"k_neighbors": 4}, "cols": ["ridge_score_trd"], "len": 12},
    {"method": "spatial_conformal_outlier", "args": ("val",), "kwargs": {"calibration_fraction": 0.25, "k_neighbors": 3}, "cols": ["is_outlier_sco"], "len": 12},
    {"method": "hyperbolic_spatial_embedding", "args": (["f1", "f2", "f3"],), "kwargs": {}, "cols": ["x_hse"], "len": 12},
    {"method": "spatial_energy_distance_test", "args": ("val", "group"), "kwargs": {}, "cols": ["energy_distance_sed"], "len": 12},
    {"method": "adaptive_radius_hotspot", "args": ("val",), "kwargs": {"n_radii": 4}, "cols": ["best_radius_arh"], "len": 12},
    {"method": "spatial_transport_accessibility", "args": ("supply", "demand"), "kwargs": {}, "cols": ["accessibility_sta"], "len": 12},
    {"method": "graph_heat_centrality", "args": (), "kwargs": {"k_neighbors": 3, "n_steps": 5}, "cols": ["heat_centrality_ghc"], "len": 12},
    {"method": "spatial_bayes_blend_interpolator", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["posterior_sbb"], "len": 12},
    {"method": "spatial_jensen_shannon_scan", "args": ("val",), "kwargs": {"k_neighbors": 3, "n_bins": 4}, "cols": ["js_divergence_sjs"], "len": 12},
    {"method": "front_propagation_distance", "args": ("source",), "kwargs": {"k_neighbors": 3, "speed_column": "speed"}, "cols": ["distance_fpd"], "len": 12},
    {"method": "spatial_kernel_herding", "args": (), "kwargs": {"n_select": 4}, "cols": ["selected_skh"], "len": 12},
    {"method": "spatial_mutual_information_map", "args": ("val", "other"), "kwargs": {"k_neighbors": 4, "n_bins": 4}, "cols": ["mi_smi"], "len": 12},
    {"method": "robust_spatial_median_field", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["median_rmf"], "len": 12},
    {"method": "spatial_bifurcation_detector", "args": ("val",), "kwargs": {"axis": "x", "window": 3}, "cols": ["bifurcation_score_sbd"], "len": 12},
    {"method": "spatial_adversarial_validator", "args": (["f1", "f2", "f3"],), "kwargs": {"split_axis": "x", "epochs": 20}, "cols": ["domain_prob_sav"], "len": 12},
    {"method": "spatial_consensus_partition", "args": ("val",), "kwargs": {"k_neighbors": 3}, "cols": ["cluster_scpn"], "len": 12},
]


@pytest.mark.parametrize("case", TOOL_CASES, ids=[case["method"] for case in TOOL_CASES])
def test_tools_441_520_smoke(sample_frame, case):
    method = getattr(sample_frame, case["method"])
    result = method(*case.get("args", ()), **case.get("kwargs", {}))
    records = result.to_records()
    if "len" in case:
        assert len(records) == case["len"]
    if "min_len" in case:
        assert len(records) >= case["min_len"]
    assert records
    for column in case["cols"]:
        assert column in records[0]
