DELETE FROM dim_station;
DELETE FROM dim_station_attribute_history;
DELETE FROM dim_region;
DELETE FROM dim_category;
DELETE FROM fact_observation;
DELETE FROM mart_alert_station_daily;
DELETE FROM mart_region_status_daily;

INSERT INTO dim_region
SELECT
    ROW_NUMBER() OVER (ORDER BY region) AS region_key,
    region AS region_name
FROM (
    SELECT DISTINCT region
    FROM staging_readings
);

INSERT INTO dim_category
SELECT
    ROW_NUMBER() OVER (ORDER BY category) AS category_key,
    category AS category_name
FROM (
    SELECT DISTINCT category
    FROM staging_readings
);

INSERT INTO dim_station
SELECT
    ROW_NUMBER() OVER (ORDER BY station_id) AS station_key,
    station_id,
    station_name,
    region,
    category
FROM (
    SELECT DISTINCT station_id, station_name, region, category
    FROM staging_readings
);

INSERT INTO dim_station_attribute_history
SELECT
    ROW_NUMBER() OVER (ORDER BY station_id, effective_from) AS station_history_key,
    station_id,
    station_name,
    owner_team,
    response_tier,
    effective_from,
    NULLIF(effective_to, '') AS effective_to,
    is_current
FROM staging_station_attribute_history;

INSERT INTO fact_observation
SELECT
    ROW_NUMBER() OVER (ORDER BY s.station_id, r.observed_at) AS observation_id,
    s.station_key,
    rg.region_key,
    c.category_key,
    r.observed_at,
    r.status,
    r.alert_score,
    r.reading_value
FROM staging_readings AS r
JOIN dim_station AS s ON s.station_id = r.station_id
JOIN dim_region AS rg ON rg.region_name = r.region
JOIN dim_category AS c ON c.category_name = r.category;

INSERT INTO mart_alert_station_daily
SELECT
    SUBSTR(r.observed_at, 1, 10) AS observation_date,
    s.station_id,
    s.station_name,
    rg.region_name,
    c.category_name,
    COUNT(*) AS alert_count,
    MAX(r.alert_score) AS max_alert_score
FROM staging_readings AS r
JOIN dim_station AS s ON s.station_id = r.station_id
JOIN dim_region AS rg ON rg.region_name = r.region
JOIN dim_category AS c ON c.category_name = r.category
WHERE r.status = 'alert'
GROUP BY 1, 2, 3, 4, 5;

INSERT INTO mart_region_status_daily
SELECT
    SUBSTR(r.observed_at, 1, 10) AS observation_date,
    rg.region_name,
    r.status,
    COUNT(*) AS observation_count,
    ROUND(AVG(r.alert_score), 2) AS avg_alert_score,
    MAX(r.alert_score) AS max_alert_score
FROM staging_readings AS r
JOIN dim_region AS rg ON rg.region_name = r.region
GROUP BY 1, 2, 3;