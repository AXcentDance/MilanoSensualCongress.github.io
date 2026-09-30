import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const prefix of ['', '/it']) {
  test(`${prefix || '/'}: async styles preserve the critical heading design`, async ({ page }) => {
    let releaseBase, releaseEnhancements;
    const baseGate = new Promise(resolve => { releaseBase = resolve; });
    const enhancementGate = new Promise(resolve => { releaseEnhancements = resolve; });
    const heldEnhancements = new Set();
    await page.route(/\.css(?:\?|$)/, async route => {
      const path = new URL(route.request().url()).pathname;
      if (/\/edition-(?:motion|personality)\.css$/.test(path)) {
        heldEnhancements.add(path);
        await enhancementGate;
      } else await baseGate;
      await route.continue();
    });
    const heading = page.locator('.premiere-hero h1.premiere-statement');
    const typography = () => heading.evaluate(el => {
      const style = getComputedStyle(el);
      return { family: style.fontFamily, weight: style.fontWeight, size: style.fontSize };
    });
    try {
      // All external CSS is held first, so this is the complete inline design.
      await page.goto(`${prefix}/`, { waitUntil: 'domcontentloaded' });
      await expect(heading).toBeVisible();
      await expect(heading).toHaveCSS('opacity', '1');
      const initial = await typography();
      expect(initial.family).toContain('Inter');
      expect(initial.weight).toBe('900');

      // Apply the older base layer while holding its later overrides. The
      // complete critical cascade must still win during this intermediate state.
      releaseBase();
      // Release occupied connections before expecting later stylesheet requests.
      await expect.poll(() => heldEnhancements.size).toBe(2);
      const baseSheet = page.locator('link[rel="stylesheet"][href*="/css/edition-2027.css"]');
      await expect(baseSheet).toHaveAttribute('media', 'all');
      await expect.poll(() => page.locator('link[rel="stylesheet"]').evaluateAll(links =>
        links.filter(link => !/\/edition-(?:motion|personality)\.css(?:\?|$)/.test(link.href))
          .every(link => link.media === 'all' && link.sheet !== null)
      )).toBe(true);
      expect(await typography()).toEqual(initial);
      await expect(heading).toBeVisible();
      await expect(heading).toHaveCSS('opacity', '1');

      releaseEnhancements();
      await page.waitForLoadState('load');
      expect(await typography()).toEqual(initial);
      await expect(heading).toBeVisible();
      await expect(heading).toHaveCSS('opacity', '1');
    } finally {
      releaseBase();
      releaseEnhancements();
    }
  });

  test(`${prefix || '/'}: homepage respects the saved motion choice without floating controls`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(`${prefix}/news`);
    const toggle = page.locator('.e27-motion-toggle');
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await page.goto(`${prefix}/`);
    await expect(toggle).toHaveCount(0);
    await expect(page.locator('.premiere-film-toggle, .e27-video-toggle')).toHaveCount(0);
    await expect(page.locator('body')).toHaveClass(/e27-motion-paused/);
    expect(await page.locator('#heroVideo, #heroAmbientVideo').evaluateAll(videos => videos.map(el => ({ paused: el.paused, source: el.getAttribute('src') })))).toEqual([{ paused: true, source: null }, { paused: true, source: null }]);
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '1');
    await page.goBack();
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await page.goForward();
    await expect(toggle).toHaveCount(0);
    await expect(page.locator('body')).not.toHaveClass(/e27-motion-paused/);
    await expect.poll(() => page.locator('#heroVideo').evaluate(el => !el.paused && el.currentTime > 0.1), { timeout: 15000 }).toBe(true);
  });

  test(`${prefix || '/'}: a restored page picks up the saved motion preference`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(`${prefix}/news`);
    const toggle = page.locator('.e27-motion-toggle');
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
    // Simulate a preference changed elsewhere while this document was cached.
    await page.evaluate(() => {
      sessionStorage.setItem('msc-motion-paused', 'true');
      dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
    });
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(await page.evaluate(() => document.getAnimations().filter(a => a.effect.getComputedTiming().iterations === Infinity).every(a => a.playState === 'paused'))).toBe(true);
  });

  test(`${prefix || '/'}: reduced motion leaves content still and visible`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(`${prefix}/`);
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('#edition-facts')).toContainText('Devero Hotel');
    await expect(page.locator('.e27-motion-toggle')).toHaveCount(0);
    await expect(page.locator('body')).not.toHaveClass(/e27-motion-on/);
    expect(await page.locator('#heroVideo, #heroAmbientVideo').evaluateAll(videos => videos.map(el => ({ paused: el.paused, source: el.getAttribute('src') })))).toEqual([{ paused: true, source: null }, { paused: true, source: null }]);
    if (await page.evaluate(() => matchMedia('(hover: hover)').matches)) {
      const portrait = page.locator('.e27-artist img').first();
      await portrait.hover();
      await expect(portrait).toHaveCSS('transform', 'none');
    }
    await page.locator('.premiere-hero').evaluate(el => el.scrollIntoView({ behavior: 'instant' }));
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await expect.poll(() => page.locator('#heroVideo').evaluate(el => !el.paused && el.currentTime > 0.1), { timeout: 15000 }).toBe(true);
    await expect(page.locator('.e27-motion-toggle')).toHaveCount(0);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect(page.locator('.e27-motion-toggle')).toHaveCount(0);
    await expect.poll(() => page.locator('#heroVideo, #heroAmbientVideo').evaluateAll(videos => videos.every(el => el.paused))).toBe(true);
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '1');
  });

  test(`${prefix || '/'}: homepage has no chapter guide or floating click shield`, async ({ page }) => {
    await page.goto(`${prefix}/`);
    await expect(page.locator('.scene-progress')).toHaveCount(0);
    const form = page.locator('#reminder-form');
    await page.evaluate(() => document.fonts.ready);
    await form.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await expect.poll(() => form.locator('button[type="submit"]').evaluate(button => {
      const bounds = button.getBoundingClientRect();
      return button.contains(document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2));
    })).toBe(true);
    await expect(page.locator('.scene-progress')).toHaveCount(0);
  });
}
