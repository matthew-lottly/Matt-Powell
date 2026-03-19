import { useEffect, useMemo, useRef } from "react";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";

import type { DashboardLayer } from "./types";


interface MapCanvasProps {
  layers: DashboardLayer[];
}


export function MapCanvas({ layers }: MapCanvasProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const featureCollection = useMemo(
    (): GeoJSON.FeatureCollection<GeoJSON.Point> => ({
      type: "FeatureCollection",
      features: layers.map((layer) => ({
        type: "Feature",
        properties: {
          id: layer.id,
          title: layer.title,
          status: layer.status,
          region: layer.region,
        },
        geometry: {
          type: "Point",
          coordinates: [layer.coordinates.longitude, layer.coordinates.latitude],
        },
      })),
    }),
    [layers],
  );

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "OpenStreetMap",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm",
          },
        ],
      },
      center: [-112.5, 40.5],
      zoom: 3.25,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => {
      map.addSource("operations-layers", {
        type: "geojson",
        data: featureCollection,
      });
      map.addLayer({
        id: "operations-layer-points",
        type: "circle",
        source: "operations-layers",
        paint: {
          "circle-radius": 9,
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
          "circle-color": [
            "match",
            ["get", "status"],
            "active",
            "#2d7f70",
            "review",
            "#bf7c2c",
            "offline",
            "#99504a",
            "#61747b",
          ],
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [featureCollection]);

  useEffect(() => {
    const source = mapRef.current?.getSource("operations-layers") as GeoJSONSource | undefined;
    if (source) {
      source.setData(featureCollection as GeoJSON.FeatureCollection);
    }
  }, [featureCollection]);

  return (
    <section className="map-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Map Surface</p>
          <h2>Open Operations View</h2>
        </div>
        <p className="section-copy">Live MapLibre surface using OpenStreetMap raster tiles and a GeoJSON overlay for operational layers.</p>
      </div>
      <div ref={mapContainerRef} className="map-surface" aria-label="Operations map" data-testid="map-surface">
        <div className="map-region west">West</div>
        <div className="map-region central">Central</div>
        <div className="map-region east">East</div>
      </div>
    </section>
  );
}
