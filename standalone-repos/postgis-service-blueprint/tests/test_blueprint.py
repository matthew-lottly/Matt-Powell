from pathlib import Path

from postgis_service_blueprint.blueprint import build_service_blueprint, export_seed_sql, export_service_blueprint, load_layer_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_layer_features() -> None:
    features = load_layer_features(PROJECT_ROOT / "data" / "service_layers.geojson")

    assert len(features) == 3
    assert features[0].layer_name == "monitoring_sites"
    assert {feature.region for feature in features} == {"West", "Central", "East"}


def test_build_service_blueprint() -> None:
    blueprint = build_service_blueprint(PROJECT_ROOT)

    assert blueprint["serviceName"] == "PostGIS Service Blueprint"
    assert blueprint["summary"]["featureCount"] == 3
    assert blueprint["summary"]["layers"]["monitoring_sites"] == 2
    assert blueprint["collections"][0]["id"] == "maintenance_zones"
    assert blueprint["publicationPlan"]["database"] == "PostgreSQL + PostGIS"
    assert "bbox filter" in blueprint["collections"][1]["queryPatterns"]


def test_export_service_blueprint(tmp_path: Path) -> None:
    output_path = export_service_blueprint(tmp_path, service_name="Open Spatial Service")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Open Spatial Service" in content
    assert "postgis_service_blueprint.json" in str(output_path)


def test_export_seed_sql(tmp_path: Path) -> None:
    output_path = export_seed_sql(tmp_path / "sample_seed.sql", project_root=PROJECT_ROOT)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "TRUNCATE TABLE monitoring_features;" in content
    assert "INSERT INTO monitoring_features" in content
    assert "ST_SetSRID(ST_MakePoint" in content
