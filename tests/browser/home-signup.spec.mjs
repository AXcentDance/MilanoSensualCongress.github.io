import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const [path, language] of [['/', 'EN'], ['/it/', 'IT']]) {
  test(`${path}: fixed email invitation scrolls, closes and returns on reload`, async ({ page }) => {
    await page.goto(path);
    const panel = page.locator('#home-signup');
    await expect(panel).toBeVisible();
    await expect(panel).toHaveCSS('position', 'fixed');
    await expect(panel.locator('.home-signup-date')).toHaveText(language === 'IT' ? '19/20/21 novembre 2027' : '19/20/21 November 2027');
    await expect(page.locator('#reminder-container')).toHaveCount(0);
    const before = await panel.boundingBox();
    expect(Math.abs(before.x + before.width / 2 - page.viewportSize().width / 2)).toBeLessThan(2);
    await expect(panel).toHaveCSS('text-align', 'center');
    await expect(panel.locator('label')).toHaveCount(0);
    await expect(panel.locator('input[type=email]')).toHaveAccessibleName(language === 'IT' ? 'Il tuo indirizzo email' : 'Your email address');
    await page.evaluate(() => window.scrollTo({ top: 1500, behavior: 'instant' }));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(1000);
    const after = await panel.boundingBox();
    expect(Math.abs(after.y - before.y)).toBeLessThan(2);
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(1000);
    expect(after.x).toBeGreaterThanOrEqual(0);
    expect(after.x + after.width).toBeLessThanOrEqual(page.viewportSize().width);
    expect(after.y + after.height).toBeLessThanOrEqual(page.viewportSize().height);
    await page.screenshot({ path: `.quality/signup-${language}-${test.info().project.name}.png` });
    await panel.locator('[data-signup-close]').click();
    await expect(panel).toBeHidden();
    await page.reload();
    await expect(panel).toBeVisible();
    await page.goto(path === '/' ? '/it/' : '/');
    await expect(panel).toBeVisible();
  });

  test(`${path}: email invitation validates, retries and confirms only saved signups`, async ({ page }) => {
    let requests = 0;
    let reply = 'error';
    await page.route('https://script.google.com/**', async route => {
      requests++;
      const url = new URL(route.request().url());
      expect(url.searchParams.get('email')).toBe('signup-test@example.com');
      expect(url.searchParams.get('source')).toBe(`Home - ${language} | 2027 news and discounts | email opt-in`);
      await route.fulfill({ status: 200, contentType: 'text/plain', body: reply });
    });
    await page.goto(path);
    const panel = page.locator('#home-signup');
    const email = panel.locator('input[type=email]');
    const submit = panel.locator('button[type=submit]');
    await email.fill('invalid');
    await submit.click();
    expect(requests).toBe(0);
    await email.fill('signup-test@example.com');
    await submit.click();
    await expect(panel.getByRole('alert')).toBeVisible();
    await expect(submit).toBeEnabled();
    await expect(email).toHaveValue('signup-test@example.com');
    reply = 'success';
    await submit.click();
    await expect(panel.getByRole('status')).toContainText(language === 'IT' ? 'Grazie!' : 'Thank you!');
    expect(requests).toBe(2);
    await expect(page.locator('#reminder-form')).toHaveCount(0);
    await page.reload();
    await expect(panel).toBeVisible();
  });

  test(`${path}: invitation remains closable with unavailable storage and Escape`, async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('Storage unavailable'); } });
    });
    await page.goto(path);
    const panel = page.locator('#home-signup');
    await expect(panel).toBeVisible();
    await panel.locator('[data-signup-close]').focus();
    await page.keyboard.press('Escape');
    await expect(panel).toBeHidden();
  });
}
