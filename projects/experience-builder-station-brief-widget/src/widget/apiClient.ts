import type {
  ApiObservation,
  ApiObservationExportBundle,
  ApiThreshold,
  StationObservation,
  StationRecord,
  StationStatus,
} from "./types";


function deriveStatus(observation: ApiObservation, threshold: ApiThreshold | undefined): StationStatus {
  if (observation.status === "offline") {
    return "offline";
  }
  if (!threshold || threshold.metricName !== observation.metricName) {
    return observation.status;
  }
  if (threshold.minValue !== null && observation.value < threshold.minValue) {
    return "alert";
  }
  if (threshold.maxValue !== null && observation.value > threshold.maxValue) {
    return "alert";
  }
  return "normal";
}


function deriveAlertScore(observation: ApiObservation, threshold: ApiThreshold | undefined, status: StationStatus): number {
  if (!threshold || threshold.metricName !== observation.metricName) {
    return status === "alert" ? 1 : status === "offline" ? 0.05 : 0.25;
  }
  if (threshold.maxValue !== null) {
    return Number(Math.max(observation.value / threshold.maxValue, 0).toFixed(2));
  }
  if (threshold.minValue !== null) {
    if (observation.value <= 0) {
      return 1;
    }
    return Number(Math.max(threshold.minValue / observation.value, 0).toFixed(2));
  }
  return status === "alert" ? 1 : 0.25;
}


function buildNote(observation: ApiObservation, threshold: ApiThreshold | undefined, status: StationStatus): string {
  if (status === "offline") {
    return `${observation.metricName} telemetry is offline at ${observation.value} ${observation.unit}.`;
  }
  if (threshold?.maxValue !== null && threshold?.maxValue !== undefined) {
    const direction = observation.value > threshold.maxValue ? "above" : "within";
    return `${observation.metricName} is ${direction} the ${threshold.maxValue} ${observation.unit} threshold.`;
  }
  if (threshold?.minValue !== null && threshold?.minValue !== undefined) {
    const direction = observation.value < threshold.minValue ? "below" : "within";
    return `${observation.metricName} is ${direction} the ${threshold.minValue} ${observation.unit} threshold.`;
  }
  return `${observation.metricName} reported ${observation.value} ${observation.unit} with ${status} status.`;
}


function toStationObservation(observation: ApiObservation, threshold: ApiThreshold | undefined): StationObservation {
  const status = deriveStatus(observation, threshold);
  return {
    observedAt: observation.observedAt,
    status,
    alertScore: deriveAlertScore(observation, threshold, status),
    readingValue: observation.value,
    note: buildNote(observation, threshold, status),
  };
}


export function mapExportBundleToStations(bundle: ApiObservationExportBundle): StationRecord[] {
  const thresholdLookup = new Map(bundle.thresholds.map((threshold) => [threshold.featureId, threshold]));
  const groupedObservations = new Map<string, StationObservation[]>();

  for (const observation of bundle.observations.observations) {
    const threshold = thresholdLookup.get(observation.featureId);
    const normalized = toStationObservation(observation, threshold);
    const existing = groupedObservations.get(observation.featureId) ?? [];
    existing.push(normalized);
    existing.sort((left, right) => right.observedAt.localeCompare(left.observedAt));
    groupedObservations.set(observation.featureId, existing);
  }

  return bundle.features.features.map((feature) => {
    const observations = groupedObservations.get(feature.properties.featureId) ?? [];
    const latestObservation = observations[0];
    return {
      id: feature.properties.featureId,
      name: feature.properties.name,
      region: feature.properties.region,
      category: feature.properties.category,
      owner: bundle.source.name,
      status: latestObservation?.status ?? feature.properties.status,
      alertScore: latestObservation?.alertScore ?? 0,
      lastObservedAt: latestObservation?.observedAt ?? feature.properties.lastObservationAt,
      readingValue: latestObservation?.readingValue ?? 0,
      unit: (() => {
        const sourceObservation = bundle.observations.observations.find(
          (entry) => entry.featureId === feature.properties.featureId,
        );
        return sourceObservation?.unit ?? "n/a";
      })(),
      observations,
    };
  });
}


export async function loadStationsFromApi(apiBaseUrl: string): Promise<StationRecord[]> {
  const baseUrl = apiBaseUrl.trim().replace(/\/$/, "");
  const response = await fetch(`${baseUrl}/api/v1/observations/export?format=json`);
  if (!response.ok) {
    throw new Error(`API request failed with ${response.status}`);
  }
  const bundle = await response.json() as ApiObservationExportBundle;
  return mapExportBundleToStations(bundle);
}