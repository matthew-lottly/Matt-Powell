INSERT INTO public.spatial_assets (feature_id, name, category, region, geometry)
VALUES
    ('asset-001', 'River Gauge Alpha', 'hydrology', 'Midwest', ST_SetSRID(ST_MakePoint(-93.265, 44.977), 4326)),
    ('asset-002', 'Wildfire Sensor Bravo', 'hazards', 'West', ST_SetSRID(ST_MakePoint(-121.494, 38.581), 4326)),
    ('asset-003', 'Transit Stop Cluster', 'transportation', 'Northeast', ST_SetSRID(ST_MakePoint(-71.0589, 42.3601), 4326))
ON CONFLICT (feature_id) DO NOTHING;