export type LayerStatus = "active" | "review" | "offline";

export interface DashboardLayer {
  id: string;
  title: string;
  region: string;
  status: LayerStatus;
  format: string;
  featureCount: number;
  coordinates: {
    longitude: number;
    latitude: number;
  };
  center: {
    x: number;
    y: number;
  };
}
