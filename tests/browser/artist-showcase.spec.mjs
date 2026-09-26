import { test, expect } from '@playwright/test';

for (const path of ['/', '/it/']) {
  test(`${path}: artist videos load on demand, switch, stop and restore focus`, async ({ page }) => {
    const embeds = [];
    await page.route('https://**/*', route => {
      if (route.request().url().startsWith('https://www.youtube-nocookie.com/embed/')) embeds.push(route.request().url());
      return route.fulfill({ status: 200, contentType: 'text/html', body: '<title>Artist video test double</title>' });
    });
    await page.goto(path);
    const cards = page.locator('[data-artist-video]');
    await expect(cards).toHaveCount(8);
    expect(await cards.evaluateAll(items => new Set(items.map(item => item.dataset.artistVideo)).size)).toBe(8);
    expect(embeds).toEqual([]);
    await expect(page.locator('#artist-player iframe')).toHaveCount(0);
    await cards.first().click();
    const dialog = page.locator('#artist-player');
    await expect(dialog).toBeVisible();
    await expect(page.locator('#artist-player-title')).toHaveText('Gero y Migle');
    await expect(dialog.locator('iframe')).toHaveAttribute('src', /embed\/j4CmXKDCMzI/);
    await expect.poll(() => embeds.length).toBe(1);
    await expect(page.locator('#heroVideo')).toHaveJSProperty('paused', true);
    await dialog.locator('[data-artist-step="-1"]').click();
    await expect(page.locator('#artist-player-title')).toHaveText('Aitor Gomez');
    await expect(dialog.locator('iframe')).toHaveAttribute('src', /embed\/uHm4EmmPess/);
    await expect(page.locator('#artist-player-count')).toHaveText('08 / 08');
    await dialog.locator('[data-artist-step="1"]').click();
    await expect(page.locator('#artist-player-title')).toHaveText('Gero y Migle');
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    await expect(dialog.locator('iframe')).toHaveCount(0);
    await expect(cards.first()).toBeFocused();
    await cards.nth(3).click();
    await expect(page.locator('#artist-player-title')).toHaveText('Agustín y Alba');
    await dialog.locator('.e27-player-close').click();
    await expect(dialog.locator('iframe')).toHaveCount(0);
    await expect(cards.nth(3)).toBeFocused();
  });

  test(`${path}: congress film plays in view and pause control stops it`, async ({ page }) => {
    await page.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
    await page.goto(path);
    const film = page.locator('#heroVideo');
    await film.scrollIntoViewIfNeeded();
    await expect.poll(() => film.evaluate(video => video.currentTime), { timeout: 15000 }).toBeGreaterThan(.1);
    await page.locator('.e27-video-toggle').click();
    await expect(film).toHaveJSProperty('paused', true);
  });

  test(`${path}: artist portraits are direct video links without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    const page = await context.newPage();
    await page.goto(baseURL + path);
    const cards = page.locator('[data-artist-video]');
    await expect(cards).toHaveCount(8);
    for (const card of await cards.all()) {
      await expect(card).toHaveAttribute('href', /^https:\/\/www\.youtube\.com\/watch\?v=[\w-]{11}$/);
      await expect(card).toHaveAccessibleName(/.+/);
    }
    await context.close();
  });
}
