import { useEffect, useMemo, useState } from "react";

import { filterStations, regionsForStations, summarizeStations } from "./transform";
import type { StationRecord, StationStatus, WidgetConfig } from "./types";


interface StationBriefWidgetProps {
  stations: StationRecord[];
  config: WidgetConfig;
  isLoading: boolean;
  loadError: string | null;
  onConfigChange: (nextConfig: WidgetConfig) => void;
}


const ALL_STATUSES: StationStatus[] = ["alert", "normal", "offline"];


export function StationBriefWidget({ stations, config, isLoading, loadError, onConfigChange }: StationBriefWidgetProps) {
  const regions = useMemo(() => regionsForStations(stations), [stations]);
  const [region, setRegion] = useState(config.defaultRegion ?? "All");
  const [selectedStatuses, setSelectedStatuses] = useState<StationStatus[]>(config.defaultStatuses);
  const [selectedId, setSelectedId] = useState(stations[0]?.id ?? "");
  const [comparisonId, setComparisonId] = useState(config.comparisonStationId ?? "");
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  useEffect(() => {
    setRegion(config.defaultRegion ?? "All");
  }, [config.defaultRegion]);

  useEffect(() => {
    setSelectedStatuses(config.defaultStatuses.length === 0 ? ALL_STATUSES : config.defaultStatuses);
  }, [config.defaultStatuses]);

  useEffect(() => {
    setComparisonId(config.comparisonStationId ?? "");
  }, [config.comparisonStationId]);

  const filteredStations = useMemo(
    () => filterStations(stations, region, selectedStatuses),
    [stations, region, selectedStatuses],
  );
  const summary = useMemo(() => summarizeStations(filteredStations), [filteredStations]);
  const thresholdStations = filteredStations.filter((station) => station.alertScore >= config.alertThreshold);
  const selectedStation = filteredStations.find((station) => station.id === selectedId) ?? filteredStations[0] ?? null;
  const comparisonCandidates = filteredStations.filter((station) => station.id !== selectedStation?.id);
  const comparisonStation = config.comparisonMode
    ? comparisonCandidates.find((station) => station.id === comparisonId) ?? comparisonCandidates[0] ?? null
    : null;

  useEffect(() => {
    if (filteredStations.length === 0) {
      setSelectedId("");
      setIsHistoryOpen(false);
      return;
    }
    if (!selectedStation) {
      setSelectedId(filteredStations[0].id);
    }
  }, [filteredStations, selectedStation]);

  useEffect(() => {
    if (!config.comparisonMode) {
      setComparisonId("");
      return;
    }
    if (comparisonCandidates.length === 0) {
      setComparisonId("");
      return;
    }
    if (!comparisonStation) {
      const nextComparisonId = comparisonCandidates[0].id;
      setComparisonId(nextComparisonId);
      updateConfig("comparisonStationId", nextComparisonId);
    }
  }, [comparisonCandidates, comparisonStation, config.comparisonMode]);

  function updateConfig<K extends keyof WidgetConfig>(key: K, value: WidgetConfig[K]) {
    onConfigChange({ ...config, [key]: value });
  }

  function toggleStatus(status: StationStatus) {
    const nextStatuses = selectedStatuses.includes(status)
      ? selectedStatuses.filter((entry) => entry !== status)
      : [...selectedStatuses, status];
    const normalizedStatuses = nextStatuses.length === 0 ? ALL_STATUSES : nextStatuses;
    setSelectedStatuses(normalizedStatuses);
    updateConfig("defaultStatuses", normalizedStatuses);
  }

  function renderStationDetailCard(station: StationRecord, heading: string) {
    return (
      <article className="comparison-card">
        <div className="panel-head">
          <div>
            <p className="eyebrow">{heading}</p>
            <h3>{station.name}</h3>
          </div>
          <span className={`status-chip ${station.status}`}>{station.status}</span>
        </div>
        <div className="detail-grid">
          <div>
            <p className="detail-label">Region</p>
            <strong>{station.region}</strong>
          </div>
          <div>
            <p className="detail-label">Category</p>
            <strong>{station.category.replaceAll("_", " ")}</strong>
          </div>
          <div>
            <p className="detail-label">Last Observed</p>
            <strong>{station.lastObservedAt}</strong>
          </div>
          <div>
            <p className="detail-label">Reading</p>
            <strong>{station.readingValue} {station.unit}</strong>
          </div>
          {config.showOwner ? (
            <div>
              <p className="detail-label">Owner</p>
              <strong>{station.owner}</strong>
            </div>
          ) : null}
          <div>
            <p className="detail-label">Alert Score</p>
            <strong>{station.alertScore}</strong>
          </div>
        </div>
        <div className="history-preview">
          <p className="detail-label">Latest History Note</p>
          <p className="section-copy">{station.observations[0]?.note ?? "No observations available."}</p>
        </div>
      </article>
    );
  }

  return (
    <section className="widget-shell">
      <div className="widget-header">
        <div>
          <p className="eyebrow">Widget Surface</p>
          <h2>{config.title}</h2>
          <p className="section-copy">{config.subtitle}</p>
          <div className="runtime-badges">
            <span className="badge">{config.dataSource === "live" ? "Live API" : "Mock Snapshot"}</span>
            {isLoading ? <span className="badge">Refreshing</span> : null}
          </div>
        </div>
        <div className="widget-controls">
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
          <fieldset className="filter-group">
            <legend>Visible Statuses</legend>
            <div className="status-filter-list">
              {ALL_STATUSES.map((status) => (
                <label key={status} className={`status-filter ${selectedStatuses.includes(status) ? "active" : ""}`}>
                  <input
                    aria-label={`${status} status filter`}
                    type="checkbox"
                    checked={selectedStatuses.includes(status)}
                    onChange={() => toggleStatus(status)}
                  />
                  <span>{status}</span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </div>

      {loadError ? (
        <div className="runtime-banner" role="status">
          Live API load failed: {loadError}. Showing the built-in mock snapshot instead.
        </div>
      ) : null}

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
            <p className="section-copy">Public-safe example of the kind of configuration state common in map-centric widget UIs, including Experience Builder-inspired patterns.</p>
          </div>
          <div className="detail-grid compact">
            <div>
              <label className="control-block">
                <span>Title</span>
                <input value={config.title} onChange={(event) => updateConfig("title", event.target.value)} />
              </label>
            </div>
            <div>
              <label className="control-block">
                <span>Default Region</span>
                <select
                  value={config.defaultRegion ?? "All"}
                  onChange={(event) => updateConfig("defaultRegion", event.target.value === "All" ? null : event.target.value)}
                >
                  {regions.map((entry) => (
                    <option key={entry} value={entry}>
                      {entry}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div>
              <label className="control-block">
                <span>Alert Threshold</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={config.alertThreshold}
                  onChange={(event) => updateConfig("alertThreshold", Number(event.target.value))}
                />
              </label>
            </div>
            <div>
              <label className="control-block">
                <span>Data Source</span>
                <select
                  aria-label="Data Source"
                  value={config.dataSource}
                  onChange={(event) => updateConfig("dataSource", event.target.value as WidgetConfig["dataSource"])}
                >
                  <option value="mock">Mock Snapshot</option>
                  <option value="live">Live API</option>
                </select>
              </label>
            </div>
            <div>
              <label className="toggle-block">
                <span>Show Owner</span>
                <input
                  type="checkbox"
                  checked={config.showOwner}
                  onChange={(event) => updateConfig("showOwner", event.target.checked)}
                />
              </label>
            </div>
            <div>
              <label className="toggle-block">
                <span>Comparison Mode</span>
                <input
                  aria-label="Comparison Mode"
                  type="checkbox"
                  checked={config.comparisonMode}
                  onChange={(event) => updateConfig("comparisonMode", event.target.checked)}
                />
              </label>
            </div>
            <div className="config-span-two">
              <label className="control-block">
                <span>Subtitle</span>
                <input value={config.subtitle} onChange={(event) => updateConfig("subtitle", event.target.value)} />
              </label>
            </div>
            <div className="config-span-two">
              <label className="control-block">
                <span>API Base URL</span>
                <input
                  aria-label="API Base URL"
                  value={config.apiBaseUrl}
                  onChange={(event) => updateConfig("apiBaseUrl", event.target.value)}
                />
              </label>
            </div>
            {config.comparisonMode ? (
              <div className="config-span-two">
                <label className="control-block">
                  <span>Comparison Station</span>
                  <select
                    aria-label="Comparison Station"
                    value={comparisonStation?.id ?? ""}
                    onChange={(event) => {
                      setComparisonId(event.target.value);
                      updateConfig("comparisonStationId", event.target.value || null);
                    }}
                  >
                    {comparisonCandidates.length === 0 ? <option value="">No comparison stations</option> : null}
                    {comparisonCandidates.map((station) => (
                      <option key={station.id} value={station.id}>
                        {station.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : null}
            <div className="config-span-two">
              <p className="detail-label">Persisted Statuses</p>
              <strong>{selectedStatuses.join(", ")}</strong>
            </div>
            <div>
              <p className="detail-label">Above Threshold</p>
              <strong>{thresholdStations.length}</strong>
            </div>
            <div>
              <p className="detail-label">Saved State</p>
              <strong>Browser Local Storage</strong>
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
                aria-label={`Select ${station.name} in list`}
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
                  <h3>{config.comparisonMode ? "Side-by-Side Comparison" : selectedStation.name}</h3>
                </div>
                <div className="panel-actions">
                  {!config.comparisonMode ? <span className={`status-chip ${selectedStation.status}`}>{selectedStation.status}</span> : null}
                  <button
                    type="button"
                    className="history-button"
                    aria-label={`View history for ${selectedStation.name}`}
                    onClick={() => setIsHistoryOpen(true)}
                  >
                    View History
                  </button>
                </div>
              </div>
              {config.comparisonMode ? (
                <div className="comparison-grid">
                  {renderStationDetailCard(selectedStation, "Primary Station")}
                  {comparisonStation ? (
                    renderStationDetailCard(comparisonStation, "Comparison Station")
                  ) : (
                    <article className="comparison-card comparison-empty">
                      <p className="section-copy">No second station matches the current filters.</p>
                    </article>
                  )}
                </div>
              ) : (
                renderStationDetailCard(selectedStation, "Station Detail")
              )}
            </>
          ) : (
            <p className="section-copy">No station matches the current filters.</p>
          )}
        </section>
      </div>

      {isHistoryOpen && selectedStation ? (
        <div className="modal-overlay" role="presentation" onClick={() => setIsHistoryOpen(false)}>
          <div
            className="history-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="history-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="panel-head">
              <div>
                <p className="eyebrow">Observation History</p>
                <h3 id="history-modal-title">{selectedStation.name} history</h3>
              </div>
              <button type="button" className="history-button" onClick={() => setIsHistoryOpen(false)}>
                Close
              </button>
            </div>
            <div className="history-grid">
              {selectedStation.observations.map((observation) => (
                <article key={`${selectedStation.id}-${observation.observedAt}`} className="history-row">
                  <div>
                    <p className="detail-label">Observed</p>
                    <strong>{observation.observedAt}</strong>
                  </div>
                  <div>
                    <p className="detail-label">Reading</p>
                    <strong>{observation.readingValue} {selectedStation.unit}</strong>
                  </div>
                  <div>
                    <p className="detail-label">Alert Score</p>
                    <strong>{observation.alertScore}</strong>
                  </div>
                  <span className={`status-chip ${observation.status}`}>{observation.status}</span>
                  <p className="section-copy history-note">{observation.note}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}