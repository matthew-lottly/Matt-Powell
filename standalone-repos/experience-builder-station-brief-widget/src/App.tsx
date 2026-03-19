import { useEffect, useState } from "react";

import { StationBriefWidget } from "./widget/StationBriefWidget";
import { loadStationsFromApi } from "./widget/apiClient";
import { loadWidgetConfig, saveWidgetConfig } from "./widget/configStorage";
import { defaultConfig, mockStations } from "./widget/mockData";
import type { StationRecord, WidgetConfig } from "./widget/types";


export function App() {
  const [config, setConfig] = useState<WidgetConfig>(() => loadWidgetConfig(defaultConfig));
  const [stations, setStations] = useState<StationRecord[]>(mockStations);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    saveWidgetConfig(config);
  }, [config]);

  useEffect(() => {
    let isMounted = true;

    async function refreshStations() {
      if (config.dataSource === "mock") {
        setStations(mockStations);
        setLoadError(null);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const nextStations = await loadStationsFromApi(config.apiBaseUrl);
        if (!isMounted) {
          return;
        }
        setStations(nextStations);
        setLoadError(null);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setStations(mockStations);
        setLoadError(error instanceof Error ? error.message : "Live API request failed.");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void refreshStations();

    return () => {
      isMounted = false;
    };
  }, [config.apiBaseUrl, config.dataSource]);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">ArcGIS UI Demo</p>
          <h1>Experience Builder Station Brief Widget</h1>
          <p className="hero-copy">
            Public-safe React and TypeScript prototype of an ArcGIS Experience Builder style widget for station
            filtering, operational summaries, persisted status filters, live API snapshot loading, and selection-driven
            station detail panels.
          </p>
        </div>
        <div className="hero-notes">
          <span className="badge">TypeScript</span>
          <span className="badge">React</span>
          <span className="badge">GIS UI</span>
          <span className="badge">Experience Builder Pattern</span>
        </div>
      </section>

      <StationBriefWidget
        stations={stations}
        config={config}
        isLoading={isLoading}
        loadError={loadError}
        onConfigChange={setConfig}
      />
    </main>
  );
}