import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { App } from "../src/App";


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


afterEach(() => {
  storage.clear();
});


describe("App smoke", () => {
  it("renders the widget concept shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Station Brief Widget Concept" })).toBeInTheDocument();
    expect(screen.getByText("GIS Widget Prototype")).toBeInTheDocument();
  });
});
