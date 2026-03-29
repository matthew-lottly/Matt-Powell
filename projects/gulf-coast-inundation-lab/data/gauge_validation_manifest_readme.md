# Gauge Validation Manifest

The companion GeoJSON file contains ten public USGS gauges selected to span the Gulf Coast study area across HUC2 regions `03`, `08`, and `12`.

Suggested workflow:

1. Upload `gauge_validation_manifest.geojson` to Earth Engine as a table asset.
2. Buffer the points or replace them with final AOI polygons for each reach.
3. Preserve the `gaugeId` and `gaugeName` fields so the export script can join back to NWIS stage data.

The file is a starting manifest for validation design, not a claim that all ten sites will produce equally strong $R^2$ values.