import { useMemo, useState } from "react";

import dashboardData from "../data/dashboard_layers.json";
import { MapCanvas } from "./map/MapCanvas";
import { summarizeLayers } from "./map/summary";
import type { DashboardLayer, LayerStatus } from "./map/types";


const ALL_STATUSES: LayerStatus[] = ["active", "review", "offline"];


export function App() {
  const [selectedStatus, setSelectedStatus] = useState<LayerStatus | "all">("all");
  const [selectedRegion, setSelectedRegion] = useState<string>("All");
  const layers = dashboardData.layers as DashboardLayer[];

  const regions = useMemo(
    () => ["All", ...new Set(layers.map((layer) => layer.region))],
    [layers],
  );

  const filteredLayers = useMemo(
    () =>
      layers.filter((layer) => {
        const regionMatch = selectedRegion === "All" || layer.region === selectedRegion;
        const statusMatch = selectedStatus === "all" || layer.status === selectedStatus;
        return regionMatch && statusMatch;
      }),
    [layers, selectedRegion, selectedStatus],
  );

  const summary = useMemo(() => summarizeLayers(filteredLayers), [filteredLayers]);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Open Web Map Client</p>
          <h1>Operations Dashboard</h1>
          <p className="hero-copy">
            Public-safe React and TypeScript dashboard with a live MapLibre map, regional filters, layer-state
            review, and feature inspection patterns that can pair with PostGIS-backed services.
          </p>
        </div>
        <div className="hero-notes">
          <span className="badge">TypeScript</span>
          <span className="badge">React</span>
          <span className="badge">Map UI</span>
          <span className="badge">Open Stack</span>
        </div>
      </section>

      <section className="control-panel">
        <label>
          <span>Region</span>
          <select value={selectedRegion} onChange={(event) => setSelectedRegion(event.target.value)}>
            {regions.map((region) => (
              <option key={region} value={region}>
                {region}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Status</span>
          <select value={selectedStatus} onChange={(event) => setSelectedStatus(event.target.value as LayerStatus | "all")}>
            <option value="all">All</option>
            {ALL_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="summary-grid">
        <article className="summary-card">
          <p className="summary-label">Visible Layers</p>
          <strong>{summary.totalLayers}</strong>
        </article>
        <article className="summary-card">
          <p className="summary-label">Features</p>
          <strong>{summary.totalFeatures}</strong>
        </article>
        <article className="summary-card">
          <p className="summary-label">Regions</p>
          <strong>{summary.regionCount}</strong>
        </article>
      </section>

      <section className="dashboard-grid">
        <MapCanvas layers={filteredLayers} />
        <aside className="layer-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Layer Stack</p>
              <h2>Operational Layers</h2>
            </div>
          </div>
          <ul className="layer-list">
            {filteredLayers.map((layer) => (
              <li key={layer.id} className="layer-card">
                <div>
                  <p className="layer-title">{layer.title}</p>
                  <p className="layer-meta">{layer.region} · {layer.format} · {layer.featureCount} features</p>
                  <p className="layer-meta">
                    {layer.coordinates.latitude.toFixed(2)}, {layer.coordinates.longitude.toFixed(2)}
                  </p>
                </div>
                <span className={`status-chip ${layer.status}`}>{layer.status}</span>
              </li>
            ))}
          </ul>
        </aside>
      </section>
    </main>
  );
}
