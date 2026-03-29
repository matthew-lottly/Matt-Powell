import type { DashboardLayer } from "./types";


export function summarizeLayers(layers: DashboardLayer[]) {
  return {
    totalLayers: layers.length,
    totalFeatures: layers.reduce((count, layer) => count + layer.featureCount, 0),
    regionCount: new Set(layers.map((layer) => layer.region)).size,
  };
}
