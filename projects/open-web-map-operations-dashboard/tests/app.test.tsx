import { render, screen } from "@testing-library/react";

import { App } from "../src/App";


describe("App", () => {
  it("renders the dashboard heading and layers", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Operations Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Monitoring Sites")).toBeInTheDocument();
    expect(screen.getByText("Smoke Operations")).toBeInTheDocument();
  });
});
