CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS public.monitoring_stations (
    feature_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    region TEXT NOT NULL,
    status TEXT NOT NULL,
    last_observation_at TIMESTAMPTZ NOT NULL,
    geometry GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS monitoring_stations_geometry_gix
    ON public.monitoring_stations
    USING GIST (geometry);