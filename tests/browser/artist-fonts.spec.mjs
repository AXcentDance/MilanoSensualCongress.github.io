import { test, expect } from '@playwright/test';

const pages = ['/artists', '/it/artists'];
const playfairFont = /\/fonts\/playfair-display[^/?]*\.woff2(?:\?.*)?$/;

async function settleArtistStyles(page) {
  await expect.poll(() => page.locator('link[rel="stylesheet"]').evaluateAll(links => links.every(link => link.media !== 'print'))).toBe(true);
  // Hold only Playfair to isolate the heading swap from the body font's loading.
  await page.evaluate(() => document.fonts.load('20px Inter'));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function layout(page) {
  return page.evaluate(() => Object.fromEntries([
    ['title', 'main > header h1'], ['intro', 'main > header p'],
    ['hero', 'main > header'], ['collection', 'main > section'],
  ].map(([name, selector]) => {
    const rect = document.querySelector(selector).getBoundingClientRect();
    return [name, { top: rect.top + scrollY, height: rect.height, bottom: rect.bottom + scrollY }];
  })));
}

async function expectReadableHeading(page) {
  const title = page.locator('main > header h1');
  await expect(title).toBeVisible();
  await expect(title).toHaveCSS('opacity', '1');
  const fits = await title.evaluate(element => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const width = document.documentElement.clientWidth;
    return [...range.getClientRects()].every(rect => rect.left >= -1 && rect.right <= width + 1);
  });
  expect(fits, 'Heading text fits the viewport with the available font').toBe(true);
  await expect(page.locator('main > header a[href*="lasalsadelbaile.com"]')).toBeVisible();
}

for (const path of pages) {
  test(`${path}: artist heading preserves layout when Playfair arrives late`, async ({ page }, info) => {
    let releaseFonts;
    const gate = new Promise(resolve => { releaseFonts = resolve; });
    const heldFonts = new Set();
    await page.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
    await page.route(playfairFont, async route => {
      heldFonts.add(new URL(route.request().url()).pathname);
      await gate;
      await route.continue();
    });
    await page.addInitScript(() => {
      window.__artistHeadingShifts = [];
      if (!PerformanceObserver.supportedEntryTypes.includes('layout-shift')) return;
      window.__artistHeadingObserver = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput && entry.sources.some(source => source.node?.closest?.('main > header, main > section'))) {
            window.__artistHeadingShifts.push(entry.value);
          }
        }
      });
      window.__artistHeadingObserver.observe({ type: 'layout-shift', buffered: true });
    });
    try {
      await page.goto(path, { waitUntil: 'domcontentloaded' });
      await expect.poll(() => heldFonts.has('/fonts/playfair-display-latin.woff2')).toBe(true);
      await settleArtistStyles(page);
      expect(await page.evaluate(() => [...document.fonts].some(font => font.family.replace(/["']/g, '') === 'Playfair Display' && font.status === 'loaded'))).toBe(false);
      await expectReadableHeading(page);
      const before = await layout(page);
      await page.evaluate(() => {
        window.__artistHeadingObserver?.takeRecords();
        window.__artistHeadingShifts = [];
      });
      releaseFonts();
      await page.waitForLoadState('load');
      await page.evaluate(() => document.fonts.ready);
      await expect.poll(() => page.evaluate(() => [...document.fonts].some(font => font.family.replace(/["']/g, '') === 'Playfair Display' && font.status === 'loaded'))).toBe(true);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await expectReadableHeading(page);
      const after = await layout(page);
      const shifts = await page.evaluate(() => window.__artistHeadingShifts);
      await info.attach('artist-heading-font-layout', { body: JSON.stringify({ before, after, shifts }, null, 2), contentType: 'application/json' });
      for (const [element, dimension] of [['title', 'top'], ['title', 'height'], ['intro', 'top'], ['hero', 'bottom'], ['collection', 'top']]) {
        expect(Math.abs(after[element][dimension] - before[element][dimension]), `${element} ${dimension} stays stable during Playfair swap`).toBeLessThanOrEqual(1);
      }
      // Geometry covers every engine; Chromium also exposes layout-shift entries.
      expect(shifts.reduce((sum, value) => sum + value, 0)).toBeLessThan(0.02);
    } finally {
      releaseFonts();
    }
  });

  test(`${path}: artist heading remains readable when Playfair fails`, async ({ page }) => {
    const blocked = new Set();
    await page.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
    await page.route(playfairFont, route => {
      blocked.add(new URL(route.request().url()).pathname);
      return route.abort('failed');
    });
    await page.goto(path);
    await settleArtistStyles(page);
    expect(blocked.has('/fonts/playfair-display-latin.woff2')).toBe(true);
    expect(await page.evaluate(() => [...document.fonts].some(font => font.family.replace(/["']/g, '') === 'Playfair Display' && font.status === 'loaded'))).toBe(false);
    await expectReadableHeading(page);
  });
}
