CREATE TABLE IF NOT EXISTS dim_station (
    station_key INTEGER PRIMARY KEY,
    station_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    region TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_station_attribute_history (
    station_history_key INTEGER PRIMARY KEY,
    station_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    owner_team TEXT NOT NULL,
    response_tier TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_region (
    region_key INTEGER PRIMARY KEY,
    region_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_category (
    category_key INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_observation (
    observation_id INTEGER PRIMARY KEY,
    station_key INTEGER NOT NULL,
    region_key INTEGER NOT NULL,
    category_key INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    alert_score DOUBLE NOT NULL,
    reading_value DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS mart_alert_station_daily (
    observation_date TEXT NOT NULL,
    station_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    region_name TEXT NOT NULL,
    category_name TEXT NOT NULL,
    alert_count INTEGER NOT NULL,
    max_alert_score DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS mart_region_status_daily (
    observation_date TEXT NOT NULL,
    region_name TEXT NOT NULL,
    status TEXT NOT NULL,
    observation_count INTEGER NOT NULL,
    avg_alert_score DOUBLE NOT NULL,
    max_alert_score DOUBLE NOT NULL
);