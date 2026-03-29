import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { App } from "../src/App";
import { clearWidgetConfig } from "../src/widget/configStorage";


const storage = new Map<string, string>();

Object.defineProperty(window, "localStorage", {
  value: {
    getItem(key: string) {
      return storage.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      storage.set(key, value);
    },
    removeItem(key: string) {
      storage.delete(key);
    },
  },
  configurable: true,
});

const fetchMock = vi.fn();

Object.defineProperty(globalThis, "fetch", {
  value: fetchMock,
  configurable: true,
});


describe("widget config persistence", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    clearWidgetConfig();
    storage.clear();
  });

  test("restores saved config across remounts", () => {
    const firstRender = render(<App />);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Ops Brief" } });
    fireEvent.change(screen.getByLabelText("Default Region"), { target: { value: "West" } });
    fireEvent.click(screen.getByLabelText("Show Owner"));
    fireEvent.click(screen.getByLabelText("normal status filter"));

    firstRender.unmount();

    render(<App />);

    expect(screen.getByDisplayValue("Ops Brief")).toBeInTheDocument();
    expect(screen.getAllByDisplayValue("West")).toHaveLength(2);
    expect(screen.getByLabelText("Show Owner")).not.toBeChecked();
    expect(screen.getByLabelText("normal status filter")).not.toBeChecked();
    expect(screen.getAllByText("Sierra Air Quality Node").length).toBeGreaterThan(0);
    expect(screen.queryByText("Columbia Basin Sensor")).not.toBeInTheDocument();
  });

  test("opens a station history modal", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Select Sierra Air Quality Node in list" }));
    fireEvent.click(screen.getByRole("button", { name: "View history for Sierra Air Quality Node" }));

    const dialog = screen.getByRole("dialog", { name: "Sierra Air Quality Node history" });

    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText("Smoke plume remains concentrated on the east side of the basin.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(screen.queryByRole("dialog", { name: "Sierra Air Quality Node history" })).not.toBeInTheDocument();
  });

  test("loads stations from the live API export bundle", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        source: {
          name: "environmental-monitoring-api",
          exportedAt: "2026-03-18T14:05:00Z",
          dataSource: "sample_features.geojson",
        },
        features: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              properties: {
                featureId: "station-201",
                name: "Live Delta Station",
                category: "hydrology",
                region: "South",
                status: "normal",
                lastObservationAt: "2026-03-18T14:00:00Z",
              },
              geometry: {
                type: "Point",
                coordinates: [-90.1, 29.9],
              },
            },
          ],
        },
        observations: {
          observations: [
            {
              observationId: "obs-live-1",
              featureId: "station-201",
              observedAt: "2026-03-18T14:00:00Z",
              metricName: "river_stage_ft",
              value: 6.8,
              unit: "ft",
              status: "normal",
            },
          ],
        },
        thresholds: [
          {
            featureId: "station-201",
            metricName: "river_stage_ft",
            minValue: null,
            maxValue: 8,
          },
        ],
      }),
    });

    render(<App />);

    fireEvent.change(screen.getByLabelText("Data Source"), { target: { value: "live" } });

    await waitFor(() => {
      expect(screen.getAllByText("Live Delta Station").length).toBeGreaterThan(0);
    });

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/observations/export?format=json");
    expect(screen.getAllByText("Live API").length).toBeGreaterThan(0);
  });

  test("renders side-by-side comparison mode", () => {
    render(<App />);

    fireEvent.click(screen.getByLabelText("Comparison Mode"));
    fireEvent.change(screen.getByLabelText("Comparison Station"), { target: { value: "station-004" } });

    expect(screen.getByText("Side-by-Side Comparison")).toBeInTheDocument();
    expect(screen.getByText("Primary Station")).toBeInTheDocument();
    expect(screen.getAllByText("Comparison Station").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Columbia Basin Sensor").length).toBeGreaterThan(0);
  });
});