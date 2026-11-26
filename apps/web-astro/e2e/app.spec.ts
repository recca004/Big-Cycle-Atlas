import { test, expect } from "@playwright/test";

const ROUTES = [
  "/",
  "/countries",
  "/country/USA",
  "/country/CHN",
  "/country/DEU",
  "/country/JPN",
  "/country/GBR",
  "/country/FRA",
  "/country/IND",
  "/country/CHE",
  "/forces",
  "/workspace",
  "/compare",
  "/cycle",
  "/forecast",
  "/markets",
  "/strategies",
  "/portfolio",
  "/watchlist",
  "/economy",
  "/debt",
  "/trade",
  "/data",
  "/sources",
  "/methodology",
  "/progress",
  "/research/validation",
  "/research/debt-cycle",
  "/research/historical-power",
  "/settings",
];

test.describe("route availability", () => {
  for (const route of ROUTES) {
    test(`${route} loads without console errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      const res = await page.goto(route);
      expect(res?.status()).toBe(200);
      await page.waitForLoadState("networkidle");
      expect(errors).toEqual([]);
    });
  }
});

test.describe("live API data", () => {
  test("country profile renders real metrics", async ({ page }) => {
    await page.goto("/country/USA");
    await expect(page.getByText("United States")).toBeVisible();
    await expect(page.getByText(/World Bank/).first()).toBeVisible();
    // GDP metric populated from API
    await expect(page.getByText(/\$30\.\d+T/).first()).toBeVisible();
  });

  test("force scores render with model version", async ({ page }) => {
    await page.goto("/country/USA/forces");
    await expect(page.getByText(/Rule of law/i).first()).toBeVisible();
    await expect(
      page.locator(".status-pill", { hasText: /available/i }).first(),
    ).toBeVisible();
  });

  test("validation registry renders a stable question URL", async ({ page }) => {
    await page.goto("/research/validation?question=Q11");
    await expect(page.getByRole("heading", { name: "Theory Validation" })).toBeVisible();
    await expect(page.locator("article")).toContainText("Q11");
    await expect(page.locator("article")).toContainText(/Evaluation implemented/i);
  });

  test("compare page renders cross-country bars", async ({ page }) => {
    await page.goto("/compare");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/Indebtedness/i).first()).toBeVisible();
  });
});

test.describe("workspace", () => {
  test("workspace loads widgets and persists across reload", async ({
    page,
  }) => {
    await page.goto("/workspace");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Debt and Credit Monitor")).toBeVisible();
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Debt and Credit Monitor")).toBeVisible();
  });

  test("edit mode toggles and widgets show controls", async ({ page }) => {
    await page.goto("/workspace");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: /edit/i }).first().click();
    await expect(
      page.locator(".react-grid-item .widget-drag-handle").first(),
    ).toBeVisible();
  });
});

test.describe("theme", () => {
  test("dark and light themes apply", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() =>
      localStorage.setItem("bca:theme", "dark"),
    );
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute(
      "data-theme",
      "dark",
    );
    await page.evaluate(() =>
      localStorage.setItem("bca:theme", "light"),
    );
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute(
      "data-theme",
      "light",
    );
  });
});

test.describe("mobile", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("country page is usable at 390px", async ({ page }) => {
    await page.goto("/country/USA");
    await expect(page.getByText("United States")).toBeVisible();
    await expect(page.getByText(/GDP growth/i).first()).toBeVisible();
  });
});
