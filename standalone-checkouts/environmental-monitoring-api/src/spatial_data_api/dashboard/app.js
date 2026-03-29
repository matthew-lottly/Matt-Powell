async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed for ${path}`);
  }
  return response.json();
}

function formatLabel(value) {
  return value.replaceAll("_", " ");
}

function renderRows(targetId, entries) {
  const target = document.getElementById(targetId);
  target.innerHTML = "";
  for (const [label, value] of entries) {
    const row = document.createElement("div");
    row.className = "pill-row";
    row.innerHTML = `<span>${formatLabel(label)}</span><strong>${value}</strong>`;
    target.appendChild(row);
  }
}

function renderStations(features) {
  const target = document.getElementById("alert-stations");
  target.innerHTML = "";

  if (features.length === 0) {
    target.innerHTML = '<div class="station-card"><h4>No active alerts</h4><p>All stations are in normal or offline states.</p></div>';
    return;
  }

  for (const feature of features) {
    const card = document.createElement("article");
    const props = feature.properties;
    card.className = "station-card";
    card.innerHTML = `
      <h4>${props.name}</h4>
      <p>${formatLabel(props.category)} monitoring in ${props.region}</p>
      <div class="station-meta">
        <span class="meta-chip">${props.status}</span>
        <span class="meta-chip">Observed ${props.lastObservationAt}</span>
        <span class="meta-chip">${props.featureId}</span>
      </div>
    `;
    target.appendChild(card);
  }
}

function formatObservationValue(observation) {
  return `${observation.value} ${observation.unit}`;
}

function renderObservations(observations, features) {
  const target = document.getElementById("recent-observations");
  target.innerHTML = "";

  const featureNames = new Map(features.map((feature) => [feature.properties.featureId, feature.properties.name]));

  for (const observation of observations.slice(0, 5)) {
    const card = document.createElement("article");
    const stationName = featureNames.get(observation.featureId) ?? observation.featureId;
    card.className = "observation-card-item";
    card.innerHTML = `
      <div class="observation-topline">
        <div>
          <h4>${stationName}</h4>
          <p class="observation-copy">${formatLabel(observation.metricName)} · ${observation.observedAt}</p>
        </div>
        <div class="observation-value">${formatObservationValue(observation)}</div>
      </div>
      <div class="station-meta">
        <span class="meta-chip">${observation.status}</span>
        <span class="meta-chip">${observation.featureId}</span>
      </div>
    `;
    target.appendChild(card);
  }
}

function renderObservationSummary(summary, observations) {
  const target = document.getElementById("observation-summary");
  const alertCount = summary.statuses.alert ?? 0;
  target.innerHTML = `
    <article class="summary-tile tone-slate">
      <p class="summary-label">Window</p>
      <strong>${summary.totalObservations}</strong>
      <span>${observations.length} observations loaded for dashboard analysis</span>
    </article>
    <article class="summary-tile tone-alert">
      <p class="summary-label">Alerts</p>
      <strong>${alertCount}</strong>
      <span>Alert readings in the current recent-observation window</span>
    </article>
    <article class="summary-tile tone-moss">
      <p class="summary-label">Metrics</p>
      <strong>${Object.keys(summary.metrics).length}</strong>
      <span>${Object.keys(summary.categories).map(formatLabel).join(", ")}</span>
    </article>
    <article class="summary-tile tone-sand">
      <p class="summary-label">Observed Range</p>
      <strong>${summary.latestObservedAt ?? "--"}</strong>
      <span>Earliest in window: ${summary.earliestObservedAt ?? "--"}</span>
    </article>
  `;
}

function renderRecentAlertFocus(observations, features) {
  const target = document.getElementById("recent-alert-focus");
  target.innerHTML = "";

  const featureLookup = new Map(
    features.map((feature) => [feature.properties.featureId, feature.properties]),
  );
  const alertObservations = observations.filter((observation) => observation.status === "alert").slice(0, 3);

  if (alertObservations.length === 0) {
    target.innerHTML = '<div class="signal-card empty-state"><h4>No recent alert readings</h4><p>The current recent-observation window contains only normal or offline readings.</p></div>';
    return;
  }

  for (const observation of alertObservations) {
    const feature = featureLookup.get(observation.featureId);
    const card = document.createElement("article");
    card.className = "signal-card signal-alert";
    card.innerHTML = `
      <div class="signal-topline">
        <div>
          <h4>${feature?.name ?? observation.featureId}</h4>
          <p>${formatLabel(feature?.category ?? "unknown")} in ${feature?.region ?? "unknown region"}</p>
        </div>
        <span class="signal-value">${formatObservationValue(observation)}</span>
      </div>
      <div class="station-meta">
        <span class="meta-chip alert-chip">${formatLabel(observation.metricName)}</span>
        <span class="meta-chip alert-chip">${observation.observedAt}</span>
      </div>
    `;
    target.appendChild(card);
  }
}

function renderStatusShifts(observations, features) {
  const target = document.getElementById("status-shifts");
  target.innerHTML = "";

  const featureLookup = new Map(
    features.map((feature) => [feature.properties.featureId, feature.properties]),
  );
  const grouped = new Map();

  for (const observation of observations) {
    const stationObservations = grouped.get(observation.featureId) ?? [];
    stationObservations.push(observation);
    grouped.set(observation.featureId, stationObservations);
  }

  const shifts = [];
  for (const [featureId, stationObservations] of grouped.entries()) {
    if (stationObservations.length < 2) {
      continue;
    }
    const [latest, previous] = stationObservations;
    if (latest.status === previous.status) {
      continue;
    }
    shifts.push({ featureId, latest, previous, feature: featureLookup.get(featureId) });
  }

  if (shifts.length === 0) {
    target.innerHTML = '<div class="signal-card empty-state"><h4>No recent status changes</h4><p>The loaded recent-observation window does not yet include two differing statuses for the same station.</p></div>';
    return;
  }

  for (const shift of shifts) {
    const card = document.createElement("article");
    card.className = "signal-card signal-shift";
    card.innerHTML = `
      <div class="signal-topline">
        <div>
          <h4>${shift.feature?.name ?? shift.featureId}</h4>
          <p>${formatLabel(shift.feature?.category ?? "unknown")} monitoring</p>
        </div>
        <span class="signal-value">${shift.latest.observedAt}</span>
      </div>
      <p class="signal-copy">Status changed from <strong>${shift.previous.status}</strong> to <strong>${shift.latest.status}</strong> between the two most recent readings in the current window.</p>
      <div class="station-meta">
        <span class="meta-chip">Previous: ${shift.previous.observedAt}</span>
        <span class="meta-chip">Latest metric: ${formatLabel(shift.latest.metricName)}</span>
      </div>
    `;
    target.appendChild(card);
  }
}

function projectPoint([longitude, latitude]) {
  const x = ((longitude + 130) / 70) * 640;
  const y = ((52 - latitude) / 27) * 320;
  return [x, y];
}

function renderMap(features) {
  const map = document.getElementById("station-map");
  map.innerHTML = `
    <rect x="0" y="0" width="640" height="320" fill="rgba(255,255,255,0.2)"></rect>
    <path class="map-region" d="M88 228 L118 160 L176 126 L248 112 L326 106 L403 114 L478 109 L551 126 L534 181 L466 208 L413 251 L337 266 L257 257 L182 250 Z"></path>
    <path class="map-region" d="M338 266 L374 242 L420 234 L466 208 L525 194 L564 214 L541 255 L468 281 L400 282 Z"></path>
    <text class="map-label" x="120" y="102">West</text>
    <text class="map-label" x="260" y="92">Midwest</text>
    <text class="map-label" x="460" y="96">Northeast</text>
    <text class="map-label" x="430" y="294">South</text>
  `;

  for (const feature of features) {
    const [x, y] = projectPoint(feature.geometry.coordinates);
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(x));
    dot.setAttribute("cy", String(y));
    dot.setAttribute("r", "7");
    dot.setAttribute("class", `map-dot ${feature.properties.status}`);
    map.appendChild(dot);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(x + 10));
    label.setAttribute("y", String(y - 10));
    label.setAttribute("class", "map-caption");
    label.textContent = feature.properties.name;
    map.appendChild(label);
  }
}

async function initDashboard() {
  try {
    const [health, metadata, summary, allStations, alerts, recentObservations] = await Promise.all([
      fetchJson("/health/ready"),
      fetchJson("/api/v1/metadata"),
      fetchJson("/api/v1/features/summary"),
      fetchJson("/api/v1/features"),
      fetchJson("/api/v1/features?status=alert"),
      fetchJson("/api/v1/observations/recent?limit=8"),
    ]);

    document.getElementById("health-indicator").textContent = health.ready ? "Ready" : "Degraded";
    document.getElementById("health-indicator").classList.toggle("alert", !health.ready);
    document.getElementById("health-meta").textContent = `${metadata.name} using ${health.backend} backend · source: ${health.data_source}`;

    document.getElementById("metric-total").textContent = summary.total_features;
    document.getElementById("metric-alerts").textContent = summary.statuses.alert ?? 0;
    document.getElementById("metric-regions").textContent = summary.regions.length;

    renderRows("status-breakdown", Object.entries(summary.statuses));
    renderMap(allStations.features);
    renderStations(alerts.features);
    renderObservationSummary(recentObservations.summary, recentObservations.observations);
    renderRecentAlertFocus(recentObservations.observations, allStations.features);
    renderObservations(recentObservations.observations, allStations.features);
    renderStatusShifts(recentObservations.observations, allStations.features);
  } catch (error) {
    document.getElementById("health-indicator").textContent = "Unavailable";
    document.getElementById("health-indicator").classList.add("alert");
    document.getElementById("health-meta").textContent = error.message;
  }
}

initDashboard();