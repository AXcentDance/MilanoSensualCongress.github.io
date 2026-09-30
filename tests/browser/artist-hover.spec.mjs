import { test, expect } from '@playwright/test';

const preview = '.e27-artist-preview';
const artist = '#artist-showcase [data-artist-video]';
const embedOrigin = 'https://www.youtube-nocookie.com';
const localPreviewRoot = '/images/artists/klau-ros-insomnia-mexico-preview-v01/';
const klau = `${artist}[data-artist-name="Klau y Ros"]`;
const isPhone = page => page.viewportSize().width <= 600;
const playButton = card => card.locator('.e27-artist-play');

async function expectButtonState(card, pressed) {
  const button = playButton(card);
  await expect(button).toHaveAttribute('aria-pressed', String(pressed));
  const label = await button.getAttribute(pressed ? 'data-stop-label' : 'data-play-label');
  await expect(button).toHaveAttribute('aria-label', label);
  if (await button.isVisible()) await expect(button).toHaveAccessibleName(label);
}

async function activatePreview(page, card) {
  if (isPhone(page)) await playButton(card).click();
  else await hoverCard(page, card);
}

async function expectScrollUnchanged(page, before) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  expect(await page.evaluate(() => scrollY), 'Preview controls leave the page at the visitor’s scroll position').toBe(before);
}

function watchLocalPreviewRequests(page) {
  const requests = [];
  page.on('request', request => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith(localPreviewRoot)) requests.push(pathname.slice(localPreviewRoot.length));
  });
  return requests;
}

async function settleCard(card) {
  await card.evaluate(async element => {
    await document.fonts.ready;
    element.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(requestAnimationFrame);
    await Promise.all(element.getAnimations().filter(animation => animation.playState === 'running')
      .map(animation => animation.finished.catch(() => {})));
    element.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(requestAnimationFrame);
  });
}

async function hoverCard(page, card) {
  await settleCard(card);
  const rect = await card.boundingBox();
  await page.mouse.move(rect.x + rect.width / 2, rect.y + rect.height / 2);
}

async function stubEmbeds(page, mode = 'playing') {
  const requests = [];
  await page.route('https://**/*', route => {
    if (!route.request().url().startsWith(`${embedOrigin}/embed/`)) return route.fulfill({ status: 200, body: '' });
    requests.push(route.request().url());
    return route.fulfill({ status: 200, contentType: 'text/html', body: `<!doctype html><title>Dance preview fixture</title><script>
      addEventListener('message', event => {
        let data; try { data = JSON.parse(event.data); } catch (_) { return; }
        const send = value => parent.postMessage(JSON.stringify(value), event.origin);
        if (data.event === 'listening') send({ event: 'initialDelivery', info: { playerState: -1 } });
        if (data.func === 'playVideo' && ${JSON.stringify(mode)} === 'playing') send({ event: 'onStateChange', info: 1 });
        if (data.func === 'playVideo' && ${JSON.stringify(mode)} === 'error') send({ event: 'onError', info: 101 });
      });
    </script>` });
  });
  return requests;
}

