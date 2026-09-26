import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
});

for (const path of ['/', '/it/']) {
  test(`${path}: short viewport keeps the last mobile navigation link reachable`, async ({ page, browserName }, info) => {
    await page.setViewportSize({ width: Math.min(info.project.use.viewport.width, 812), height: 375 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(path);
    const button = page.locator('button[aria-controls="mobile-menu"]');
    await button.focus();
    await page.keyboard.press('Enter');
    await expect(button).toHaveAttribute('aria-expanded', 'true');
    const links = page.locator('#mobile-menu a');
    // macOS WebKit uses Option+Tab to include links in keyboard navigation.
    const nextLink = browserName === 'webkit' && process.platform === 'darwin' ? 'Alt+Tab' : 'Tab';
    for (let index = 0; index < await links.count(); index++) await page.keyboard.press(nextLink);
    const last = links.last();
    await expect(last).toBeFocused();
    await expect(last).toBeInViewport({ ratio: 1 });
    await expect.poll(() => page.locator('body > nav').evaluate(nav => nav.getBoundingClientRect().bottom <= innerHeight + 1)).toBe(true);

    const language = page.locator(`#mobile-menu a[href="${path === '/' ? 'it/' : '../'}"]`);
    await language.click();
    await expect(page).toHaveURL(path === '/' ? /\/it\/$/ : /:\d+\/$/);
  });

  test(`${path}: primary navigation works without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    try {
      await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
      const page = await context.newPage();
      await page.goto(baseURL + path);
      await expect(page.locator('button[aria-controls="mobile-menu"]')).toBeHidden();
      if (info.project.use.viewport.width < 1280) {
        await expect(page.locator('#mobile-menu')).toBeVisible();
        expect(await page.evaluate(() => document.querySelector('main').getBoundingClientRect().top >= document.querySelector('body > nav').getBoundingClientRect().bottom)).toBe(true);
      }
      const contact = page.locator('nav a[href="contact"]:visible');
      await contact.click();
      await expect(page).toHaveURL(new RegExp(path + 'contact$'));
      await expect(page.locator('h1')).toBeVisible();
    } finally { await context.close(); }
  });
}
