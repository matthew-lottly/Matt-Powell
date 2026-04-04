import { expect, test } from "@playwright/test";


test("opens station history from the list workflow", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Station Brief Widget Concept" })).toBeVisible();
  await page.getByLabel("Select Sierra Air Quality Node in list").click();
  await page.getByLabel("View history for Sierra Air Quality Node").click();

  const dialog = page.getByRole("dialog", { name: "Sierra Air Quality Node history" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Smoke plume remains concentrated on the east side of the basin.")).toBeVisible();
});

test("screenshot: captures the widget default browser view", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Station Brief Widget Concept" })).toBeVisible();
  await page.screenshot({ path: "assets/widget-live-screenshot.png", fullPage: true });
});