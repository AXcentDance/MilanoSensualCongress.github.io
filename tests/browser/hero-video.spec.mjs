import { test, expect } from '@playwright/test';

// Keep the real local MP4 and browser decoder; isolate external services only.
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const path of ['/', '/it/']) {
  test(`${path}: hero video plays inline without interaction after the page loads`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      // Register before the page's loader: the movie must not compete with
      // the poster and other initial resources before window.load begins.
      window.addEventListener('load', () => {
        window.heroSourceAtLoadStart = document.getElementById('heroVideo').getAttribute('src');
      }, { once: true });
    });
    await page.goto(path);
    const video = page.locator('#heroVideo');
    expect(await page.evaluate(() => window.heroSourceAtLoadStart)).toBeNull();
    await expect(video).toHaveAttribute('src', /hero-720\.mp4(?:\?|$)/);

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
    expect(playback).toMatchObject({ muted: true, inline: true, fullscreen: false, loop: true, width: 1280, height: 720 });
    expect(playback.duration).toBeCloseTo(45.833333, 1);
    await expect.poll(() => video.evaluate(el => el.currentTime), {
      message: 'Playback continues beyond the first decoded frame',
    }).toBeGreaterThan(playback.time + 0.25);
  });

  test(`${path}: data saving retains the poster without downloading the hero video`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'connection', { configurable: true, value: { saveData: true } });
    });
    const movieRequests = [];
    page.on('request', request => {
      if (new URL(request.url()).pathname.endsWith('/hero-720.mp4')) movieRequests.push(request.url());
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
}
