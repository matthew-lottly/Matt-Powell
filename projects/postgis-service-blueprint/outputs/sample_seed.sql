TRUNCATE TABLE monitoring_features;
INSERT INTO monitoring_features (feature_id, layer_name, category, region, status, owner, geom) VALUES ('site-west-air-001', 'monitoring_sites', 'air_quality', 'West', 'active', 'Air Program', ST_SetSRID(ST_MakePoint(-121.4944, 38.5816), 4326));
INSERT INTO monitoring_features (feature_id, layer_name, category, region, status, owner, geom) VALUES ('site-central-smoke-002', 'monitoring_sites', 'wildfire', 'Central', 'active', 'Wildfire Operations', ST_SetSRID(ST_MakePoint(-121.3153, 44.0582), 4326));
INSERT INTO monitoring_features (feature_id, layer_name, category, region, status, owner, geom) VALUES ('zone-east-maint-003', 'maintenance_zones', 'infrastructure', 'East', 'review', 'Field Engineering', ST_SetSRID(ST_MakePoint(-104.9903, 39.7392), 4326));
