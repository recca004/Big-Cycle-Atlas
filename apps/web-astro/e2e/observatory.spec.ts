import { test, expect } from "@playwright/test";

/** Observatory homepage e2e — offline clock markers, selection, playback,
 *  camera controls and full-width research sections. */

test.describe("Great Power Observatory homepage", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".obs-app[data-hydrated=\"true\"]")).toBeVisible({ timeout: 15_000 });
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
    await expect(page.locator(".clock-marker-g[role='button']")).toHaveCount(8);
  });

  test("clicking a marker updates the focus panel", async ({ page }) => {
    const marker = page.locator(".clock-marker-g[role='button']").first();
    await marker.click();
    const label = (await marker.getAttribute("aria-label")) ?? "";
    const name = (label.split("—")[0] ?? "").trim();
    await expect(page.locator(".obs-col-left .obs-panel-title")).toContainText(
      name.slice(0, 4),
    );
  });

  test("country dropdown selects a power", async ({ page }) => {
    await page.selectOption("#obs-country-select", "CHN");
    await expect(page.locator(".obs-col-left .obs-panel-title")).toContainText(
      "China",
    );
    await expect(page.locator(".obs-di-card.domestic")).toBeVisible();
    await expect(page.locator(".obs-di-card.international")).toBeVisible();
  });

  test("power transition monitor reports evidence gates, not a countdown", async ({
    page,
  }) => {
    const monitor = page.locator(".obs-monitor");
    await expect(monitor).toContainText("Incumbent under study");
    await expect(monitor).toContainText("Challenger under study");
    await expect(monitor).toContainText("Transition window status");
    await expect(monitor).toContainText("No window issued");
    await expect(monitor).toContainText("offline evidence demonstration");
  });

  test("freshness indicator shows simulated Zurich snapshot state", async ({
    page,
  }) => {
    const fresh = page.locator(".obs-fresh");
    await expect(fresh).toContainText("Data freshness · simulated");
    await expect(fresh).toContainText("CET");
    await expect(fresh.locator(".obs-status")).toBeVisible();
    await expect(fresh).toContainText("Offline fixture");
  });

  test("historical playback scrubs the 1950–2026 demonstration periods", async ({
    page,
  }) => {
    const slider = page.locator(".obs-slider");
    await slider.fill("0");
    await expect(page.locator(".obs-period-label")).toContainText("1950");
    await expect(page.locator(".obs-period-label")).toContainText("historical");
    await expect(page.locator(".obs-clock-hist-badge")).toBeVisible();
    await page.locator("button:has-text('Latest')").click();
    await expect(page.locator(".obs-clock-hist-badge")).toBeHidden();
  });

  test("camera presets and reduced-motion control are available", async ({
    page,
  }) => {
    for (const label of ["Observatory", "Ecliptic", "Armillary", "Beacon"]) {
      await expect(
        page.locator(".obs-camera-presets button", { hasText: label }),
      ).toBeVisible();
    }
    await page.locator("button:text-is('Reduce motion')").click();
    await expect(page.locator("button:text-is('Reduce motion')")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.locator(".obs-speed input")).toBeDisabled();
  });

  test("2D toggle swaps to the SVG fallback", async ({ page }) => {
    await page.locator("button:text-is('2D')").click();
    await expect(page.locator(".obs-clock-canvas")).toHaveCount(0);
    await expect(page.locator(".obs-clock-dial svg")).toBeVisible();
    await expect(page.locator(".clock-marker-g[role='button']")).toHaveCount(8);
  });

  test("full-width sections render powers, measures, forces and history", async ({
    page,
  }) => {
    await expect(page.locator(".obs-powers tbody tr")).toHaveCount(8);
    await expect(page.locator("section[aria-label='What has changed']")).toBeVisible();
    await expect(page.locator(".measure-matrix tbody tr")).toHaveCount(8);
    await expect(page.locator(".force-row")).toHaveCount(17);
    await expect(page.locator(".history-chart")).toBeVisible();
    await expect(page.locator(".history-legend-item")).toHaveCount(8);
  });

  test("homepage makes no backend API requests", async ({ page }) => {
    const apiRequests: string[] = [];
    page.on("request", (request) => {
      const pathname = new URL(request.url()).pathname;
      if (pathname.startsWith("/api/")) apiRequests.push(request.url());
    });
    await page.reload();
    await expect(page.locator(".obs-app[data-hydrated=\"true\"]")).toBeVisible();
    expect(apiRequests).toEqual([]);
  });
});
