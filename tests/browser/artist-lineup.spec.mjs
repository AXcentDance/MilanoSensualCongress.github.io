import { test, expect } from '@playwright/test';

const selector = '#artist-collection [data-artist-preview]';
const videoSelector = 'video.e27-artist-preview';

async function settle(card) {
  await card.evaluate(async element => {
    await document.fonts.ready;
    element.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await Promise.all(element.getAnimations().filter(a => a.playState === 'running').map(a => a.finished.catch(() => {})));
  });
}

async function playing(card) {
  await expect(card).toHaveClass(/e27-preview-playing/, { timeout: 15000 });
  await expect.poll(() => card.locator(videoSelector).evaluate(video => !video.paused && video.currentTime > .2 && !video.error)).toBe(true);
  await expect(card.locator('button')).toHaveAttribute('aria-pressed', 'true');
}

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const path of ['/artists', '/it/artists']) {
  test(`${path}: lineup demos load on intent, play in place and stop on exit`, async ({ page }, info) => {
    test.setTimeout(90000);
    const requests = [];
    page.on('request', request => { if (request.url().includes('-preview-v0')) requests.push(request.url()); });
    await page.goto(path);
    const cards = page.locator(selector);
    await expect(cards).toHaveCount(9);
    await settle(cards.first());
    await expect(page.locator(videoSelector)).toHaveCount(0);
    expect(requests).toEqual([]);
    for (const card of await cards.all()) {
      await settle(card);
      if (info.project.use.hasTouch) await card.locator('button').tap();
      else await card.locator('.e27-artist-photo').hover();
      await playing(card);
      await expect(page.locator(videoSelector)).toHaveCount(1);
      await expect(page).toHaveURL(new RegExp(path + '$'));
      expect(page.context().pages()).toHaveLength(1);
      const video = card.locator(videoSelector);
      expect(await video.evaluate(v => ({ muted: v.muted, inline: v.playsInline, controls: v.controls })))
        .toEqual({ muted: true, inline: true, controls: false });
      await expect(video).toHaveCSS('object-fit', 'contain');
      await expect(video).toHaveCSS('opacity', '1');
      const frame = await video.evaluate(v => {
        const bounds = v.getBoundingClientRect();
        return { source: v.videoWidth / v.videoHeight, card: bounds.width / bounds.height };
      });
      expect(frame.source).toBeCloseTo(4 / 5, 3);
      expect(frame.card).toBeCloseTo(frame.source, 2);
      if (info.project.use.hasTouch) await card.locator('button').tap();
      else await page.mouse.move(0, 0);
      await expect(page.locator(videoSelector)).toHaveCount(0);
      await expect(card.locator('button')).toHaveAttribute('aria-pressed', 'false');
    }
  });

  test(`${path}: keyboard play, exclusive playback and motion preferences work`, async ({ page }) => {
    await page.addInitScript(() => Object.defineProperty(navigator, 'connection', {
      configurable: true, value: Object.assign(new EventTarget(), { saveData: true, effectiveType: '4g', downlink: 10 }),
    }));
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(path);
    const cards = page.locator(selector);
    const first = cards.first();
    await settle(first);
    await first.locator('.e27-artist-photo').hover();
    await page.waitForTimeout(300);
    await expect(page.locator(videoSelector)).toHaveCount(0);
    await first.locator('button').focus();
    await page.keyboard.press('Space');
    await playing(first);
    expect(await first.locator(videoSelector).evaluate(v => v.videoWidth)).toBe(240);
    const next = cards.nth(1);
    await next.locator('button').focus();
    await page.keyboard.press('Enter');
    await playing(next);
    await expect(first.locator(videoSelector)).toHaveCount(0);
    await expect(page.locator(videoSelector)).toHaveCount(1);
    await page.evaluate(() => document.body.classList.add('e27-motion-paused'));
    await expect(page.locator(videoSelector)).toHaveCount(0);
    await page.evaluate(() => document.body.classList.remove('e27-motion-paused'));
    await next.locator('button').press('Space');
    await playing(next);
    await page.locator('.e27-footer').scrollIntoViewIfNeeded();
    await expect(page.locator(videoSelector)).toHaveCount(0);
  });

  test(`${path}: an unavailable demo retains the photograph and can be retried`, async ({ page }) => {
    let fail = true;
    await page.route('**/msc-2027-gero-migle-preview-v04/index.m3u8', route => fail
      ? route.fulfill({ status: 404, body: '' }) : route.continue());
    await page.goto(path);
    const first = page.locator(selector).first();
    await settle(first);
    await first.locator('button').focus();
    const response = page.waitForResponse(r => r.url().includes('gero-migle-preview-v04/index.m3u8'));
    await page.keyboard.press('Space');
    expect((await response).status()).toBe(404);
    await expect(first.locator('button')).toHaveAttribute('aria-busy', 'false');
    await expect(first.locator('img')).toBeVisible();
    await expect(page.locator(videoSelector)).toHaveCount(0);
    fail = false;
    await page.keyboard.press('Space');
    await playing(first);
    await page.keyboard.press('Space');
    await expect(page.locator(videoSelector)).toHaveCount(0);
  });
}
