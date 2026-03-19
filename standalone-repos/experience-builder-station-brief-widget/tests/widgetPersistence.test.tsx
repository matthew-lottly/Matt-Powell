import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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

    firstRender.unmount();

    render(<App />);

    expect(screen.getByDisplayValue("Ops Brief")).toBeInTheDocument();
    expect(screen.getAllByDisplayValue("West")).toHaveLength(2);
    expect(screen.getByLabelText("Show Owner")).not.toBeChecked();
    expect(screen.getAllByText("Sierra Air Quality Node").length).toBeGreaterThan(0);
  });
});