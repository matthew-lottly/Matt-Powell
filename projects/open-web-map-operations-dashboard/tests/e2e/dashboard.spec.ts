import { expect, test } from "@playwright/test";


test("filters the dashboard by region and status", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Operations Dashboard" })).toBeVisible();

  await page.getByLabel("Region").selectOption("West");
  await page.getByLabel("Status").selectOption("active");

  await expect(page.getByText("Monitoring Sites")).toBeVisible();
  await expect(page.getByText("Smoke Operations")).toHaveCount(0);
  await expect(page.locator(".summary-card strong").first()).toHaveText("1");
});

test("screenshot: captures the default dashboard review state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Operations Dashboard" })).toBeVisible();
  await page.screenshot({ path: "assets/dashboard-live-screenshot.png", fullPage: true });
});