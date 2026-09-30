import { test, expect } from '@playwright/test';

const heroMovie = /\/msc-2027-duomo-wordmark-(?:hero-intro|ambient-loop)-v07-(?:480|720|1080)\.mp4(?:\?|$)/;

// Keep the real local MP4 and browser decoder; isolate external services only.
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const path of ['/', '/it/']) {
  test(`${path}: the Duomo opening hands off to a moving sky without restarting the introduction`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      // Cover the viewport fallback used by browsers without network hints.
      Object.defineProperty(navigator, 'connection', { configurable: true, value: undefined });
      // The movie must not compete with the poster and initial resources.
      window.addEventListener('load', () => {
        window.heroSourcesAtLoadStart = [...document.querySelectorAll('#heroVideo, #heroAmbientVideo')].map(el => el.getAttribute('src'));
        document.getElementById('heroAmbientVideo').addEventListener('playing', event => {
          window.firstAmbientPlayingTime ??= event.target.currentTime;
        });
      }, { once: true });
    });
    await page.goto(path);
    const video = page.locator('#heroVideo');
    const ambient = page.locator('#heroAmbientVideo');
    expect(await page.evaluate(() => window.heroSourcesAtLoadStart)).toEqual([null, null]);
    await expect(video).toHaveAttribute('src', heroMovie);
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '1');
    await expect(page.locator('.e27-video-toggle, .premiere-film-toggle, .e27-motion-toggle')).toHaveCount(0);

    // Observe decoded motion, rather than only an HTTP response or play() call.
    await expect.poll(() => video.evaluate(el => ({
      error: el.error ? { code: el.error.code, message: el.error.message } : null,
      playing: !el.paused,
      advanced: el.currentTime > 0.25,
    })), { timeout: 15000, message: 'The actual Duomo MP4 decodes and autoplays without a click or tap' })
      .toEqual({ error: null, playing: true, advanced: true });
    const playback = await video.evaluate(el => ({
      muted: el.muted,
      // Firefox plays inline but does not expose the playsInline IDL property.
      inline: el.hasAttribute('playsinline') && (!('playsInline' in el) || el.playsInline),
      fullscreen: Boolean(document.fullscreenElement || el.webkitDisplayingFullscreen),
      loop: el.loop,
      width: el.videoWidth,
      height: el.videoHeight,
      duration: el.duration,
      time: el.currentTime,
    }));
    expect(playback).toMatchObject({ muted: true, inline: true, fullscreen: false, loop: false });
    expect(playback.height).toBe(page.viewportSize().width <= 1000 ? 720 : 1080);
    expect(playback.width / playback.height).toBeCloseTo(16 / 9, 2);
    expect(playback.duration).toBeCloseTo(10, 1);
    await expect.poll(() => video.evaluate(el => el.currentTime), {
      message: 'Playback continues beyond the first decoded frame',
    }).toBeGreaterThan(playback.time + 0.25);

    // The film takes over from the initial statement once its event title
    // appears; the reserved heading space must not make the page jump.
    const introHeight = await page.locator('.premiere-intro').evaluate(el => el.getBoundingClientRect().height);
    await video.evaluate(el => { el.currentTime = 6; });
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '0');
    expect(await page.locator('.premiere-intro').evaluate(el => el.getBoundingClientRect().height)).toBeCloseTo(introHeight, 1);

    // Let the real decoder finish the introduction. The camera/title remain
    // fixed while a separate seamless sky film takes over.
    await video.evaluate(el => { el.currentTime = el.duration - 0.4; });
    await expect.poll(() => video.evaluate(el => el.ended && el.paused)).toBe(true);
    const end = await video.evaluate(el => el.currentTime);
    await expect(ambient).toHaveAttribute('src', heroMovie);
    await expect.poll(() => ambient.evaluate(el => ({
      error: el.error ? { code: el.error.code, message: el.error.message } : null,
      playing: !el.paused,
      advanced: el.currentTime > 1.25,
    })), { timeout: 15000, message: 'The ambient sky decodes and moves after the introduction' })
      .toEqual({ error: null, playing: true, advanced: true });
    const firstAmbientTime = await page.evaluate(() => window.firstAmbientPlayingTime);
    expect(firstAmbientTime, 'The sky starts at the frame matching the end of the intro').toBeGreaterThanOrEqual(1.15);
    expect(firstAmbientTime).toBeLessThan(1.7);
    const ambientPlayback = await ambient.evaluate(el => ({
      muted: el.muted,
      inline: el.hasAttribute('playsinline') && (!('playsInline' in el) || el.playsInline),
      loop: el.loop,
      duration: el.duration,
      time: el.currentTime,
    }));
    expect(ambientPlayback).toMatchObject({ muted: true, inline: true, loop: true });
    expect(ambientPlayback.duration).toBeCloseTo(9.25, 1);
    await expect.poll(() => ambient.evaluate(el => el.currentTime)).toBeGreaterThan(ambientPlayback.time + .25);
    await expect(ambient).toHaveCSS('opacity', '1');

    // Observe a native repeat and continuing motion, not a frozen last frame
    // or a second run through the opening camera move.
    await ambient.evaluate(el => {
      window.ambientRepeated = false;
      let previous = el.currentTime;
      el.addEventListener('timeupdate', () => {
        if (previous > el.duration - 1 && el.currentTime < 1) window.ambientRepeated = true;
        previous = el.currentTime;
      });
      el.currentTime = el.duration - .4;
    });
    // Record the wrap in-page so the assertion cannot miss the first second
    // between cross-browser polling intervals on a busy test runner.
    await expect.poll(() => page.evaluate(() => window.ambientRepeated), { timeout: 10000 }).toBe(true);
    await expect.poll(() => ambient.evaluate(el => !el.paused && el.currentTime > .25)).toBe(true);
    expect(await video.evaluate(el => ({ paused: el.paused, ended: el.ended, time: el.currentTime }))).toEqual({ paused: true, ended: true, time: end });
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '0');

    await page.locator('#artist-showcase').evaluate(el => el.scrollIntoView({ behavior: 'instant' }));
    await expect(ambient).toHaveJSProperty('paused', true);
    const pausedAt = await ambient.evaluate(el => el.currentTime);
    await page.waitForTimeout(300);
    expect(await ambient.evaluate(el => el.currentTime)).toBeCloseTo(pausedAt, 2);
    await page.locator('.premiere-hero').evaluate(el => el.scrollIntoView({ behavior: 'instant' }));
    await expect.poll(() => ambient.evaluate(el => el.currentTime)).toBeGreaterThan(pausedAt + .1);

    // Simulate the browser's visibility signal without depending on whether
    // a particular headless engine backgrounds a second test tab.
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await expect(ambient).toHaveJSProperty('paused', true);
    await expect(video).toHaveJSProperty('paused', true);
    await page.evaluate(() => {
      delete document.hidden;
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await expect.poll(() => ambient.evaluate(el => !el.paused)).toBe(true);
    expect(await video.evaluate(el => ({ ended: el.ended, time: el.currentTime }))).toEqual({ ended: true, time: end });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect.poll(() => page.locator('#heroVideo, #heroAmbientVideo').evaluateAll(videos => videos.every(el => el.paused))).toBe(true);
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '1');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await expect.poll(() => ambient.evaluate(el => !el.paused)).toBe(true);
    await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '0');
  });

  for (const preference of ['data saving', 'reduced motion', 'slow 2g']) {
    test(`${path}: ${preference} retains the poster without downloading either hero video`, async ({ page }) => {
      await page.emulateMedia({ reducedMotion: preference === 'reduced motion' ? 'reduce' : 'no-preference' });
      if (preference === 'data saving') await page.addInitScript(() => {
        Object.defineProperty(navigator, 'connection', { configurable: true, value: { saveData: true } });
      });
      if (preference === 'slow 2g') await page.addInitScript(() => {
        Object.defineProperty(navigator, 'connection', { configurable: true, value: { effectiveType: '2g', downlink: .25, saveData: false } });
      });
      const movieRequests = [];
      page.on('request', request => {
        if (heroMovie.test(new URL(request.url()).pathname)) movieRequests.push(request.url());
      });
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('.premiere-poster-image')).toBeVisible();
      await expect(page.locator('#heroVideo')).toHaveAttribute('data-poster', /wordmark-hero-poster-v07\.webp$/);
      // Allow the deferred enhancement to run before asserting that it avoided
      // the download; an immediate post-load snapshot could miss that work.
      await page.waitForTimeout(1600);
      const states = await page.locator('#heroVideo, #heroAmbientVideo').evaluateAll(videos => videos.map(el => ({
        source: el.getAttribute('src'),
        paused: el.paused,
        time: el.currentTime,
      })));
      expect(states).toEqual([{ source: null, paused: true, time: 0 }, { source: null, paused: true, time: 0 }]);
      expect(movieRequests).toEqual([]);
      await expect(page.locator('.premiere-statement')).toHaveCSS('opacity', '1');
      await expect(page.locator('.e27-video-toggle, .premiere-film-toggle, .e27-motion-toggle')).toHaveCount(0);
    });
  }

  test(`${path}: a slow connection selects a real 480p film and keeps the poster until it decodes`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      const connection = new EventTarget();
      Object.assign(connection, { effectiveType: '3g', downlink: .8, saveData: false });
      Object.defineProperty(navigator, 'connection', { configurable: true, value: connection });
    });
    const requests = [];
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route(heroMovie, async route => { requests.push(route.request().url()); await gate; await route.continue(); });
    try {
      await page.goto(path);
      const film = page.locator('#heroVideo');
      await expect(film).toHaveAttribute('src', /-480\.mp4$/);
      await expect(page.locator('.premiere-poster-image')).toBeVisible();
      await expect.poll(() => page.locator('.premiere-poster-image').evaluate(el => el.complete && el.naturalWidth > 0)).toBe(true);
      await expect(film).not.toHaveClass(/has-played/);
      release();
      await expect.poll(() => film.evaluate(el => el.videoHeight === 480 && !el.paused && el.currentTime > .25), { timeout: 15000 }).toBe(true);
      await film.evaluate(el => { el.currentTime = 4; });
      await expect(page.locator('#heroAmbientVideo')).toHaveAttribute('src', /-480\.mp4$/);
      expect(requests.length).toBeGreaterThan(0);
      expect(requests.every(url => /-480\.mp4$/.test(url))).toBe(true);
      const source = await film.getAttribute('src');
      const time = await film.evaluate(el => el.currentTime);
      await page.evaluate(() => {
        Object.assign(navigator.connection, { effectiveType: '4g', downlink: 10 });
        navigator.connection.dispatchEvent(new Event('change'));
      });
      await expect(film).toHaveAttribute('src', source);
      expect(await film.evaluate(el => el.currentTime)).toBeGreaterThanOrEqual(time);
      await page.evaluate(() => {
        navigator.connection.saveData = true;
        navigator.connection.dispatchEvent(new Event('change'));
      });
      await expect(film).toHaveJSProperty('paused', true);
      await expect(page.locator('#heroAmbientVideo')).toHaveJSProperty('paused', true);
    } finally { release(); }
  });
}
