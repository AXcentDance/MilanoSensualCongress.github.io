import { test, expect } from '@playwright/test';

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
    const cards = page.locator('[data-artist-video]');
    await expect(cards).toHaveCount(8);
    expect(await cards.evaluateAll(items => new Set(items.map(item => item.dataset.artistVideo)).size)).toBe(8);
    expect(embeds).toEqual([]);
    await expect(page.locator('#artist-player')).toHaveCount(0);
    await expect(cards.locator('a, [role="button"], [role="link"], .e27-play')).toHaveCount(0);
    await expect(cards.locator('button')).toHaveCount(8);
    const url = page.url();
    for (const card of await cards.all()) {
      expect(await card.evaluate(el => ({ tag: el.tagName, tabIndex: el.tabIndex })))
        .toEqual({ tag: 'ARTICLE', tabIndex: -1 });
      await expect(card).not.toHaveAttribute('href');
      await expect(card.locator('h3')).toHaveText(await card.getAttribute('data-artist-name'));
      await expect(card.locator('small')).not.toHaveText(/Watch video|Guarda/i);
      const button = card.locator('.e27-artist-play');
      await expect(button).toHaveAttribute('type', 'button');
      await expect(button).toHaveAttribute('aria-pressed', 'false');
      if (page.viewportSize().width <= 600) {
        await expect(button).toBeVisible();
        await expect(button).toHaveAccessibleName(await button.getAttribute('data-play-label'));
        expect(await card.evaluate(el => {
          const heading = el.querySelector('h3').getBoundingClientRect();
          const button = el.querySelector('.e27-artist-play').getBoundingClientRect();
          return button.left >= heading.right - 1 && button.top < heading.bottom && button.bottom > heading.top;
        }), 'The phone play button sits beside the artist name').toBe(true);
      } else await expect(button).toBeHidden();
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

  test(`${path}: the opening film pauses while visitors explore the artists`, async ({ page }) => {
    await page.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(path);
    const film = page.locator('#heroVideo');
    await expect.poll(() => film.evaluate(video => !video.paused && video.currentTime > .1), { timeout: 15000 }).toBe(true);
    await page.locator('#artist-showcase').evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
    await expect(film).toHaveJSProperty('paused', true);
    const pausedAt = await film.evaluate(video => video.currentTime);
    await page.waitForTimeout(300);
    expect(await film.evaluate(video => video.currentTime)).toBeCloseTo(pausedAt, 2);
    await page.locator('.premiere-hero').evaluate(el => el.scrollIntoView({ behavior: 'instant' }));
    await expect.poll(() => film.evaluate(video => video.currentTime)).toBeGreaterThan(pausedAt + .1);
    await film.evaluate(video => { video.currentTime = video.duration - .3; });
    const ambient = page.locator('#heroAmbientVideo');
    await expect.poll(() => ambient.evaluate(video => !video.paused && video.currentTime > 1.25), { timeout: 15000 }).toBe(true);
    await page.locator('#artist-showcase').evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
    await expect(ambient).toHaveJSProperty('paused', true);
    const ambientPausedAt = await ambient.evaluate(video => video.currentTime);
    await page.waitForTimeout(300);
    expect(await ambient.evaluate(video => video.currentTime)).toBeCloseTo(ambientPausedAt, 2);
    await page.locator('.premiere-hero').evaluate(el => el.scrollIntoView({ behavior: 'instant' }));
    await expect.poll(() => ambient.evaluate(video => video.currentTime)).toBeGreaterThan(ambientPausedAt + .1);
    await expect(film).toHaveJSProperty('ended', true);
    await expect(page.locator('.e27-video-toggle, .premiere-film-toggle, .e27-motion-toggle')).toHaveCount(0);
  });

  test(`${path}: artist portraits retain static information without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    const page = await context.newPage();
    await page.goto(baseURL + path);
    const cards = page.locator('[data-artist-video]');
    await expect(cards).toHaveCount(8);
    const url = page.url();
    for (const card of await cards.all()) {
      await expect(card).not.toHaveAttribute('href');
      await expect(card.locator('h3')).toHaveText(await card.getAttribute('data-artist-name'));
      await expect(card.locator('h3')).toBeVisible();
      await expect(card.locator('small')).toHaveText(/\S/);
      await expect(card.locator('img')).toBeVisible();
      await expect(card.locator('img')).toHaveAttribute('alt', '');
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
