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

CREATE TABLE IF NOT EXISTS public.monitoring_observations (
    observation_id TEXT PRIMARY KEY,
    feature_id TEXT NOT NULL REFERENCES public.monitoring_stations(feature_id) ON DELETE CASCADE,
    observed_at TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS monitoring_observations_feature_time_idx
    ON public.monitoring_observations (feature_id, observed_at DESC);