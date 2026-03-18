async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed for ${path}`);
  }
  return response.json();
}

function renderRows(targetId, entries) {
  const target = document.getElementById(targetId);
  target.innerHTML = "";
  for (const [label, value] of entries) {
    const row = document.createElement("div");
    row.className = "pill-row";
    row.innerHTML = `<span>${label.replaceAll("_", " ")}</span><strong>${value}</strong>`;
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
      <p>${props.category.replaceAll("_", " ")} monitoring in ${props.region}</p>
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

  for (const observation of observations) {
    const card = document.createElement("article");
    const stationName = featureNames.get(observation.featureId) ?? observation.featureId;
    card.className = "observation-card-item";
    card.innerHTML = `
      <div class="observation-topline">
        <div>
          <h4>${stationName}</h4>
          <p class="observation-copy">${observation.metricName.replaceAll("_", " ")} · ${observation.observedAt}</p>
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
      fetchJson("/api/v1/observations/recent?limit=5"),
    ]);

    document.getElementById("health-indicator").textContent = health.ready ? "Ready" : "Degraded";
    document.getElementById("health-indicator").classList.toggle("alert", !health.ready);
    document.getElementById("health-meta").textContent = `${metadata.name} using ${health.backend} backend · source: ${health.data_source}`;

    document.getElementById("metric-total").textContent = summary.total_features;
    document.getElementById("metric-alerts").textContent = summary.statuses.alert ?? 0;
    document.getElementById("metric-regions").textContent = summary.regions.length;

    renderRows("status-breakdown", Object.entries(summary.statuses));
    renderRows("category-breakdown", Object.entries(summary.categories));
    renderMap(allStations.features);
    renderStations(alerts.features);
    renderObservations(recentObservations.observations, allStations.features);
  } catch (error) {
    document.getElementById("health-indicator").textContent = "Unavailable";
    document.getElementById("health-indicator").classList.add("alert");
    document.getElementById("health-meta").textContent = error.message;
  }
}

initDashboard();