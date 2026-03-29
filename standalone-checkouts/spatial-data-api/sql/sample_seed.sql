INSERT INTO public.monitoring_stations (feature_id, name, category, region, status, last_observation_at, geometry)
VALUES
    ('station-001', 'Mississippi River Gauge', 'hydrology', 'Midwest', 'normal', '2026-03-18T12:00:00Z', ST_SetSRID(ST_MakePoint(-93.265, 44.977), 4326)),
    ('station-002', 'Sierra Air Quality Node', 'air_quality', 'West', 'alert', '2026-03-18T12:05:00Z', ST_SetSRID(ST_MakePoint(-121.494, 38.581), 4326)),
    ('station-003', 'Boston Harbor Buoy', 'water_quality', 'Northeast', 'offline', '2026-03-17T22:30:00Z', ST_SetSRID(ST_MakePoint(-71.0589, 42.3601), 4326))
ON CONFLICT (feature_id) DO NOTHING;

INSERT INTO public.monitoring_observations (observation_id, feature_id, observed_at, metric_name, value, unit, status)
VALUES
    ('obs-1001', 'station-001', '2026-03-18T12:00:00Z', 'river_stage_ft', 12.4, 'ft', 'normal'),
    ('obs-1002', 'station-001', '2026-03-18T11:30:00Z', 'river_stage_ft', 12.1, 'ft', 'normal'),
    ('obs-2001', 'station-002', '2026-03-18T12:05:00Z', 'pm25', 41.8, 'ug/m3', 'alert'),
    ('obs-2002', 'station-002', '2026-03-18T11:45:00Z', 'pm25', 33.2, 'ug/m3', 'alert'),
    ('obs-3001', 'station-003', '2026-03-17T22:30:00Z', 'dissolved_oxygen', 0.0, 'mg/L', 'offline'),
    ('obs-3002', 'station-003', '2026-03-17T20:00:00Z', 'dissolved_oxygen', 5.7, 'mg/L', 'normal')
ON CONFLICT (observation_id) DO NOTHING;