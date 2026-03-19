import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";

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


describe("widget config persistence", () => {
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
});