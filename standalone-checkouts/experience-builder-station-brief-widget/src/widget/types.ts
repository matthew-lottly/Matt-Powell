export type StationStatus = "normal" | "alert" | "offline";


export type WidgetDataSource = "mock" | "live";


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
  dataSource: WidgetDataSource;
  apiBaseUrl: string;
  comparisonMode: boolean;
  comparisonStationId: string | null;
}


export interface WidgetSummary {
  totalStations: number;
  alertStations: number;
  offlineStations: number;
  avgAlertScore: number;
}


export interface ApiThreshold {
  featureId: string;
  metricName: string;
  minValue: number | null;
  maxValue: number | null;
}


export interface ApiFeature {
  type: "Feature";
  properties: {
    featureId: string;
    name: string;
    category: string;
    region: string;
    status: StationStatus;
    lastObservationAt: string;
  };
  geometry: {
    type: string;
    coordinates: number[];
  };
}


export interface ApiObservation {
  observationId: string;
  featureId: string;
  observedAt: string;
  metricName: string;
  value: number;
  unit: string;
  status: StationStatus;
}


export interface ApiObservationExportBundle {
  source: {
    name: string;
    exportedAt: string;
    dataSource: string;
  };
  features: {
    type: "FeatureCollection";
    features: ApiFeature[];
  };
  observations: {
    observations: ApiObservation[];
  };
  thresholds: ApiThreshold[];
}