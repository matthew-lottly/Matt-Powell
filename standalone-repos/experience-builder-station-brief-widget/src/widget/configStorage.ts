import type { WidgetConfig } from "./types";


const STORAGE_KEY = "experience-builder-station-brief-widget:config";


export function loadWidgetConfig(defaultConfig: WidgetConfig): WidgetConfig {
  if (typeof window === "undefined") {
    return defaultConfig;
  }

  const rawValue = window.localStorage.getItem(STORAGE_KEY);
  if (!rawValue) {
    return defaultConfig;
  }

  try {
    const parsed = JSON.parse(rawValue) as Partial<WidgetConfig>;
    return {
      ...defaultConfig,
      ...parsed,
    };
  } catch {
    return defaultConfig;
  }
}


export function saveWidgetConfig(config: WidgetConfig): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}


export function clearWidgetConfig(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(STORAGE_KEY);
}