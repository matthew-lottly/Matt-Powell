import type { StationRecord, WidgetSummary } from "./types";


export function filterStations(stations: StationRecord[], region: string): StationRecord[] {
  if (region === "All") {
    return stations;
  }
  return stations.filter((station) => station.region === region);
}


export function summarizeStations(stations: StationRecord[]): WidgetSummary {
  const alertStations = stations.filter((station) => station.status === "alert").length;
  const offlineStations = stations.filter((station) => station.status === "offline").length;
  const avgAlertScore = stations.length === 0
    ? 0
    : Number((stations.reduce((total, station) => total + station.alertScore, 0) / stations.length).toFixed(2));

  return {
    totalStations: stations.length,
    alertStations,
    offlineStations,
    avgAlertScore,
  };
}


export function regionsForStations(stations: StationRecord[]): string[] {
  return ["All", ...new Set(stations.map((station) => station.region).sort())];
}