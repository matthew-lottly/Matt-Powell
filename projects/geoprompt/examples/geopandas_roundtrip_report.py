from __future__ import annotations

from pathlib import Path

import geoprompt as gp


def main() -> None:
    frame = gp.GeoPromptFrame.from_records(
        [
            {
                "site_id": "substation-a",
                "demand": 120.0,
                "geometry": {"type": "Point", "coordinates": (-111.90, 40.75)},
            },
            {
                "site_id": "substation-b",
                "demand": 95.0,
                "geometry": {"type": "Point", "coordinates": (-111.84, 40.78)},
            },
        ],
        crs="EPSG:4326",
    )

    if gp.geopandas_available():
        geodataframe = gp.to_geopandas(frame)
        restored = gp.from_geopandas(geodataframe)
        print(f"roundtrip rows: {len(restored)}")
    else:
        print("GeoPandas not installed; skipping roundtrip example.")

    report = gp.build_scenario_report(
        baseline_metrics={"served_load": 180.0, "deficit": 0.12},
        candidate_metrics={"served_load": 205.0, "deficit": 0.05},
        baseline_name="existing network",
        candidate_name="reinforced network",
        higher_is_better=["served_load"],
        metadata={"scenario_id": "network-reinforcement-demo"},
    )

    output_dir = Path("outputs")
    for filename in ["scenario-report.json", "scenario-report.csv", "scenario-report.md", "scenario-report.html"]:
        destination = output_dir / filename
        gp.export_scenario_report(report, destination)
        print(f"wrote {destination}")

    scores = gp.batch_accessibility_scores(
        supply_rows=[[200.0, 100.0, 30.0], [150.0, 90.0, 25.0]],
        travel_cost_rows=[[0.5, 1.0, 2.5], [0.4, 0.8, 1.8]],
        decay_method="exponential",
        rate=0.6,
    )
    print(f"batch accessibility: {scores}")


if __name__ == "__main__":
    main()