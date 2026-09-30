import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
});

async function expectPassInvitation(page, path) {
  const invitation = page.locator('nav .e27-nav-cta:visible');
  await expect(invitation).toHaveCount(1);
  await expect(invitation).toHaveAttribute('href', path === '/' ? '/tickets' : '/it/tickets');
  await expect(invitation).toHaveAccessibleName(path === '/' ? 'Book your pass' : 'Prenota il tuo pass');
  await expect(invitation).toHaveClass(/\bpremiere-nav-booking\b/);
  await expect(invitation.locator('.premiere-ticket-stub')).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.fonts.status)).toBe('loaded');
  const bounds = await invitation.boundingBox();
  expect(bounds.height, 'The pass invitation retains a usable touch target').toBeGreaterThanOrEqual(44);
  expect(bounds.x, 'The pass invitation fits inside the navigation').toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(page.viewportSize().width + 1);
}

for (const path of ['/', '/it/']) {
  test(`${path}: short viewport keeps the last mobile navigation link reachable`, async ({ page, browserName }, info) => {
    await page.setViewportSize({ width: Math.min(info.project.use.viewport.width, 812), height: 375 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(path);
    const button = page.locator('button[aria-controls="mobile-menu"]');
    await button.focus();
    await page.keyboard.press('Enter');
    await expect(button).toHaveAttribute('aria-expanded', 'true');
    await expectPassInvitation(page, path);
    const links = page.locator('#mobile-menu a');
    // macOS WebKit uses Option+Tab to include links in keyboard navigation.
    const nextLink = browserName === 'webkit' && process.platform === 'darwin' ? 'Alt+Tab' : 'Tab';
    for (let index = 0; index < await links.count(); index++) await page.keyboard.press(nextLink);
    const last = links.last();
    await expect(last).toBeFocused();
    await expect(last).toBeInViewport({ ratio: 1 });
    await expect.poll(() => page.locator('body > nav.e27-nav').evaluate(nav => nav.getBoundingClientRect().bottom <= innerHeight + 1)).toBe(true);

    const language = page.locator(`#mobile-menu a[lang="${path === '/' ? 'it' : 'en'}"]`);
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
      await expectPassInvitation(page, path);
      if (info.project.use.viewport.width <= 1100) {
        await expect(page.locator('#mobile-menu')).toBeVisible();
        expect(await page.evaluate(() => document.querySelector('main').getBoundingClientRect().top >= document.querySelector('body > nav.e27-nav').getBoundingClientRect().bottom)).toBe(true);
      }
      const programme = path === '/' ? '/program' : '/it/programma';
      await page.locator(`nav a[href="${programme}"]:visible`).click();
      await expect(page).toHaveURL(new RegExp(programme + '$'));
      await expect(page.locator('h1')).toBeVisible();
    } finally { await context.close(); }
  });
}
