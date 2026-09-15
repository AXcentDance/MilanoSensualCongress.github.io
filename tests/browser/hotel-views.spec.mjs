import { test, expect } from '@playwright/test';

const booking = 'https://atmosferaeventi.it/prenotazione/134-5LAWjvWM-nZyIV9Cv-7gKm61tZ-AyoT1uNJ';
const eventBooking = 'https://atmosferaeventi.it/prenotazione/108-ne8OWECn-A1QtaUFB-yTcrX2Pt-GmgitZmq';
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function expectSingleHotel(page) {
  await expect(page.locator('.hotel-sold-out')).toBeVisible();
  await expect(page.locator('.hotel-sold-out')).toContainText(/Devero Hotel.*SOLD OUT/);
  await expect(page.locator('h1')).toHaveText('AS HotelCambiago');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('.hotel-rate-highlight')).toContainText('Booking.com');
  await expect(page.locator('tbody td')).toHaveText(['€260', '€220']);
  await expect(page.locator(`main a[href="${booking}"]`)).toHaveCount(2);
  await expect(page.locator(`a[href="${eventBooking}"]`)).toHaveCount(0);
  await expect(page.locator('input[name="hotel-view"], [data-hotel-switcher], #carousel')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}

for (const path of ['/hotel', '/it/hotel']) {
  test(`${path}: static hotel page shows sold-out notice, AS Cambiago rates and booking`, async ({ page }) => {
    const requests = [];
    page.on('request', request => requests.push(new URL(request.url()).pathname));
    await page.goto(path);
    await expectSingleHotel(page);
    await page.evaluate(() => document.fonts.ready);
    const bounds = await page.evaluate(() => {
      const nav = document.querySelector('body > nav').getBoundingClientRect();
      const notice = document.querySelector('.hotel-sold-out').getBoundingClientRect();
      const hero = document.querySelector('.hotel-second-hero').getBoundingClientRect();
      return { navBottom: nav.bottom, noticeTop: notice.top, noticeBottom: notice.bottom, heroTop: hero.top };
    });
    expect(bounds.noticeTop).toBeGreaterThanOrEqual(bounds.navBottom - 1);
    expect(bounds.heroTop).toBeGreaterThanOrEqual(bounds.noticeBottom - 1);
    expect(requests).toContain('/images/hotel/as-hotel-cambiago-entrance-hero.webp');
    expect(requests.some(url => url.includes('devero-hotel-') || url.includes('hotel-views.js'))).toBe(false);
    await page.locator('#as-hotel-details img').scrollIntoViewIfNeeded();
    await expect.poll(() => page.locator('#as-hotel-details img').evaluate(im => im.complete && im.naturalWidth > 0)).toBe(true);
    const guide = page.locator('main a[href="BookHotel#as-hotel-cambiago"]');
    await guide.click();
    await expect(page).toHaveURL(/\/BookHotel#as-hotel-cambiago$/);
    await expect(page.locator('#as-hotel-cambiago')).toBeVisible();
  });

  test(`${path}: legacy hotel links and language navigation keep the single page`, async ({ page }) => {
    for (const hash of ['#as-hotel-cambiago', '#event-hotel', '#hotel-view-second']) {
      await page.goto(path + hash);
      await expectSingleHotel(page);
      expect(await page.evaluate(() => scrollY)).toBe(0);
    }
    const alternate = path.startsWith('/it') ? '../hotel' : 'it/hotel';
    const menu = page.locator('button[aria-controls="mobile-menu"]');
    if (await menu.isVisible()) await menu.click();
    await page.locator(`nav a[href="${alternate}"]:visible`).click();
    await expectSingleHotel(page);
    await expect(page).toHaveURL(new RegExp(path.startsWith('/it') ? '/hotel$' : '/it/hotel$'));
  });

  test(`${path}: static hotel content and booking work without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    try {
      await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
      const page = await context.newPage();
      await page.goto(baseURL + path + '#as-hotel-cambiago');
      await expectSingleHotel(page);
    } finally { await context.close(); }
  });
}
