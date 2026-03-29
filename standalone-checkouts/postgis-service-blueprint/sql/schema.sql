CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE monitoring_features (
    feature_id TEXT PRIMARY KEY,
    layer_name TEXT NOT NULL,
    category TEXT NOT NULL,
    region TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX monitoring_features_geom_idx ON monitoring_features USING GIST (geom);
CREATE INDEX monitoring_features_status_idx ON monitoring_features (status);
CREATE INDEX monitoring_features_region_idx ON monitoring_features (region);
