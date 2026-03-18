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

async function initDashboard() {
  try {
    const [health, metadata, summary, alerts] = await Promise.all([
      fetchJson("/health/ready"),
      fetchJson("/api/v1/metadata"),
      fetchJson("/api/v1/features/summary"),
      fetchJson("/api/v1/features?status=alert"),
    ]);

    document.getElementById("health-indicator").textContent = health.ready ? "Ready" : "Degraded";
    document.getElementById("health-indicator").classList.toggle("alert", !health.ready);
    document.getElementById("health-meta").textContent = `${metadata.name} using ${health.backend} backend · source: ${health.data_source}`;

    document.getElementById("metric-total").textContent = summary.total_features;
    document.getElementById("metric-alerts").textContent = summary.statuses.alert ?? 0;
    document.getElementById("metric-regions").textContent = summary.regions.length;

    renderRows("status-breakdown", Object.entries(summary.statuses));
    renderRows("category-breakdown", Object.entries(summary.categories));
    renderStations(alerts.features);
  } catch (error) {
    document.getElementById("health-indicator").textContent = "Unavailable";
    document.getElementById("health-indicator").classList.add("alert");
    document.getElementById("health-meta").textContent = error.message;
  }
}

initDashboard();