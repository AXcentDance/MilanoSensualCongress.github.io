import { test, expect } from '@playwright/test';

const booking = 'https://atmosferaeventi.it/prenotazione/134-5LAWjvWM-nZyIV9Cv-7gKm61tZ-AyoT1uNJ';
const eventBooking = 'https://atmosferaeventi.it/prenotazione/108-ne8OWECn-A1QtaUFB-yTcrX2Pt-GmgitZmq';
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function expectHotel(page, second) {
  await expect(page.locator(second ? '#hotel-choice-second' : '#hotel-choice-event')).toBeChecked();
  await expect(page.locator(second ? '#hotel-view-second' : '#hotel-view-event')).toBeVisible();
  await expect(page.locator(second ? '#hotel-view-event' : '#hotel-view-second')).toBeHidden();
}

async function expectUncoveredHero(page) {
  await page.evaluate(() => document.fonts.ready);
  await expect.poll(() => page.evaluate(() => {
    const hero = document.querySelector('.hotel-second-hero').getBoundingClientRect();
    const selector = document.querySelector('.hotel-selector').getBoundingClientRect();
    return hero.top - selector.bottom;
  })).toBeGreaterThanOrEqual(-1);
}

// Synthetic gestures exercise direction/scroll/target guards in all engines.
async function swipe(page, selector, dx, dy = 0) {
  await page.locator(selector).evaluate((element, delta) => {
    const send = (name, x, y) => {
      const event = new Event(name, { bubbles: true, cancelable: true });
      const touch = { identifier: 1, clientX: x, clientY: y };
      Object.defineProperties(event, { touches: { value: name === 'touchstart' ? [touch] : [] }, changedTouches: { value: [touch] } });
      element.dispatchEvent(event);
    };
    send('touchstart', 180, 400);
    send('touchend', 180 + delta.dx, 400 + delta.dy);
  }, { dx, dy });
}

for (const path of ['/hotel', '/it/hotel']) {
  test(`${path}: hotel views show separate content and resize to the selected hotel`, async ({ page }) => {
    await page.goto(path);
    await expectHotel(page, false);
    await expect(page.locator('#hotel-view-event')).not.toContainText('AS Hotel Cambiago');
    await expect(page.locator('#hotel-view-event a').filter({ hasText: /Devero/ }).first()).toHaveAttribute('href', eventBooking);
    await page.locator('label[for="hotel-choice-second"]').click();
    await expectHotel(page, true);
    await expect(page.locator('#hotel-view-second tbody td')).toHaveText(['€260', '€220']);
    await expect(page.locator('#hotel-view-second a[href="' + booking + '"]')).toHaveCount(2);
    await expect(page.locator('#hotel-view-second a[href="' + eventBooking + '"]')).toHaveCount(0);
    const panelHeight = await page.locator('#hotel-view-second').evaluate(el => el.getBoundingClientRect().height);
    const viewportHeight = await page.locator('.hotel-views').evaluate(el => el.getBoundingClientRect().height);
    expect(Math.abs(viewportHeight - panelHeight)).toBeLessThan(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.locator('#as-hotel-details img').scrollIntoViewIfNeeded();
    await expect.poll(() => page.locator('#as-hotel-details img').evaluate(im => im.complete && im.naturalWidth > 0)).toBe(true);
    await page.locator('label[for="hotel-choice-event"]').click();
    await expectHotel(page, false);
    expect(await page.evaluate(() => scrollY)).toBe(0);
  });

  test(`${path}: keyboard selection, history, deep links and translated views`, async ({ page }) => {
    const initialRequests = [];
    page.on('request', request => initialRequests.push(new URL(request.url()).pathname));
    await page.goto(path + '#as-hotel-cambiago');
    await expectHotel(page, true);
    await expectUncoveredHero(page);
    expect(await page.evaluate(() => scrollY)).toBe(0);
    expect(initialRequests).toContain('/images/hotel/as-hotel-cambiago-entrance-hero.webp');
    expect(initialRequests).not.toContain('/images/hotel/devero-hotel-exterior-dusk.webp');
    expect(initialRequests).not.toContain('/fonts/playfair-display-italic-latin.woff2');
    await page.goto(path);
    await page.locator('#hotel-choice-event').focus();
    await page.keyboard.press('ArrowRight');
    await expectHotel(page, true);
    await expect(page).toHaveURL(/#as-hotel-cambiago$/);
    expect(await page.locator('label[for="hotel-choice-second"]').evaluate(el => getComputedStyle(el).outlineStyle)).toBe('solid');
    const alternate = await page.locator('[data-hotel-language]').first().getAttribute('href');
    expect(alternate).toMatch(/#as-hotel-cambiago$/);
    await page.keyboard.press('ArrowLeft');
    await expectHotel(page, false);
    await page.goBack();
    await expectHotel(page, true);
    await page.goForward();
    await expectHotel(page, false);
    await page.goto(new URL(alternate, page.url()).href);
    await expectHotel(page, true);
    await expectUncoveredHero(page);
    expect(await page.evaluate(() => scrollY)).toBe(0);
    await page.reload();
    await expectHotel(page, true);
    await expectUncoveredHero(page);
    expect(await page.evaluate(() => scrollY)).toBe(0);
    await page.goto(path);
    await expectHotel(page, false);
  });

  test(`${path}: native hotel selector works without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    try {
      await context.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
      const page = await context.newPage();
      await page.goto(baseURL + path);
      await expect(page.locator('h1')).toBeVisible();
      await expectHotel(page, false);
      await page.locator('label[for="hotel-choice-second"]').click();
      await expectHotel(page, true);
      await expect(page.locator('#hotel-view-second tbody td')).toHaveText(['€260', '€220']);
      await page.locator('label[for="hotel-choice-event"]').click();
      await expectHotel(page, false);
    } finally { await context.close(); }
  });

  test(`${path}: swipe guards, rapid switches and reduced motion`, async ({ page }) => {
    await page.goto(path);
    await swipe(page, '#hotel-view-event header', -100, 180);
    await expectHotel(page, false);
    await swipe(page, '#carousel', -100);
    await expectHotel(page, false);
    await swipe(page, '#hotel-view-event header', -100);
    await expectHotel(page, true);
    await swipe(page, '#hotel-view-second header', 100);
    await expectHotel(page, false);
    await swipe(page, '.hotel-switch-track', 100);
    await expectHotel(page, true);
    // A second switch may arrive before the first slide animation finishes.
    await page.locator('label[for="hotel-choice-event"]').click();
    await page.locator('label[for="hotel-choice-second"]').click();
    await expectHotel(page, true);
    await expect(page.locator('[data-leaving]')).toHaveCount(0);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.locator('label[for="hotel-choice-event"]').click();
    await expectHotel(page, false);
    expect(await page.locator('.hotel-views').evaluate(el => el.getAnimations({ subtree: true }).length)).toBe(0);
  });
}
