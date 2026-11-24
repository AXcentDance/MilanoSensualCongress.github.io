import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const path of ['/', '/it/']) {
  test(`${path}: static hero keeps ten portraits, facts and ticket action visible without media requests`, async ({ page }) => {
    const mediaRequests = [];
    page.on('request', request => { if (/\.(mp4|m3u8|m4s)(?:\?|$)/.test(request.url())) mediaRequests.push(request.url()); });
    await page.goto(path);
    await page.evaluate(() => document.fonts.ready);
    const hero = page.locator('.premiere-media');
    await expect(hero.locator('video, [data-artist-preview], .premiere-film-control, .e27-artist-play')).toHaveCount(0);
    const cards = hero.locator('.e27-artist');
    await expect(cards).toHaveCount(10);
    expect(await cards.evaluateAll(items => items.map(item => item.dataset.artistName))).toEqual([
      'Miguel y Sunsire', 'Pablo y Raquel', 'Gero y Migle', 'Cristian y Gabriella', 'Agustin y Alba',
      'Nacho y Silvia', 'Klau y Ros', 'Luis y Andrea', 'David y Ines', 'Aitor',
    ]);
    for (const img of await hero.locator('img').all()) {
      await expect.poll(() => img.evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    }
    await cards.first().hover();
    await page.waitForTimeout(350);
    expect(mediaRequests).toEqual([]);
    const clipped = await hero.locator('h1, h2, h3, .premiere-eyebrow, .premiere-date p, .premiere-venue, a').evaluateAll(items => items.filter(item => {
      const box = item.getBoundingClientRect();
      return box.left < -1 || box.right > innerWidth + 1 || item.scrollWidth > item.clientWidth + 1;
    }).map(item => item.textContent.trim()));
    expect(clipped).toEqual([]);
    const ticket = hero.locator('.premiere-hero-ticket');
    await ticket.focus();
    expect(await ticket.evaluate(el => parseFloat(getComputedStyle(el).outlineWidth))).toBeGreaterThanOrEqual(2);
    await ticket.press('Enter');
    await expect(page).toHaveURL(new RegExp(`${path === '/it/' ? '/it' : ''}/tickets/?$`));
  });
}

for (const path of ['/', '/it/']) {
  test(`${path}: seven tricolour stars move without a visible control and respect reduced motion`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(path);
    const strip = page.locator('.premiere-stars');
    await expect(strip.locator('.premiere-star')).toHaveCount(7);
    const trailColoursMatch = await strip.locator('.premiere-star').evaluateAll(stars => stars.every(star => {
      const trail = star.querySelector('.premiere-star-trail');
      const id = trail.getAttribute('fill').slice(5, -1);
      const stops = document.getElementById(id).querySelectorAll('stop');
      return [...stops].every(stop => stop.getAttribute('stop-color') === star.lastElementChild.getAttribute('fill'));
    }));
    expect(trailColoursMatch).toBe(true);
    const star = strip.locator('.premiere-star').first();
    await expect(strip.locator('button')).toHaveCount(0);
    await expect(page.locator('.premiere-eyebrow')).toHaveCount(0);
    const first = await star.evaluate(el => getComputedStyle(el).transform);
    await expect.poll(() => star.evaluate(el => getComputedStyle(el).transform)).not.toBe(first);
    const headingBox = await page.locator('h1').boundingBox();
    const stripBox = await strip.boundingBox();
    expect(stripBox.y).toBeGreaterThanOrEqual(headingBox.y + headingBox.height);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect(star).toHaveCSS('animation-name', 'none');
    await expect(page.locator('.premiere-media video')).toHaveCount(0);
  });
}
