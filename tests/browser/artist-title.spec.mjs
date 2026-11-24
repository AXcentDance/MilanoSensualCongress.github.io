import { test, expect } from '@playwright/test';

const titleAnimations = ['artist-title-write', 'artist-spire-enter'];
const copies = [
  { path: '/artists', title: 'Artists Lineup' },
  { path: '/it/artists', title: 'Lineup Artisti' },
];

async function stubExternal(context) {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
}

test.beforeEach(async ({ context }) => stubExternal(context));

async function runningTitleAnimations(page) {
  return page.locator('.stage-title-scene').evaluate((scene, names) => scene.getAnimations({ subtree: true })
    .filter(animation => names.includes(animation.animationName) && ['running', 'pending'].includes(animation.playState)).length, titleAnimations);
}

async function expectReadableTitle(page, copy, { waitForFonts = true } = {}) {
  // Unlike fonts.ready, fonts.status also resolves reliably with scripting
  // disabled in Firefox. No animation or production style is suppressed here.
  if (waitForFonts) await expect.poll(() => page.evaluate(() => document.fonts.status)).toBe('loaded');
  const hero = page.locator('.stage-artist-hero');
  const heading = hero.getByRole('heading', { level: 1, name: copy.title, exact: true });
  await expect(heading).toBeVisible();
  await expect(heading).toHaveClass(/\bstage-artist-title\b/);
  await expect(heading).toHaveCSS('opacity', '1');
  await expect(heading).toHaveText(copy.title);
  await expect(hero.locator('svg, .stage-title-letter, .stage-hero-inner, .stage-hero-tail')).toHaveCount(0);
  const titleGeometry = await hero.locator('.stage-title-scene, .stage-artist-title, .stage-title-letter').evaluateAll(elements => elements.map(element => {
    const rect = element.getBoundingClientRect(), css = getComputedStyle(element);
    return { label: element.className, left: rect.left, right: rect.right, width: rect.width, height: rect.height, opacity: Number(css.opacity), visibility: css.visibility, viewport: document.documentElement.clientWidth };
  }));
  for (const item of titleGeometry) {
    expect(item.width, `${item.label} has visible width`).toBeGreaterThan(0);
    expect(item.height, `${item.label} has visible height`).toBeGreaterThan(0);
    expect(item.opacity, `${item.label} remains readable`).toBe(1);
    expect(item.visibility).toBe('visible');
    expect(item.left, `${item.label} fits the viewport`).toBeGreaterThanOrEqual(-1);
    expect(item.right, `${item.label} fits the viewport`).toBeLessThanOrEqual(item.viewport + 1);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'The artist title does not introduce page overflow').toBe(true);
}

async function artistLayout(page) {
  return page.evaluate(() => Object.fromEntries([
    ['scene', '.stage-title-scene'],
    ['title', '.stage-artist-title'],
    ['hero', '.stage-artist-hero'],
    ['collection', '#artist-collection'],
  ].map(([name, selector]) => {
    const rect = document.querySelector(selector).getBoundingClientRect();
    return [name, { top: rect.top + scrollY, bottom: rect.bottom + scrollY, height: rect.height }];
  })));
}

function expectStableArtistLayout(before, after) {
  for (const name of ['scene', 'title']) {
    for (const dimension of ['top', 'height']) {
      expect(Math.abs(after[name][dimension] - before[name][dimension]), `${name} ${dimension} stays reserved across the font swap`).toBeLessThanOrEqual(1);
    }
  }
  expect(Math.abs(after.hero.bottom - before.hero.bottom), 'Font availability does not resize the hero').toBeLessThanOrEqual(1);
  expect(Math.abs(after.collection.top - before.collection.top), 'The artist collection is not pushed down by font loading').toBeLessThanOrEqual(1);
}

