export type StationStatus = "normal" | "alert" | "offline";


export interface StationObservation {
  observedAt: string;
  status: StationStatus;
  alertScore: number;
  readingValue: number;
  note: string;
}


export interface StationRecord {
  id: string;
  name: string;
  region: string;
  category: string;
  owner: string;
  status: StationStatus;
  alertScore: number;
  lastObservedAt: string;
  readingValue: number;
  unit: string;
  observations: StationObservation[];
}


export interface WidgetConfig {
  title: string;
  subtitle: string;
  showOwner: boolean;
  defaultRegion: string | null;
  alertThreshold: number;
  defaultStatuses: StationStatus[];
}


export interface WidgetSummary {
  totalStations: number;
  alertStations: number;
  offlineStations: number;
  avgAlertScore: number;
}