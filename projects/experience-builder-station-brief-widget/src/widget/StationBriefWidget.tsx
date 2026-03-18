import { useMemo, useState } from "react";

import { filterStations, regionsForStations, summarizeStations } from "./transform";
import type { StationRecord, WidgetConfig } from "./types";


interface StationBriefWidgetProps {
  stations: StationRecord[];
  config: WidgetConfig;
}


export function StationBriefWidget({ stations, config }: StationBriefWidgetProps) {
  const regions = useMemo(() => regionsForStations(stations), [stations]);
  const [region, setRegion] = useState(config.defaultRegion ?? "All");
  const [selectedId, setSelectedId] = useState(stations[0]?.id ?? "");

  const filteredStations = useMemo(() => filterStations(stations, region), [stations, region]);
  const summary = useMemo(() => summarizeStations(filteredStations), [filteredStations]);
  const thresholdStations = filteredStations.filter((station) => station.alertScore >= config.alertThreshold);
  const selectedStation = filteredStations.find((station) => station.id === selectedId) ?? filteredStations[0] ?? null;

  return (
    <section className="widget-shell">
      <div className="widget-header">
        <div>
          <p className="eyebrow">Widget Surface</p>
          <h2>{config.title}</h2>
          <p className="section-copy">{config.subtitle}</p>
        </div>
        <label className="control-block">
          <span>Region</span>
          <select value={region} onChange={(event) => setRegion(event.target.value)}>
            {regions.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="summary-grid">
        <article className="summary-card accent-sand">
          <p className="summary-label">Stations</p>
          <strong>{summary.totalStations}</strong>
        </article>
        <article className="summary-card accent-alert">
          <p className="summary-label">Alert</p>
          <strong>{summary.alertStations}</strong>
        </article>
        <article className="summary-card accent-slate">
          <p className="summary-label">Offline</p>
          <strong>{summary.offlineStations}</strong>
        </article>
        <article className="summary-card accent-moss">
          <p className="summary-label">Avg Score</p>
          <strong>{summary.avgAlertScore}</strong>
        </article>
      </div>

      <div className="overview-grid">
        <section className="widget-panel coverage-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Coverage View</p>
              <h3>Map-Adjacent Mock</h3>
            </div>
            <p className="section-copy">Simple marker layout to show how list selection can stay synchronized with a map surface.</p>
          </div>
          <div className="coverage-map" aria-label="Station coverage map mock">
            <div className="coverage-region west">West</div>
            <div className="coverage-region central">Central</div>
            <div className="coverage-region east">East</div>
            <div className="coverage-region gulf">South</div>
            {filteredStations.map((station) => (
              <button
                key={station.id}
                type="button"
                className={`map-marker marker-${station.id} ${station.status}${selectedStation?.id === station.id ? " active" : ""}`}
                onClick={() => setSelectedId(station.id)}
                aria-label={`Select ${station.name}`}
              >
                <span />
              </button>
            ))}
          </div>
        </section>

        <section className="widget-panel config-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Widget Config</p>
              <h3>Runtime Settings</h3>
            </div>
            <p className="section-copy">Public-safe example of the kind of configuration state an Experience Builder widget carries.</p>
          </div>
          <div className="detail-grid compact">
            <div>
              <p className="detail-label">Default Region</p>
              <strong>{config.defaultRegion ?? "All"}</strong>
            </div>
            <div>
              <p className="detail-label">Show Owner</p>
              <strong>{config.showOwner ? "Enabled" : "Hidden"}</strong>
            </div>
            <div>
              <p className="detail-label">Alert Threshold</p>
              <strong>{config.alertThreshold}</strong>
            </div>
            <div>
              <p className="detail-label">Above Threshold</p>
              <strong>{thresholdStations.length}</strong>
            </div>
          </div>
        </section>
      </div>

      <div className="widget-grid">
        <section className="widget-panel list-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Selection</p>
              <h3>Stations</h3>
            </div>
            <p className="section-copy">Representative station records a widget might receive from a data source.</p>
          </div>
          <div className="station-list">
            {filteredStations.map((station) => (
              <button
                key={station.id}
                className={`station-row${selectedStation?.id === station.id ? " active" : ""}`}
                type="button"
                onClick={() => setSelectedId(station.id)}
              >
                <div>
                  <strong>{station.name}</strong>
                  <span>{station.category.replaceAll("_", " ")} · {station.region}</span>
                </div>
                <span className={`status-chip ${station.status}`}>{station.status}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="widget-panel detail-panel">
          {selectedStation ? (
            <>
              <div className="panel-head">
                <div>
                  <p className="eyebrow">Station Detail</p>
                  <h3>{selectedStation.name}</h3>
                </div>
                <span className={`status-chip ${selectedStation.status}`}>{selectedStation.status}</span>
              </div>
              <div className="detail-grid">
                <div>
                  <p className="detail-label">Region</p>
                  <strong>{selectedStation.region}</strong>
                </div>
                <div>
                  <p className="detail-label">Category</p>
                  <strong>{selectedStation.category.replaceAll("_", " ")}</strong>
                </div>
                <div>
                  <p className="detail-label">Last Observed</p>
                  <strong>{selectedStation.lastObservedAt}</strong>
                </div>
                <div>
                  <p className="detail-label">Reading</p>
                  <strong>{selectedStation.readingValue} {selectedStation.unit}</strong>
                </div>
                {config.showOwner ? (
                  <div>
                    <p className="detail-label">Owner</p>
                    <strong>{selectedStation.owner}</strong>
                  </div>
                ) : null}
                <div>
                  <p className="detail-label">Alert Score</p>
                  <strong>{selectedStation.alertScore}</strong>
                </div>
              </div>
            </>
          ) : (
            <p className="section-copy">No station matches the current filters.</p>
          )}
        </section>
      </div>
    </section>
  );
}