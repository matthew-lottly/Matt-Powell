import { render, screen } from "@testing-library/react";

import { App } from "../src/App";


describe("App smoke", () => {
  it("renders the dashboard shell and visible layer summary", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Operations Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Visible Layers")).toBeInTheDocument();
  });
});
