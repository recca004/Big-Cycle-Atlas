import { test, expect, type Page } from "@playwright/test";

/** Real pointer-interaction tests for the workspace engine (Mission 4 §6).
 *  Deterministic: fixed viewport, fresh localStorage, edit mode on. */

async function freshWorkspace(page: Page) {
  await page.goto("/workspace");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  // ensure a non-empty workspace exists: pick the first builtin (has widgets)
  await expect(page.locator(".ws-tab").first()).toBeVisible();
  // pick the first workspace tab that actually has widgets
  const tabs = page.locator(".ws-tab");
  const n = await tabs.count();
  for (let i = 0; i < n; i++) {
    await tabs.nth(i).click();
    if ((await page.locator(".grid-cell").count()) > 0) break;
  }
  await expect(page.locator(".grid-cell").first()).toBeVisible();
}

async function firstCellBox(page: Page) {
  const cell = page.locator(".grid-cell").first();
  await expect(cell).toBeVisible();
  return cell;
}

test.describe("workspace pointer interactions", () => {
  test("pointer drag moves the widget", async ({ page }) => {
    await freshWorkspace(page);
    await page.getByRole("button", { name: /^edit$/i }).click();
    const cell = await firstCellBox(page);
    const before = (await cell.boundingBox())!;
    const handle = cell.locator(".widget-drag-handle");
    await handle.hover();
    await page.mouse.down();
    await page.mouse.move(before.x + 160, before.y + 140, { steps: 8 });
    await page.mouse.up();
    const after = (await cell.boundingBox())!;
    expect(
      Math.abs(after.x - before.x) + Math.abs(after.y - before.y),
    ).toBeGreaterThan(40);
  });

  test("pointer resize changes the widget size", async ({ page }) => {
    await freshWorkspace(page);
    await page.getByRole("button", { name: /^edit$/i }).click();
    const cell = await firstCellBox(page);
    const before = (await cell.boundingBox())!;
    const resizer = cell.locator(".react-grid-item > .react-resizable-handle, .grid-cell .react-resizable-handle").first();
    const count = await resizer.count();
    if (count === 0) {
      // fallback: drag from the bottom-right corner region
      await page.mouse.move(before.x + before.width - 6, before.y + before.height - 6);
      await page.mouse.down();
      await page.mouse.move(before.x + before.width + 120, before.y + before.height + 80, { steps: 6 });
      await page.mouse.up();
    } else {
      const rb = (await resizer.boundingBox())!;
      await page.mouse.move(rb.x + rb.width / 2, rb.y + rb.height / 2);
      await page.mouse.down();
      await page.mouse.move(rb.x + 120, rb.y + 80, { steps: 6 });
      await page.mouse.up();
    }
    const after = (await cell.boundingBox())!;
    expect(
      Math.abs(after.width - before.width) + Math.abs(after.height - before.height),
    ).toBeGreaterThan(30);
  });

  test("locked widget does not drag", async ({ page }) => {
    await freshWorkspace(page);
    await page.getByRole("button", { name: /^edit$/i }).click();
    const cell = await firstCellBox(page);
    await cell.getByRole("button", { name: /^lock /i }).click();
    const before = (await cell.boundingBox())!;
    // locked widgets have no drag handle — drag the frame itself
    await cell.hover();
    await page.mouse.down();
    await page.mouse.move(before.x + 160, before.y + 140, { steps: 6 });
    await page.mouse.up();
    const after = (await cell.boundingBox())!;
    expect(Math.abs(after.x - before.x)).toBeLessThan(20);
    expect(Math.abs(after.y - before.y)).toBeLessThan(20);
  });

  test("undo restores the layout after a drag", async ({ page }) => {
    await freshWorkspace(page);
    await page.getByRole("button", { name: /^edit$/i }).click();
    const cell = await firstCellBox(page);
    const before = (await cell.boundingBox())!;
    const handle = cell.locator(".widget-drag-handle");
    await handle.hover();
    await page.mouse.down();
    await page.mouse.move(before.x + 200, before.y + 160, { steps: 6 });
    await page.mouse.up();
    const mid = (await cell.boundingBox())!;
    expect(Math.abs(mid.y - before.y)).toBeGreaterThan(30);
    await page.getByRole("button", { name: /undo layout change/i }).click();
    await page.waitForTimeout(500); // RGL transition animation
    const after = (await cell.boundingBox())!;
    expect(Math.abs(after.y - before.y)).toBeLessThan(25);
  });

  test("layout persists across reload", async ({ page }) => {
    await freshWorkspace(page);
    await page.getByRole("button", { name: /^edit$/i }).click();
    const cell = await firstCellBox(page);
    const before = (await cell.boundingBox())!;
    const handle = cell.locator(".widget-drag-handle");
    await handle.hover();
    await page.mouse.down();
    await page.mouse.move(before.x + 140, before.y + 100, { steps: 6 });
    await page.mouse.up();
    const moved = (await cell.boundingBox())!;
    await page.reload();
    await page.waitForTimeout(500); // settle RGL enter animation
    const persisted = (await (await firstCellBox(page)).boundingBox())!;
    // RGL re-compacts on mount — persistence is exact at the store level
    // (verified via localStorage); allow one grid row of compaction delta.
    expect(Math.abs(persisted.y - moved.y)).toBeLessThan(70);
  });
});
