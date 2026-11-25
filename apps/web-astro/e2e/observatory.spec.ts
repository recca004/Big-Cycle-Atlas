import { test, expect } from "@playwright/test";

test.describe("Great Power Observatory homepage — production", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".obs-app[data-hydrated=\"true\"]")).toBeVisible({ timeout: 90_000 });
  });

  test("dial renders all eight stages and country markers", async ({ page }) => {
    const svg = page.locator(".obs-clock-dial svg");
    for (const label of ["Early rise", "Rise", "Late rise", "Peak", "Late peak", "Early decline", "Decline", "Reset"]) {
      await expect(svg.locator("text", { hasText: new RegExp(`^${label}`) })).toBeVisible();
    }
    await expect(page.locator(".clock-marker-g[role='button']")).toHaveCount(8);
  });

  test("marker and dropdown selection update the focus panel", async ({ page }) => {
    const marker = page.locator(".clock-marker-g[role='button']").first();
    await marker.click();
    await expect(page.locator(".obs-col-left .obs-panel-title")).not.toBeEmpty();
    await page.selectOption("#obs-country-select", "CHN");
    await expect(page.locator(".obs-col-left .obs-panel-title")).toContainText("China");
    await expect(page.locator(".obs-di-card.domestic")).toBeVisible();
    await expect(page.locator(".obs-di-card.international")).toBeVisible();
  });

  test("power transition monitor reports production evidence gates", async ({ page }) => {
    const monitor = page.locator(".obs-monitor");
    await expect(monitor).toContainText("Incumbent under study");
    await expect(monitor).toContainText("Challenger under study");
    await expect(monitor).toContainText("Transition window status");
    await expect(monitor).toContainText(/No window issued|Not estimable|insufficient/i);
  });

  test("freshness shows production Zurich metadata and revision state", async ({ page }) => {
    const fresh = page.locator(".obs-fresh");
    await expect(fresh.locator(".obs-panel-title")).toHaveText("Data freshness");
    await expect(fresh).toContainText("CET");
    await expect(fresh.locator(".obs-status")).toBeVisible();
    await expect(fresh).toContainText("Production collection workflow");
  });

  test("historical playback scrubs real classified periods", async ({ page }) => {
    const slider = page.locator(".obs-slider");
    await slider.fill("0");
    await expect(page.locator(".obs-period-label")).toContainText(/2000|historical/);
    await expect(page.locator(".obs-clock-hist-badge")).toBeVisible();
    await page.locator("button:has-text('Latest')").click();
    await expect(page.locator(".obs-clock-hist-badge")).toBeHidden();
  });

  test("camera presets, reduced motion and 2D fallback are available", async ({ page }) => {
    for (const label of ["Observatory", "Ecliptic", "Armillary", "Beacon"]) {
      await expect(page.locator(".obs-camera-presets button", { hasText: label })).toBeVisible();
    }
    await page.locator("button:text-is('Reduce motion')").click();
    await expect(page.locator("button:text-is('Reduce motion')")).toHaveAttribute("aria-pressed", "true");
    await page.locator("button:text-is('2D')").click();
    await expect(page.locator(".obs-clock-canvas")).toHaveCount(0);
    await expect(page.locator(".clock-marker-g[role='button']")).toHaveCount(8);
  });

  test("full-width sections render real powers, measures, forces and history", async ({ page }) => {
    await expect(page.locator(".obs-powers tbody tr")).toHaveCount(8);
    await expect(page.locator("section[aria-label='What has changed']")).toBeVisible();
    await expect(page.locator(".measure-matrix tbody tr")).toHaveCount(8);
    await expect(page.locator(".force-row")).toHaveCount(17);
    await expect(page.locator(".history-chart")).toBeVisible();
    await expect(page.locator(".history-legend-item")).toHaveCount(8);
  });

  test("homepage requests the production overview", async ({ page }) => {
    const requests: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).pathname === "/api/observatory/overview") requests.push(request.url());
    });
    await page.reload();
    await expect(page.locator(".obs-app[data-source=\"production\"]")).toBeVisible({ timeout: 90_000 });
    expect(requests.length).toBeGreaterThan(0);
  });

  test("an API failure shows unavailable state instead of demo data", async ({ page }) => {
    await page.route("**/api/observatory/overview**", (route) => route.abort());
    await page.goto("/");
    await expect(page.locator(".obs-error")).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("body")).toContainText("No offline demonstration values were substituted");
  });
});

test.describe("Great Power Observatory homepage — explicit demo", () => {
  test("demo mode is labelled and isolated from the backend", async ({ page }) => {
    const apiRequests: string[] = [];
    page.on("request", (request) => {
      if (new URL(request.url()).pathname.startsWith("/api/")) apiRequests.push(request.url());
    });
    await page.goto("/?demo=1");
    await expect(page.locator(".obs-app[data-source=\"demo\"]")).toBeVisible();
    await expect(page.locator(".obs-demo-banner")).toContainText("Demonstration fixture");
    await expect(page.locator(".force-row")).toHaveCount(17);
    expect(apiRequests).toEqual([]);
  });
});
