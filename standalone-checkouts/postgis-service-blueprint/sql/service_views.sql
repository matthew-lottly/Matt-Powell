CREATE OR REPLACE VIEW published_monitoring_sites AS
SELECT
    feature_id,
    category,
    region,
    status,
    owner,
    geom,
    updated_at
FROM monitoring_features
WHERE layer_name = 'monitoring_sites';

CREATE OR REPLACE VIEW published_maintenance_zones AS
SELECT
    feature_id,
    category,
    region,
    status,
    owner,
    geom,
    updated_at
FROM monitoring_features
WHERE layer_name = 'maintenance_zones';
