INSERT INTO public.monitoring_stations (feature_id, name, category, region, status, last_observation_at, geometry)
VALUES
    ('station-001', 'Mississippi River Gauge', 'hydrology', 'Midwest', 'normal', '2026-03-18T12:00:00Z', ST_SetSRID(ST_MakePoint(-93.265, 44.977), 4326)),
    ('station-002', 'Sierra Air Quality Node', 'air_quality', 'West', 'alert', '2026-03-18T12:05:00Z', ST_SetSRID(ST_MakePoint(-121.494, 38.581), 4326)),
    ('station-003', 'Boston Harbor Buoy', 'water_quality', 'Northeast', 'offline', '2026-03-17T22:30:00Z', ST_SetSRID(ST_MakePoint(-71.0589, 42.3601), 4326))
ON CONFLICT (feature_id) DO NOTHING;