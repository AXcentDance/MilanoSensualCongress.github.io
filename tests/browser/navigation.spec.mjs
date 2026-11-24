import { test, expect } from '@playwright/test';

for (const path of ['/', '/it/']) {
  for (const javaScriptEnabled of [true, false]) {
    test(`${path}: homepage link works with JavaScript ${javaScriptEnabled ? 'enabled' : 'disabled'}`, async ({ browser, baseURL }, info) => {
      const context = await browser.newContext({ javaScriptEnabled, viewport: info.project.use.viewport });
      try {
        await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
        const page = await context.newPage();
        await page.goto(baseURL + path);
        const home = page.locator('nav.e27-nav a');
        await expect(home).toHaveCount(1);
        await expect(home).toHaveAttribute('href', path);
        await expect(home).toHaveAccessibleName(/Milano Sensual Congress.*2027.*Home/);
        await expect(home).toBeVisible();
        await expect(page.locator('nav.e27-nav button, #mobile-menu')).toHaveCount(0);
        const bounds = await home.boundingBox();
        expect(bounds.height).toBeGreaterThanOrEqual(44);
        expect(bounds.x).toBeGreaterThanOrEqual(0);
        expect(bounds.x + bounds.width).toBeLessThanOrEqual(page.viewportSize().width);
        await home.focus();
        await page.keyboard.press('Enter');
        await expect(page).toHaveURL(baseURL + path);
        await expect(page.locator('h1')).toBeVisible();
      } finally { await context.close(); }
    });
  }
}
