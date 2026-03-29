import type { StationRecord, StationStatus, WidgetSummary } from "./types";


export function filterStations(stations: StationRecord[], region: string, statuses: StationStatus[]): StationRecord[] {
  const visibleStatuses = statuses.length === 0 ? ["alert", "normal", "offline"] : statuses;
  return stations.filter((station) => {
    const regionMatches = region === "All" || station.region === region;
    const statusMatches = visibleStatuses.includes(station.status);
    return regionMatches && statusMatches;
  });
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