for (const path of ['/', '/it/']) {
  test(`${path}: artist previews require hover intent or the phone play button`, async ({ page }, info) => {
    const requests = await stubEmbeds(page);
    await page.goto(path);
    const cards = page.locator(artist);
    await expect(cards).toHaveCount(8);
    await expect(cards.locator('.e27-artist-number')).toHaveCount(0);
    await expect(cards.locator('.e27-artist-play')).toHaveCount(8);
    await cards.first().scrollIntoViewIfNeeded();
    await expect(page.locator(preview)).toHaveCount(0);
    expect(requests).toEqual([]);

    if (!info.project.use.hasTouch) {
      await expect(playButton(cards.first())).toBeHidden();
      await hoverCard(page, cards.first());
      // Moving straight past a card must not contact the external video host.
      await page.mouse.move(0, 0);
      await expect(page.locator(preview)).toHaveCount(0);
      await hoverCard(page, cards.first());
      await expect(cards.first()).toHaveClass(/e27-preview-playing/);
      const frame = cards.first().locator(preview);
      await expect(frame).toHaveAttribute('title', /Gero y Migle/);
      await expect(frame).toHaveAttribute('tabindex', '-1');
      const src = new URL(await frame.getAttribute('src'));
      expect(src.origin).toBe(embedOrigin);
      for (const [key, value] of Object.entries({ autoplay: '1', mute: '1', controls: '0', playsinline: '1' })) expect(src.searchParams.get(key)).toBe(value);
      await expect(cards.first().locator('h3')).toBeVisible();
      await expect(frame).toHaveCSS('pointer-events', 'none');
      await hoverCard(page, cards.nth(2));
      await expect(cards.nth(2)).toHaveClass(/e27-preview-playing/);
      await expect(page.locator(preview)).toHaveCount(1);
      await expect(cards.first().locator(preview)).toHaveCount(0);
      await page.mouse.move(0, 0);
      await expect(page.locator(preview)).toHaveCount(0);
      await hoverCard(page, cards.first());
      await expect(cards.first()).toHaveClass(/e27-preview-playing/);
    } else {
      // Touching a portrait never starts media by itself.
      await cards.first().dispatchEvent('pointerenter', { pointerType: 'touch' });
      await page.waitForTimeout(300);
      await expect(page.locator(preview)).toHaveCount(0);
      expect(requests).toEqual([]);
      if (isPhone(page)) {
        await settleCard(cards.first());
        const firstButton = playButton(cards.first());
        await expect(firstButton).toBeVisible();
        await expectButtonState(cards.first(), false);
        const bounds = await firstButton.boundingBox();
        expect(bounds.width).toBeGreaterThanOrEqual(44);
        expect(bounds.height).toBeGreaterThanOrEqual(44);
        const playScroll = await page.evaluate(() => scrollY);
        await firstButton.tap();
        await expect(cards.first()).toHaveClass(/e27-preview-playing/);
        await expectScrollUnchanged(page, playScroll);
        await expectButtonState(cards.first(), true);
        await expect(firstButton).toHaveAttribute('aria-busy', 'false');
        const stopScroll = await page.evaluate(() => scrollY);
        await firstButton.tap();
        await expect(page.locator(preview)).toHaveCount(0);
        await expectScrollUnchanged(page, stopScroll);
        await expectButtonState(cards.first(), false);
        // A keyboard user can reach the name/button after its photo has
        // scrolled above the viewport. Play and stop must preserve that position.
        await firstButton.evaluate(button => {
          button.focus({ preventScroll: true });
          const photo = button.closest('[data-artist-video]').querySelector('.e27-artist-photo');
          scrollBy({ top: photo.getBoundingClientRect().bottom + 2, behavior: 'instant' });
        });
        await expect(firstButton).toBeInViewport();
        expect(await cards.first().locator('.e27-artist-photo').evaluate(el => el.getBoundingClientRect().bottom)).toBeLessThanOrEqual(0);
        const edgeScroll = await page.evaluate(() => scrollY);
        await page.keyboard.press('Space');
        await expect(cards.first()).toHaveClass(/e27-preview-playing/);
        await expectScrollUnchanged(page, edgeScroll);
        expect(await cards.first().locator('.e27-artist-photo').evaluate(el => el.getBoundingClientRect().bottom)).toBeLessThanOrEqual(0);
        await expect(firstButton).toBeFocused();
        await page.keyboard.press('Space');
        await expect(page.locator(preview)).toHaveCount(0);
        await expectScrollUnchanged(page, edgeScroll);
        await page.keyboard.press('Space');
        await expect(cards.first()).toHaveClass(/e27-preview-playing/);
        await expectScrollUnchanged(page, edgeScroll);
        await cards.nth(2).evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
        const switchScroll = await page.evaluate(() => scrollY);
        await playButton(cards.nth(2)).tap();
        await expect(cards.nth(2)).toHaveClass(/e27-preview-playing/);
        await expectScrollUnchanged(page, switchScroll);
        await expect(page.locator(preview)).toHaveCount(1);
        await expect(cards.first().locator(preview)).toHaveCount(0);
        await expectButtonState(cards.first(), false);
        await expectButtonState(cards.nth(2), true);
        await playButton(cards.nth(2)).focus();
        const keyboardStopScroll = await page.evaluate(() => scrollY);
        await page.keyboard.press('Enter');
        await expect(page.locator(preview)).toHaveCount(0);
        await expectScrollUnchanged(page, keyboardStopScroll);
        await expectButtonState(cards.nth(2), false);
        await firstButton.tap();
        await expect(cards.first()).toHaveClass(/e27-preview-playing/);
      } else await expect(playButton(cards.first())).toBeHidden();
    }
    const url = page.url();
    const activeFrame = await cards.first().locator(preview).count() ? await cards.first().locator(preview).elementHandle() : null;
    const requestCount = requests.length;
    await cards.first().locator('img').click();
    await expect(page).toHaveURL(url);
    await expect(page.locator('#artist-player')).toHaveCount(0);
    expect(page.context().pages()).toHaveLength(1);
    expect(requests).toHaveLength(requestCount);
    if (activeFrame) {
      expect(await activeFrame.evaluate(el => el.isConnected)).toBe(true);
      await expect(cards.first()).toHaveClass(/e27-preview-playing/);
      if (isPhone(page)) await playButton(cards.first()).click();
      else await page.mouse.move(0, 0);
    }
    await expect(page.locator(preview)).toHaveCount(0);
  });

  for (const name of ['Gero y Migle', 'Klau y Ros']) {
    test(`${path}: ${name} artist hover previews stop offscreen and obey motion and data preferences`, async ({ page }, info) => {
      test.skip(!!info.project.use.hasTouch && !isPhone(page), 'Tablet portraits retain passive touch behavior.');
      const embeds = await stubEmbeds(page);
      const localRequests = watchLocalPreviewRequests(page);
      await page.addInitScript(() => {
        const connection = new EventTarget();
        connection.saveData = false;
        Object.defineProperty(navigator, 'connection', { configurable: true, value: connection });
      });
      await page.goto(path);
      const first = page.locator(`${artist}[data-artist-name="${name}"]`);
      if (isPhone(page)) {
        await page.emulateMedia({ reducedMotion: 'reduce' });
        await page.evaluate(() => { navigator.connection.saveData = true; navigator.connection.dispatchEvent(new Event('change')); });
        await first.scrollIntoViewIfNeeded();
        await first.dispatchEvent('pointerenter', { pointerType: 'touch' });
        await first.dispatchEvent('pointerenter', { pointerType: 'mouse' });
        await page.waitForTimeout(300);
        await expect(page.locator(preview)).toHaveCount(0);
        expect(embeds).toEqual([]);
        expect(localRequests).toEqual([]);
        await activatePreview(page, first);
        await expect(first).toHaveClass(/e27-preview-playing/);
        await expectButtonState(first, true);
        await first.dispatchEvent('pointerleave', { pointerType: 'mouse' });
        await expect(first).toHaveClass(/e27-preview-playing/);
        await page.evaluate(() => scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }));
        await expect(page.locator(preview)).toHaveCount(0);
        await expectButtonState(first, false);
        await activatePreview(page, first);
        await expect(first).toHaveClass(/e27-preview-playing/);
        await page.evaluate(() => document.body.classList.add('e27-motion-paused'));
        await expect(page.locator(preview)).toHaveCount(0);
        await expectButtonState(first, false);
        await activatePreview(page, first);
        await page.waitForTimeout(300);
        await expect(page.locator(preview)).toHaveCount(0);
        await page.evaluate(() => document.body.classList.remove('e27-motion-paused'));
        await activatePreview(page, first);
        await expect(first).toHaveClass(/e27-preview-playing/);
        await page.evaluate(() => {
          Object.defineProperty(document, 'hidden', { configurable: true, value: true });
          document.dispatchEvent(new Event('visibilitychange'));
        });
        await expect(page.locator(preview)).toHaveCount(0);
        await expectButtonState(first, false);
        return;
      }
      const enter = async () => { await page.mouse.move(0, 0); await hoverCard(page, first); };
      await enter();
      await expect(first).toHaveClass(/e27-preview-playing/);
      await page.evaluate(() => scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }));
      await expect(page.locator(preview)).toHaveCount(0);
      await enter();
      await expect(first).toHaveClass(/e27-preview-playing/);
      await page.evaluate(() => document.body.classList.add('e27-motion-paused'));
      await expect(page.locator(preview)).toHaveCount(0);
      await enter();
      await page.waitForTimeout(300);
      await expect(page.locator(preview)).toHaveCount(0);
      await page.evaluate(() => document.body.classList.remove('e27-motion-paused'));
      await enter();
      await expect(first).toHaveClass(/e27-preview-playing/);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await expect(page.locator(preview)).toHaveCount(0);
      await enter();
      await page.waitForTimeout(300);
      await expect(page.locator(preview)).toHaveCount(0);
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await enter();
      await expect(first).toHaveClass(/e27-preview-playing/);
      await page.evaluate(() => { navigator.connection.saveData = true; navigator.connection.dispatchEvent(new Event('change')); });
      await expect(page.locator(preview)).toHaveCount(0);
      await enter();
      await page.waitForTimeout(300);
      await expect(page.locator(preview)).toHaveCount(0);
      await page.evaluate(() => { navigator.connection.saveData = false; navigator.connection.dispatchEvent(new Event('change')); });
      await enter();
      await expect(first).toHaveClass(/e27-preview-playing/);
      await page.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, value: true });
        document.dispatchEvent(new Event('visibilitychange'));
      });
      await expect(page.locator(preview)).toHaveCount(0);
    });
  }

  test(`${path}: Klau y Ros streams the real HD segments and loops through hover or the phone button`, async ({ page }, info) => {
    test.setTimeout(60000);
    const requests = watchLocalPreviewRequests(page);
    const embeds = await stubEmbeds(page);
    await page.goto(path);
    const card = page.locator(klau);
    const passiveTouch = info.project.use.hasTouch && !isPhone(page);
    await expect(card).toHaveAttribute('data-artist-preview', `${localPreviewRoot}index.m3u8`);
    await card.scrollIntoViewIfNeeded();
    await expect(card.locator(preview)).toHaveCount(0);
    expect(requests).toEqual([]);

    if (info.project.use.hasTouch) {
      await card.dispatchEvent('pointerenter', { pointerType: 'touch' });
      await page.waitForTimeout(350);
      await expect(card.locator(preview)).toHaveCount(0);
      expect(requests).toEqual([]);
    }
    if (!passiveTouch) {
      if (!isPhone(page)) {
        await hoverCard(page, card);
        await page.mouse.move(0, 0);
        await page.waitForTimeout(300);
        expect(requests).toEqual([]);
      }
      if (isPhone(page)) await settleCard(card);
      const startScroll = await page.evaluate(() => scrollY);
      await activatePreview(page, card);
      const video = card.locator(`video${preview}`);
      await expect(card).toHaveClass(/e27-preview-playing/);
      await expect.poll(() => video.evaluate(el => ({
        error: el.error?.code ?? null, playing: !el.paused, advanced: el.currentTime > .25,
      })), { timeout: 15000, message: 'The local clip must actually decode and advance after the intended interaction' })
        .toEqual({ error: null, playing: true, advanced: true });
      if (isPhone(page)) await expectScrollUnchanged(page, startScroll);
      expect(await video.evaluate(el => ({
        width: el.videoWidth, height: el.videoHeight, muted: el.muted, loop: el.loop,
        inline: el.hasAttribute('playsinline') && (!('playsInline' in el) || el.playsInline),
        controls: el.controls,
      }))).toEqual({ width: 1080, height: 1920, muted: true, loop: true, inline: true, controls: false });
      await expect(video).toHaveAttribute('tabindex', '-1');
      await expect(video).toHaveAttribute('aria-hidden', 'true');
      await expect(video).toHaveCSS('pointer-events', 'none');
      await expect(video).toHaveCSS('object-fit', 'cover');
      await expect(video).toHaveCSS('opacity', '1');
      await expect(card.locator('h3')).toBeVisible();
      await card.screenshot({ path: info.outputPath('klau-preview.png') });
      expect(embeds).toEqual([]);
      expect(requests).toContain('index.m3u8');
      // The MSE player should request only a short buffer ahead. Native HLS
      // chooses its own buffering policy, so its prefetch count is not fixed.
      if ((await video.getAttribute('src'))?.startsWith('blob:')) expect(requests).not.toContain('segment-004.m4s');

      await video.evaluate(el => {
        el.previewPlayback = { maximum: el.currentTime, looped: false, timeAfterLoop: 0 };
        let previous = el.currentTime;
        el.addEventListener('timeupdate', () => {
          const state = el.previewPlayback;
          state.maximum = Math.max(state.maximum, el.currentTime);
          if (previous > 18 && el.currentTime < 2) state.looped = true;
          if (state.looped) state.timeAfterLoop = el.currentTime;
          previous = el.currentTime;
        });
        // Let the actual decoder play the full clip at its natural rate.
        // Native HLS does not consistently support accelerated playback.
      });
      await expect.poll(() => video.evaluate(el => ({
        crossedAllSegments: el.previewPlayback.maximum > 19,
        loopedAndAdvancing: el.previewPlayback.looped && el.previewPlayback.timeAfterLoop > .25,
        error: el.error?.code ?? null,
      })), { timeout: 30000, message: 'Playback crosses segment boundaries, loops and continues decoding' })
        .toEqual({ crossedAllSegments: true, loopedAndAdvancing: true, error: null });
      // Fragment timestamps may include the encoder's two-frame reorder offset.
      expect(Math.abs((await video.evaluate(el => el.duration)) - 20)).toBeLessThan(.1);
      for (const filename of ['init.mp4', ...Array.from({ length: 5 }, (_, index) => `segment-00${index}.m4s`)]) {
        expect(requests).toContain(filename);
      }

      const removedVideo = await video.elementHandle();
      const stopScroll = await page.evaluate(() => scrollY);
      if (isPhone(page)) await playButton(card).click();
      else await page.mouse.move(0, 0);
      await expect(card.locator(preview)).toHaveCount(0);
      if (isPhone(page)) await expectScrollUnchanged(page, stopScroll);
      expect(await removedVideo.evaluate(el => ({ paused: el.paused, source: el.getAttribute('src'), connected: el.isConnected })))
        .toEqual({ paused: true, source: null, connected: false });
      const requestCount = requests.length;
      await page.waitForTimeout(400);
      expect(requests).toHaveLength(requestCount);
      const replayScroll = await page.evaluate(() => scrollY);
      await activatePreview(page, card);
      await expect(card).toHaveClass(/e27-preview-playing/);
      if (isPhone(page)) await expectScrollUnchanged(page, replayScroll);
      await expect(card.locator(preview)).toHaveCSS('opacity', '1');
    }

    await page.screenshot({ path: info.outputPath('artist-section.png') });
    await expect(card).not.toHaveAttribute('href');
    const url = page.url();
    const activeVideo = passiveTouch ? null : await card.locator(preview).elementHandle();
    await card.locator('img').click();
    await expect(page).toHaveURL(url);
    await expect(page.locator('#artist-player')).toHaveCount(0);
    expect(page.context().pages()).toHaveLength(1);
    expect(embeds).toEqual([]);
    if (activeVideo) {
      expect(await activeVideo.evaluate(el => el.isConnected && !el.paused)).toBe(true);
      const time = await activeVideo.evaluate(el => el.currentTime);
      await expect.poll(() => activeVideo.evaluate(el => el.currentTime)).toBeGreaterThan(time + .1);
      if (isPhone(page)) {
        const other = page.locator(artist).first();
        await playButton(other).click();
        await expect(other).toHaveClass(/e27-preview-playing/);
        await expect(page.locator(preview)).toHaveCount(1);
        await expectButtonState(card, false);
        expect(await activeVideo.evaluate(el => ({ paused: el.paused, source: el.getAttribute('src'), connected: el.isConnected })))
          .toEqual({ paused: true, source: null, connected: false });
        await page.setViewportSize({ width: 768, height: 1024 });
        await expect(page.locator(preview)).toHaveCount(0);
        await expect(playButton(other)).toBeHidden();
        await expectButtonState(other, false);
      } else await page.mouse.move(0, 0);
    } else {
      expect(requests).toEqual([]);
    }
    await expect(page.locator(preview)).toHaveCount(0);
  });

  test(`${path}: failed local artist hover streaming keeps the portrait and can recover on a later hover`, async ({ page }, info) => {
    test.skip(!!info.project.use.hasTouch && !isPhone(page), 'Tablet portraits never request the hover stream.');
    await stubEmbeds(page);
    const requests = watchLocalPreviewRequests(page);
    let fail = true;
    await page.route(`**${localPreviewRoot}index.m3u8`, route => fail ? route.abort('failed') : route.continue());
    await page.goto(path);
    const card = page.locator(klau);
    await activatePreview(page, card);
    await expect.poll(() => requests.length).toBeGreaterThan(0);
    await expect(card.locator(preview)).toHaveCount(0);
    await expect(card).not.toHaveClass(/e27-preview-(loading|playing)/);
    await expect(card.locator('img')).toBeVisible();
    await expect(card).not.toHaveAttribute('href');
    if (isPhone(page)) {
      await expectButtonState(card, false);
      await expect(playButton(card)).toHaveAttribute('aria-busy', 'false');
    }
    fail = false;
    await page.mouse.move(0, 0);
    await activatePreview(page, card);
    await expect(card).toHaveClass(/e27-preview-playing/);
    await expect.poll(() => card.locator(`video${preview}`).evaluate(el => el.currentTime)).toBeGreaterThan(.25);
  });

  test(`${path}: unavailable artist previews preserve the static portrait without a click action`, async ({ page }, info) => {
    test.skip(!!info.project.use.hasTouch && !isPhone(page), 'Tablet portraits remain static.');
    const requests = await stubEmbeds(page, 'error');
    await page.goto(path);
    const first = page.locator(artist).first();
    await activatePreview(page, first);
    await expect.poll(() => requests.length).toBe(1);
    await expect(page.locator(preview)).toHaveCount(0);
    await expect(first).not.toHaveClass(/e27-preview-(loading|playing)/);
    await expect(first.locator('img')).toBeVisible();
    await expect(first).not.toHaveAttribute('href');
    if (isPhone(page)) await expectButtonState(first, false);
    const url = page.url();
    await first.locator('img').click();
    await expect(page).toHaveURL(url);
    await expect(page.locator('#artist-player')).toHaveCount(0);
    await expect(page.locator(preview)).toHaveCount(0);
    expect(page.context().pages()).toHaveLength(1);
  });
}
