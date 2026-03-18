import type { StationRecord, WidgetConfig } from "./types";


export const defaultConfig: WidgetConfig = {
  title: "Station Brief",
  subtitle: "Selection-aware monitoring summary for operations teams.",
  showOwner: true,
  defaultRegion: null,
  alertThreshold: 0.75,
};


export const mockStations: StationRecord[] = [
  {
    id: "station-001",
    name: "Mississippi River Gauge",
    region: "Midwest",
    category: "hydrology",
    owner: "River Operations",
    status: "alert",
    alertScore: 0.81,
    lastObservedAt: "2026-03-18T13:00:00Z",
    readingValue: 7.2,
    unit: "ft",
  },
  {
    id: "station-002",
    name: "Sierra Air Quality Node",
    region: "West",
    category: "air_quality",
    owner: "Air Program",
    status: "alert",
    alertScore: 0.88,
    lastObservedAt: "2026-03-18T13:05:00Z",
    readingValue: 79.3,
    unit: "AQI",
  },
  {
    id: "station-003",
    name: "Boston Harbor Buoy",
    region: "Northeast",
    category: "water_quality",
    owner: "Coastal Monitoring",
    status: "offline",
    alertScore: 0.15,
    lastObservedAt: "2026-03-17T22:30:00Z",
    readingValue: 2.1,
    unit: "mg/L",
  },
  {
    id: "station-004",
    name: "Columbia Basin Sensor",
    region: "West",
    category: "hydrology",
    owner: "River Operations",
    status: "normal",
    alertScore: 0.34,
    lastObservedAt: "2026-03-18T11:15:00Z",
    readingValue: 4.9,
    unit: "ft",
  },
  {
    id: "station-005",
    name: "Gulf Wetlands Monitor",
    region: "South",
    category: "water_quality",
    owner: "Habitat Program",
    status: "alert",
    alertScore: 0.76,
    lastObservedAt: "2026-03-18T10:40:00Z",
    readingValue: 6.8,
    unit: "mg/L",
  },
];