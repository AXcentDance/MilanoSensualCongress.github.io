import { test, expect } from '@playwright/test';

const booking = 'https://www.booking.com/Share-aq5kGb';
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function expectHotelGuide(page) {
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('main')).toContainText(/20–22 (November|novembre) 2026/);
  await expect(page.locator('#brianteo')).toContainText('Brianteo');
  await expect(page.locator('#brianteo')).toContainText('Burago di Molgora');
  await expect(page.locator('#brianteo a[href="' + booking + '"]')).toBeVisible();
  await expect(page.locator('main')).toContainText('Devero Hotel');
  await expect(page.locator('main')).toContainText('AS Hotel Cambiago');
  await expect(page.locator('main').getByText(/SOLD OUT/, { exact: false })).toHaveCount(2);
  await expect(page.locator('main a[href*="atmosferaeventi.it"]')).toHaveCount(0);
  await expect(page.locator('main')).not.toContainText(/€260|€220|lower than|inferiori|2027/);
  await expect(page.locator('a[href="tel:+393934407045"]')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}

for (const path of ['/hotel', '/it/hotel', '/BookHotel', '/it/BookHotel']) {
  test(path + ': third hotel booking and sold-out status stay clear', async ({ page, context }) => {
    await page.goto(path);
    await expectHotelGuide(page);
    await expect(page.locator('main a[href*="google.com/maps/dir"]')).toHaveAttribute('href', /origin=Brianteo.*destination=Devero/);
    await expect(page.locator('main a[href*="brianteo.it/"]')).toHaveAttribute('href', path.startsWith('/it') ? 'https://www.brianteo.it/it' : 'https://www.brianteo.it/en');
    const popupPromise = context.waitForEvent('page');
    await page.locator('#brianteo a[href="' + booking + '"]').click();
    const popup = await popupPromise;
    await expect(popup).toHaveURL(booking);
    await popup.close();

    if (path.endsWith('/hotel')) {
      const banners = page.locator('main > .hotel-sold-out');
      await expect(banners).toHaveCount(2);
      await expect(banners.nth(0)).toContainText('Devero Hotel');
      await expect(banners.nth(1)).toContainText('AS Hotel Cambiago');
      const [first, second, hero] = await Promise.all([banners.nth(0).boundingBox(), banners.nth(1).boundingBox(), page.locator('#brianteo').boundingBox()]);
      expect(first.y + first.height).toBeLessThanOrEqual(second.y + 1);
      expect(second.y + second.height).toBeLessThanOrEqual(hero.y + 1);
      expect(first.width).toBe(second.width);
      const photo = page.locator('.hotel-property img');
      await photo.scrollIntoViewIfNeeded();
      await expect.poll(() => photo.evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
      await expect(page.locator('.hotel-property figcaption')).toContainText('Brianteo Hotel');
      await page.locator('main a[href="BookHotel#brianteo"]').click();
      await expect(page).toHaveURL(/\/BookHotel#brianteo$/);
      await expectHotelGuide(page);
    }
  });

  test(path + ': hotel information and booking work without JavaScript', async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    try {
      await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
      const page = await context.newPage();
      await page.goto(baseURL + path);
      await expectHotelGuide(page);
    } finally { await context.close(); }
  });
}

for (const path of ['/hotel', '/it/hotel']) {
  test(path + ': existing hotel anchors and language switch still work', async ({ page }) => {
    for (const hash of ['#as-hotel-cambiago', '#event-hotel', '#hotel-view-second', '#as-hotel-details']) {
      await page.goto(path + hash);
      await expect(page.locator(hash)).toBeVisible();
      await expectHotelGuide(page);
    }
    const alternate = path.startsWith('/it') ? '../hotel' : 'it/hotel';
    const menu = page.locator('button[aria-controls="mobile-menu"]');
    if (await menu.isVisible()) await menu.click();
    await page.locator('nav a[href="' + alternate + '"]:visible').click();
    await expectHotelGuide(page);
    await expect(page).toHaveURL(new RegExp(path.startsWith('/it') ? '/hotel$' : '/it/hotel$'));
  });
}
