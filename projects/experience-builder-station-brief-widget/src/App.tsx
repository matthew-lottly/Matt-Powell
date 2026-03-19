import { useEffect, useState } from "react";

import { StationBriefWidget } from "./widget/StationBriefWidget";
import { loadWidgetConfig, saveWidgetConfig } from "./widget/configStorage";
import { defaultConfig, mockStations } from "./widget/mockData";
import type { WidgetConfig } from "./widget/types";


export function App() {
  const [config, setConfig] = useState<WidgetConfig>(() => loadWidgetConfig(defaultConfig));

  useEffect(() => {
    saveWidgetConfig(config);
  }, [config]);

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">ArcGIS UI Demo</p>
          <h1>Experience Builder Station Brief Widget</h1>
          <p className="hero-copy">
            Public-safe React and TypeScript prototype of an ArcGIS Experience Builder style widget for station
            filtering, operational summaries, persisted status filters, and selection-driven station detail panels.
          </p>
        </div>
        <div className="hero-notes">
          <span className="badge">TypeScript</span>
          <span className="badge">React</span>
          <span className="badge">GIS UI</span>
          <span className="badge">Experience Builder Pattern</span>
        </div>
      </section>

      <StationBriefWidget stations={mockStations} config={config} onConfigChange={setConfig} />
    </main>
  );
}