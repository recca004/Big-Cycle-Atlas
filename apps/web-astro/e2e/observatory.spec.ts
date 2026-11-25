import { test, expect } from "@playwright/test";

/** Observatory homepage e2e — clock markers, selection, playback,
 *  panels. Runs against the prod server (API same-origin). */

test.describe("Great Power Observatory homepage", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // The overview endpoint computes composites on first hit (~20s cold).
    await expect(page.locator(".obs-app")).toBeVisible({ timeout: 120_000 });
  });

  test("dial renders all eight stage labels and country markers", async ({
    page,
  }) => {
    const svg = page.locator(".obs-clock-dial svg");
    for (const label of [
      "Early rise",
      "Rise",
      "Late rise",
      "Peak",
      "Late peak",
      "Early decline",
      "Decline",
      "Reset",
    ]) {
      await expect(
        svg.locator("text", { hasText: new RegExp(`^${label}`) }),
      ).toBeVisible();
    }
    await expect(
      page.locator(".clock-marker-g[role='button']"),
    ).toHaveCount(8, { timeout: 15_000 });
  });

  test("clicking a marker updates the focus panel", async ({ page }) => {
    const marker = page
      .locator(".clock-marker-g[role='button']")
      .first();
    await marker.click();
    const label = (await marker.getAttribute("aria-label")) ?? "";
    const name = (label.split("—")[0] ?? "").trim();
    await expect(
      page.locator(".obs-col-left .obs-panel-title"),
    ).toContainText(name.slice(0, 4));
  });

  test("country dropdown selects a power", async ({ page }) => {
    await page.selectOption("#obs-country-select", "CHN");
    await expect(
      page.locator(".obs-col-left .obs-panel-title"),
    ).toContainText("China");
  });

  test("power transition monitor reports evidence gates, not a countdown", async ({
    page,
  }) => {
    const monitor = page.locator(".obs-monitor");
    await expect(monitor).toContainText("Incumbent under study");
    await expect(monitor).toContainText("Challenger under study");
    await expect(monitor).toContainText("Estimated transition window");
    await expect(monitor).toContainText("Not estimable");
  });

  test("freshness indicator shows collection state", async ({ page }) => {
    const fresh = page.locator(".obs-fresh");
    await expect(fresh).toContainText("Data freshness");
    await expect(fresh.locator(".obs-status")).toBeVisible();
  });

  test("historical playback scrubs through real periods", async ({
    page,
  }) => {
    const slider = page.locator(".obs-slider");
    await slider.fill("0");
    await expect(page.locator(".obs-playback-period")).toContainText(
      "historical classifications",
    );
    await expect(page.locator(".obs-clock-hist-badge")).toBeVisible();
    await page.locator("button:has-text('Latest')").click();
    await expect(page.locator(".obs-clock-hist-badge")).toBeHidden();
  });

  test("2D toggle swaps to the SVG fallback", async ({ page }) => {
    await page.locator("button:has-text('2D')").click();
    await expect(page.locator(".obs-clock-canvas")).toBeHidden();
    await expect(page.locator(".obs-clock-dial svg")).toBeVisible();
  });

  test("below-the-fold sections render powers table and changes", async ({
    page,
  }) => {
    await expect(
      page.locator(".obs-powers tbody tr"),
    ).toHaveCount(8);
    await expect(
      page.locator("section[aria-label='What has changed']"),
    ).toBeVisible();
  });
});
