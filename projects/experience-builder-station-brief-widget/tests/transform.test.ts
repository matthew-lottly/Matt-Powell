import { describe, expect, test } from "vitest";

import { mockStations } from "../src/widget/mockData";
import { filterStations, regionsForStations, summarizeStations } from "../src/widget/transform";


describe("station brief widget transforms", () => {
  test("filters by region", () => {
    const filtered = filterStations(mockStations, "West");
    expect(filtered).toHaveLength(2);
    expect(filtered[0].id).toBe("station-002");
  });

  test("summarizes stations", () => {
    const summary = summarizeStations(mockStations);
    expect(summary.totalStations).toBe(5);
    expect(summary.alertStations).toBe(3);
    expect(summary.offlineStations).toBe(1);
    expect(summary.avgAlertScore).toBe(0.59);
  });

  test("lists regions with All first", () => {
    expect(regionsForStations(mockStations)).toEqual(["All", "Midwest", "Northeast", "South", "West"]);
  });
});