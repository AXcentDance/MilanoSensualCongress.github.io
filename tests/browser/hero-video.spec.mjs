import { test, expect } from '@playwright/test';

// Keep the real local MP4 and browser decoder; isolate external services only.
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const path of ['/', '/it/']) {
  test(`${path}: hero video plays inline without interaction after the page loads`, async ({ page }, testInfo) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'connection', { configurable: true, value: undefined });
      // Register before the page's loader: the movie must not compete with
      // the poster and other initial resources before window.load begins.
      window.addEventListener('load', () => {
        window.heroSourceAtLoadStart = document.getElementById('heroVideo').getAttribute('src');
      }, { once: true });
    });
    await page.goto(path);
    const video = page.locator('#heroVideo');
    expect(await page.evaluate(() => window.heroSourceAtLoadStart)).toBeNull();
    const smallScreen = testInfo.project.use.viewport.width <= 1000;
    await expect(video).toHaveAttribute('src', new RegExp(`hero-loop-v1-${smallScreen ? 480 : 720}\\.mp4$`));

    // A poster, successful HTTP response, or play() call alone cannot prove
    // that a browser can decode this asset. Observe real playback progress.
    await expect.poll(() => video.evaluate(el => ({
      error: el.error ? { code: el.error.code, message: el.error.message } : null,
      playing: !el.paused,
      advanced: el.currentTime > 0.25,
    })), { timeout: 15000, message: 'The actual hero MP4 decodes and autoplays without a click or tap' })
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
    expect(playback).toMatchObject({ muted: true, inline: true, fullscreen: false, loop: true,
      width: smallScreen ? 854 : 1280, height: smallScreen ? 480 : 720 });
    expect(playback.duration).toBeCloseTo(12, 1);
    await expect.poll(() => video.evaluate(el => el.currentTime), {
      message: 'Playback continues beyond the first decoded frame',
    }).toBeGreaterThan(playback.time + 0.25);
    await video.evaluate(el => {
      window.heroLooped = false;
      let previous = el.duration - .4;
      el.addEventListener('timeupdate', () => {
        if (previous > el.duration - 1 && el.currentTime < 1) window.heroLooped = true;
        previous = el.currentTime;
      });
      el.currentTime = el.duration - .4;
    });
    await expect.poll(() => page.evaluate(() => window.heroLooped), { timeout: 6000 }).toBe(true);
  });

  test(`${path}: data saving retains the poster without downloading the hero video`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'connection', { configurable: true, value: { saveData: true } });
    });
    const movieRequests = [];
    page.on('request', request => {
      if (new URL(request.url()).pathname.endsWith('.mp4')) movieRequests.push(request.url());
    });
    await page.goto(path);
    await expect(page.locator('h1')).toBeVisible();
    const state = await page.locator('#heroVideo').evaluate(el => ({
      source: el.getAttribute('src'),
      paused: el.paused,
      time: el.currentTime,
      poster: el.getAttribute('poster'),
    }));
    expect(state).toMatchObject({ source: null, paused: true, time: 0 });
    expect(state.poster).toMatch(/poster\.webp$/);
    expect(movieRequests).toEqual([]);
  });

  test(`${path}: very slow connections retain the poster`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'connection', { configurable: true,
        value: { effectiveType: '2g', downlink: .2, saveData: false } });
    });
    const movies = [];
    page.on('request', request => { if (new URL(request.url()).pathname.endsWith('.mp4')) movies.push(request.url()); });
    await page.goto(path);
    await expect(page.locator('h1')).toBeVisible();
    expect(await page.locator('#heroVideo').getAttribute('src')).toBeNull();
    expect(movies).toEqual([]);
  });

  test(`${path}: slow connections use the economy clip and keep their chosen source`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      const connection = new EventTarget();
      Object.assign(connection, { effectiveType: '3g', downlink: 1, saveData: false });
      Object.defineProperty(navigator, 'connection', { configurable: true, value: connection });
    });
    await page.goto(path);
    const video = page.locator('#heroVideo');
    await expect(video).toHaveAttribute('src', /hero-loop-v1-360\.mp4$/);
    await expect.poll(() => video.evaluate(el => !el.paused && el.currentTime > .25 && el.videoWidth === 640)).toBe(true);
    const source = await video.getAttribute('src');
    await page.evaluate(() => {
      navigator.connection.saveData = true;
      navigator.connection.dispatchEvent(new Event('change'));
    });
    await expect.poll(() => video.evaluate(el => el.paused)).toBe(true);
    await page.evaluate(() => {
      Object.assign(navigator.connection, { saveData: false, effectiveType: '4g', downlink: 10 });
      navigator.connection.dispatchEvent(new Event('change'));
    });
    await expect.poll(() => video.evaluate(el => !el.paused)).toBe(true);
    await page.setViewportSize({ width: 1440, height: 900 });
    expect(await video.getAttribute('src')).toBe(source);
  });

  test(`${path}: hero pauses offscreen, in hidden tabs and for reduced motion`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(path);
    const video = page.locator('#heroVideo');
    await expect.poll(() => video.evaluate(el => !el.paused && el.currentTime > .25)).toBe(true);
    const source = await video.getAttribute('src');
    await page.locator('footer').scrollIntoViewIfNeeded();
    await expect.poll(() => video.evaluate(el => el.paused)).toBe(true);
    await page.locator('h1').scrollIntoViewIfNeeded();
    await expect.poll(() => video.evaluate(el => !el.paused)).toBe(true);
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: true });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await expect.poll(() => video.evaluate(el => el.paused)).toBe(true);
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, value: false });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await expect.poll(() => video.evaluate(el => !el.paused)).toBe(true);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect.poll(() => video.evaluate(el => el.paused)).toBe(true);
    expect(await video.getAttribute('src')).toBe(source);
  });
}