async function waitForArtistStyles(page) {
  // The font request is deliberately pending, so navigation cannot wait for load.
  // Settle the async stylesheet cascade before comparing fallback and web fonts.
  await expect.poll(() => page.locator('link[rel="stylesheet"]').evaluateAll(links => links.every(link => link.media !== 'print'))).toBe(true);
  await expect(page.locator('.stage-title-scene')).toHaveCSS('display', 'grid');
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function expectStaticTitle(page, copy) {
  await expectReadableTitle(page, copy);
  expect(await runningTitleAnimations(page), 'The title does not animate in this preference state').toBe(0);
  const names = await page.locator('.stage-title-scene').evaluate(scene => [scene, ...scene.querySelectorAll('*')]
    .flatMap(element => getComputedStyle(element).animationName.split(',').map(name => name.trim())));
  expect(names.filter(name => titleAnimations.includes(name)), 'Title entrance animations are disabled').toEqual([]);
}

for (const copy of copies) {
  test(`${copy.path}: artist title keeps its layout while delayed web fonts arrive`, async ({ page }, info) => {
    let releaseFonts;
    const fontGate = new Promise(resolve => { releaseFonts = resolve; });
    const requestedFonts = new Set();
    await page.route(/\/fonts\/[^/?]+\.woff2(?:\?.*)?$/, async route => {
      requestedFonts.add(new URL(route.request().url()).pathname);
      await fontGate;
      await route.continue();
    });
    await page.addInitScript(() => {
      window.__artistFontShifts = [];
      if (!PerformanceObserver.supportedEntryTypes.includes('layout-shift')) return;
      window.__artistFontShiftObserver = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          if (entry.hadRecentInput) continue;
          if (entry.sources.some(source => source.node?.closest?.('.stage-artist-hero, #artist-collection'))) {
            window.__artistFontShifts.push(entry.value);
          }
        }
      });
      window.__artistFontShiftObserver.observe({ type: 'layout-shift', buffered: true });
    });
    try {
      await page.goto(copy.path, { waitUntil: 'domcontentloaded' });
      await expect.poll(() => requestedFonts.has('/fonts/inter-latin.woff2')).toBe(true);
      await waitForArtistStyles(page);
      expect(await page.evaluate(() => [...document.fonts].some(font => font.family.replace(/["']/g, '') === 'Inter' && font.status === 'loaded')), 'Inter is still withheld; the visible title is fallback text').toBe(false);
      await expectReadableTitle(page, copy, { waitForFonts: false });
      const before = await artistLayout(page);
      await page.evaluate(() => {
        window.__artistFontShiftObserver?.takeRecords();
        window.__artistFontShifts = [];
      });
      releaseFonts();
      await page.waitForLoadState('load');
      await expectReadableTitle(page, copy);
      await expect.poll(() => page.evaluate(() => [...document.fonts].some(font => font.family.replace(/["']/g, '') === 'Inter' && font.status === 'loaded')), { message: 'The released Inter font is used by the document' }).toBe(true);
      await expect.poll(() => runningTitleAnimations(page), { timeout: 2500 }).toBe(0);
      const after = await artistLayout(page);
      const shifts = await page.evaluate(() => window.__artistFontShifts);
      await info.attach('artist-delayed-font-layout', { body: JSON.stringify({ before, after, shifts }, null, 2), contentType: 'application/json' });
      expectStableArtistLayout(before, after);
      // Geometry is checked in all engines; layout-shift entries are additionally
      // checked where that API is supported (currently Chromium).
      expect(shifts.reduce((sum, value) => sum + value, 0), 'Late fonts do not cause a material hero/collection layout shift').toBeLessThan(0.02);
    } finally {
      releaseFonts();
    }
  });

  test(`${copy.path}: artist title stays readable when web fonts fail`, async ({ page }, info) => {
    const fontPattern = /\/fonts\/[^/?]+\.woff2(?:\?.*)?$/;
    const blockedFonts = new Set();
    const blockFont = route => {
      blockedFonts.add(new URL(route.request().url()).pathname);
      return route.abort('failed');
    };
    await page.route(fontPattern, blockFont);
    await page.goto(copy.path);
    await expectReadableTitle(page, copy);
    await expect.poll(() => runningTitleAnimations(page), { timeout: 2500 }).toBe(0);
    expect(blockedFonts.has('/fonts/inter-latin.woff2'), 'The Inter request was actually aborted').toBe(true);
    const blockedFaces = await page.evaluate(() => [...document.fonts].map(font => ({ family: font.family, status: font.status })));
    await info.attach('artist-blocked-font-faces', { body: JSON.stringify(blockedFaces, null, 2), contentType: 'application/json' });
    // WebKit may retain an unloaded face after an aborted preload; requiring
    // exactly "error" would test engine bookkeeping instead of fallback layout.
    expect(blockedFaces.some(font => font.family.replace(/["']/g, '') === 'Inter' && font.status === 'loaded'), 'The blocked visit uses fallback text').toBe(false);
    await info.attach('artist-blocked-font-layout', { body: JSON.stringify(await artistLayout(page), null, 2), contentType: 'application/json' });
  });

  test(`${copy.path}: gallery follows the title and ends at the footer`, async ({ page }) => {
    const portraitRequests = [];
    page.on('request', request => {
      if (/\/klau-ros-bachata-sensual(?:_\d+w)?\.webp$/.test(request.url())) portraitRequests.push(request.url());
    });
    await page.goto(copy.path);
    await expectReadableTitle(page, copy);
    const cards = page.locator('.stage-artist-gallery .stage-artist-tile');
    await expect(cards).toHaveCount(9);
    await expect(cards.locator('h2')).toHaveText(['Gero y Migle', 'Klau y Ros', 'Pablo y Raquel', 'Cristian y Gabriella', 'Agustín y Alba', 'David y Ines', 'Nacho y Silvia', 'Aitor Gomez', 'Irene y Tomas']);
    for (let i = 0; i < 3; i++) await expect(cards.nth(i).locator('.stage-artist-country')).toHaveText(copy.path.startsWith('/it/') ? '2 Workshop + Masterclass' : '2 Workshops + Masterclass');
    if (page.viewportSize().width > 1000) {
      const bounds = await cards.evaluateAll(cards => cards.slice(0, 4).map(card => card.getBoundingClientRect().top));
      expect(Math.max(...bounds.slice(0, 3)) - Math.min(...bounds.slice(0, 3))).toBeLessThan(1);
      expect(bounds[3]).toBeGreaterThan(bounds[0] + 300);
    }
    await expect(page.locator('.stage-orbit-topics, #artist-collection .experience-section-head')).toHaveCount(0);
    await expect.poll(() => cards.first().locator('img').evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    await expect.poll(() => cards.nth(1).locator('img').evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    expect(portraitRequests, 'Visible portrait loads one responsive image per visit').toHaveLength(1);
    const layout = await artistLayout(page);
    expect(layout.collection.top - layout.hero.bottom).toBeLessThanOrEqual(1);
    await expect(page.locator('#guest-artists, .guest-invitation')).toHaveCount(0);
    await expect(page.locator('main > section:last-child')).toHaveAttribute('id', 'artist-collection');
    await expect(page.locator('main + footer')).toHaveCount(1);
  });

  test(`${copy.path}: artist title stays visible with reduced motion`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(copy.path);
    await expect(page.locator('body')).not.toHaveClass(/\be27-motion-on\b/);
    await expect(page.locator('.e27-motion-toggle')).toBeHidden();
    await expectStaticTitle(page, copy);
  });

  test(`${copy.path}: artist title and hero content remain visible without JavaScript`, async ({ browser, baseURL }, info) => {
    const { viewport, hasTouch, isMobile, deviceScaleFactor } = info.project.use;
    const context = await browser.newContext({ javaScriptEnabled: false, viewport, hasTouch, isMobile, deviceScaleFactor });
    try {
      await stubExternal(context);
      const page = await context.newPage();
      await page.goto(baseURL + copy.path);
      await expectStaticTitle(page, copy);
      await expect(page.locator('.stage-artist-gallery .stage-artist-tile')).toHaveCount(9);
      await expect(page.locator('.e27-motion-toggle')).toBeHidden();
    } finally {
      await context.close();
    }
  });
}
