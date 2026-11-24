import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const headliners = JSON.parse(readFileSync(new URL('../../data/editions/2027.json', import.meta.url))).headliners;
const flyerOrder = headliners.homepagePresentation.order;

async function expectPhoneFlyer(page, path) {
  const flyer = page.locator('.premiere-mobile-flyer img');
  await expect(page.locator('#artist-showcase .e27-artists-grid')).toBeHidden();
  await expect(flyer).toBeVisible();
  await expect(flyer).toHaveAttribute('alt', path === '/it/' ? /^Locandina di Milano Sensual Congress/ : /^Milano Sensual Congress flyer/);
  await expect.poll(() => flyer.evaluate(img => img.complete && img.naturalWidth > 1)).toBe(true);
  const box = await flyer.boundingBox();
  expect(Math.abs(box.width / box.height - 4 / 5)).toBeLessThan(.01);
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width);
  const sources = await page.locator('#artist-showcase .e27-artist img').evaluateAll(images => images.map(img => img.currentSrc));
  expect(sources.every(src => src.startsWith('data:image/'))).toBe(true);
}

for (const path of ['/', '/it/']) {
  test(`${path}: artist portraits are informational and ignore clicks and Enter`, async ({ page }) => {
    const embeds = [];
    await page.route('https://**/*', route => {
      if (route.request().url().startsWith('https://www.youtube-nocookie.com/embed/')) embeds.push(route.request().url());
      return route.fulfill({ status: 200, contentType: 'text/html', body: '<title>Artist video test double</title>' });
    });
    // Disable hover motion here so an actual pointer click cannot be mistaken
    // for a request caused independently by lingering over the card.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(path);
    const cards = page.locator('.home-premiere .e27-artist');
    await expect(cards).toHaveCount(headliners.artists.length);
    expect(await cards.evaluateAll(items => items.map(item => item.dataset.artistName))).toEqual(flyerOrder);
    expect(await cards.evaluateAll(items => new Set(items.filter(item => item.dataset.artistPreview).map(item => item.dataset.artistPreview)).size)).toBe(headliners.homepagePresentation.videoPreviews.artists.length);
    expect(embeds).toEqual([]);
    await expect(page.locator('#artist-player')).toHaveCount(0);
    await expect(cards.locator('a, [role="button"], [role="link"], .e27-play')).toHaveCount(0);
    await expect(cards.locator('button')).toHaveCount(headliners.homepagePresentation.videoPreviews.artists.length);
    await expect(cards.locator('small')).toHaveCount(0);
    await expect(page.locator('.e27-showcase-intro')).toHaveCount(0);
    if (page.viewportSize().width <= 700) {
      await expectPhoneFlyer(page, path);
      return;
    }
    await expect(page.locator('.premiere-mobile-flyer')).toBeHidden();
    const url = page.url();
    for (const card of await cards.all()) {
      expect(await card.evaluate(el => ({ tag: el.tagName, tabIndex: el.tabIndex })))
        .toEqual({ tag: 'ARTICLE', tabIndex: -1 });
      await expect(card).not.toHaveAttribute('href');
      await expect(card.locator('h3')).toHaveText(await card.getAttribute('data-artist-name'));
      await expect(card.locator('h3')).toBeVisible();
      if (await card.getAttribute('data-artist-preview')) {
        const button = card.locator('.e27-artist-play');
        await expect(button).toHaveAttribute('type', 'button');
        await expect(button).toHaveAttribute('aria-pressed', 'false');
        if (page.viewportSize().width <= 600) {
          await expect(button).toBeVisible();
          await expect(button).toHaveAccessibleName(await button.getAttribute('data-play-label'));
          expect(await card.evaluate(el => {
            const heading = el.querySelector('h3').getBoundingClientRect();
            const button = el.querySelector('.e27-artist-play').getBoundingClientRect();
            return button.left >= heading.right - 1 && button.top < heading.bottom &&
              button.bottom > heading.top && button.width >= 44 && button.height >= 44;
          }), 'The phone preview control sits beside the artist name with a 44px touch target').toBe(true);
        } else await expect(button).toBeHidden();
      }
      await card.locator('img').click();
      await expect(card).not.toBeFocused();
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(url);
    }
    await page.waitForTimeout(300);
    expect(page.context().pages()).toHaveLength(1);
    expect(embeds).toEqual([]);
    await expect(page.locator('#artist-player, .e27-artist-preview')).toHaveCount(0);
  });

  test(`${path}: artist portraits retain static information without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    const page = await context.newPage();
    await page.goto(baseURL + path);
    const cards = page.locator('.home-premiere .e27-artist');
    await expect(cards).toHaveCount(headliners.artists.length);
    expect(await cards.evaluateAll(items => items.map(item => item.dataset.artistName))).toEqual(flyerOrder);
    if (page.viewportSize().width <= 700) {
      await expectPhoneFlyer(page, path);
      await context.close();
      return;
    }
    await expect(page.locator('.premiere-mobile-flyer')).toBeHidden();
    const url = page.url();
    for (const card of await cards.all()) {
      await expect(card).not.toHaveAttribute('href');
      await expect(card.locator('h3')).toHaveText(await card.getAttribute('data-artist-name'));
      await expect(card.locator('h3')).toBeVisible();
      await expect(card.locator('small')).toHaveCount(0);
      await card.scrollIntoViewIfNeeded();
      await expect(card.locator('img')).toBeVisible();
      await expect(card.locator('img')).toHaveAttribute('alt', '');
      await expect.poll(() => card.locator('img').evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
      expect(await card.locator('img').evaluate(img => {
        const bounds = img.getBoundingClientRect();
        return Math.abs(bounds.width / bounds.height - img.naturalWidth / img.naturalHeight);
      }), 'The unframed portrait fits the original website card proportions').toBeLessThan(.01);
      await expect(card.locator('.e27-artist-play')).toBeHidden();
    }
    await cards.first().locator('img').click();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(url);
    await expect(page.locator('#artist-player, .e27-artist-preview')).toHaveCount(0);
    expect(context.pages()).toHaveLength(1);
    await context.close();
  });
}
