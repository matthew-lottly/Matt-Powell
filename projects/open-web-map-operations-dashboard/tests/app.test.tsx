import { fireEvent, render, screen, within } from "@testing-library/react";

import { App } from "../src/App";


describe("App", () => {
  it("filters layers by region and status and updates the summary", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Operations Dashboard" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Region"), { target: { value: "West" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "active" } });

    const summaryGrid = screen.getByText("Visible Layers").closest("section");
    expect(summaryGrid).not.toBeNull();
    const summary = within(summaryGrid as HTMLElement);
    expect(summary.getAllByText("1")).toHaveLength(2);

    expect(screen.getByText("Monitoring Sites")).toBeInTheDocument();
    expect(screen.queryByText("Smoke Operations")).not.toBeInTheDocument();
    expect(screen.queryByText("Utility Constraints")).not.toBeInTheDocument();
  });
});
