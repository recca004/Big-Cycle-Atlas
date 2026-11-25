import { test, expect } from '@playwright/test';

const PAGES = ['/forecast', '/markets', '/strategies', '/portfolio', '/watchlist'];

for (const path of PAGES) {
  test(`a11y audit ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    // Extension overlays inject content outside <main>; scope all checks.
    const issues = await page.locator('main').evaluate((root) => {
      const out: string[] = [];
      if (root.querySelectorAll('h1').length !== 1)
        out.push(`h1 count = ${root.querySelectorAll('h1').length}`);
      root.querySelectorAll('input, select, textarea').forEach((el) => {
        const named = el.id && root.querySelector(`label[for="${el.id}"]`)
          || el.getAttribute('aria-label')
          || el.closest('label');
        if (!named) out.push(`unnamed ${el.tagName.toLowerCase()} (${(el as HTMLElement).className || 'no class'})`);
      });
      root.querySelectorAll('button').forEach((b) => {
        if (!b.textContent?.trim() && !b.getAttribute('aria-label'))
          out.push('button with no accessible name');
      });
      root.querySelectorAll('img').forEach((i) => {
        if (!i.hasAttribute('alt')) out.push('img without alt');
      });
      return out;
    });
    expect(issues, `${path}: ${issues.join('; ')}`).toEqual([]);
  });
}
