import { test, expect } from '@playwright/test';
import { sitePages } from '../../scripts/site-pages.mjs';

// Functional tests isolate external services. Lighthouse separately loads them normally.
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const entry of sitePages()) {
  test(`${entry.file}: content, assets, layout and navigation`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const response = await page.goto(entry.path);
    expect(response.status()).toBe(200);
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
    expect(await page.locator('h1').evaluate(el => {
      for (let node = el; node; node = node.parentElement) {
        if (+getComputedStyle(node).opacity <= .05) return false;
        if (node.getAnimations().some(a => a.effect.getKeyframes().some(f => Number(f.opacity) === 0))) return false;
      }
      return true;
    }), 'The main heading is visible without an opacity reveal').toBe(true);

    const navLogo = page.locator('nav img[src*="milano-sensual-congress-official-logo-nav-2027"]');
    await expect(navLogo).toHaveCount(1);
    await expect(navLogo).toBeVisible();
    await expect.poll(() => navLogo.evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    const logoGeometry = await navLogo.evaluate(async image => {
      // naturalWidth on a srcset image is density-corrected. Decode the chosen
      // URL alone to check its actual pixels against this device's resolution.
      const selected = new Image();
      selected.src = image.currentSrc;
      await selected.decode();
      const bounds = image.getBoundingClientRect();
      return {
        source: new URL(image.currentSrc).pathname,
        pixels: { width: selected.naturalWidth, height: selected.naturalHeight },
        rendered: { width: bounds.width, height: bounds.height },
        dpr: devicePixelRatio,
      };
    });
    expect(logoGeometry.source, 'Navigation selects a bounded logo variant').toMatch(/\/milano-sensual-congress-official-logo-nav-2027(?:_(?:100|175|300)w)?\.webp$/);
    expect(logoGeometry.pixels.width, 'The selected logo has enough pixels for its rendered size and device density').toBeGreaterThanOrEqual(Math.floor(logoGeometry.rendered.width * logoGeometry.dpr) - 2);
    expect(Math.abs(logoGeometry.rendered.width / logoGeometry.rendered.height - logoGeometry.pixels.width / logoGeometry.pixels.height), 'The navigation logo retains its image proportions').toBeLessThan(.03);

    const breadcrumb = page.locator('nav[aria-label*="readcrumb"]');
    if (entry.indexable && !['index.html', 'it/index.html'].includes(entry.file)) {
      await expect(breadcrumb).toBeHidden();
      await expect(breadcrumb).toHaveAttribute('hidden', '');
    }

    const menuButton = page.locator('button[aria-controls="mobile-menu"]');
    if (await menuButton.isVisible()) {
      await menuButton.focus();
      await page.keyboard.press('Enter');
      await expect(menuButton).toHaveAttribute('aria-expanded', 'true');
      await expect(page.locator('#mobile-menu')).toBeVisible();
      const links = page.locator('#mobile-menu a');
      expect(await links.count()).toBeGreaterThan(2);
      await page.keyboard.press('Enter');
      await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
      await expect(page.locator('#mobile-menu')).toBeHidden();
    }
    const nativeMenu = page.locator('details.mobile-nav, details.levels-mobile-menu');
    if (await nativeMenu.isVisible()) {
      await nativeMenu.locator('summary').click();
      await expect(nativeMenu).toHaveAttribute('open', '');
      await nativeMenu.locator('summary').click();
      await expect(nativeMenu).not.toHaveAttribute('open', '');
    }
    const question = page.locator('main details').first();
    if (await question.count()) {
      const initiallyOpen = await question.evaluate(el => el.open);
      await question.locator('summary').focus();
      await page.keyboard.press('Space');
      await expect.poll(() => question.evaluate(el => el.open)).toBe(!initiallyOpen);
      await page.keyboard.press('Space');
      await expect.poll(() => question.evaluate(el => el.open)).toBe(initiallyOpen);
    }
    const overflow = await page.evaluate(() => {
      const width = document.documentElement.clientWidth;
      return [...document.querySelectorAll('nav a, nav button, h1, main p, main table, form')]
        .filter(el => {
          const rect = el.getBoundingClientRect(), css = getComputedStyle(el);
          const closed = el.closest('details:not([open])');
          if (closed && !closed.querySelector('summary').contains(el)) return false;
          for (let parent = el.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
            if (['auto', 'scroll'].includes(getComputedStyle(parent).overflowX) && parent.scrollWidth > parent.clientWidth + 1) return false;
          }
          return rect.width && rect.height && css.visibility !== 'hidden' && (rect.left < -1 || rect.right > width + 1);
        }).map(el => `${el.tagName}: ${el.textContent.trim().slice(0,65)}`);
    });
    expect(overflow, 'Readable content and navigation fit the viewport').toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'No horizontal page overflow').toBe(true);

    // Reveal lazy images through the same scrolling available to visitors.
    await page.evaluate(async () => {
      for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight * .8) {
        scrollTo({ top: y, behavior: 'instant' });
        await new Promise(requestAnimationFrame);
      }
      scrollTo({ top: 0, behavior: 'instant' });
    });
    // Document scrolling cannot reveal flags clipped by the nested country
    // picker. Scroll every rendered flag into view through its real container
    // and require the intended image to decode, rather than exempting flags
    // or treating their deliberately empty offscreen placeholders as broken.
    for (const flag of await page.locator('img[data-nations-flag-src]:visible').all()) {
      const source = await flag.getAttribute('data-nations-flag-src');
      await flag.scrollIntoViewIfNeeded();
      await expect(flag).toHaveAttribute('src', source);
      await expect.poll(() => flag.evaluate(image => image.complete && image.naturalWidth > 0 && image.naturalHeight > 0), { message: `The revealed country flag decodes: ${source}` }).toBe(true);
    }
    await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
    await expect.poll(() => page.locator('img').evaluateAll(images => images.filter(im => im.getClientRects().length && (!im.complete || !im.naturalWidth)).map(im => im.getAttribute('src'))), { timeout: 10000 }).toEqual([]);
    expect(errors).toEqual([]);
    if (entry.indexable) {
      const alternate = await page.locator(`head link[hreflang="${entry.file.startsWith('it/') ? 'en' : 'it'}"]`).getAttribute('href');
      const href = new URL(alternate).pathname;
      const matching = await page.locator('nav a').evaluateAll((links, wanted) => links.some(a => new URL(a.href).pathname === wanted), href);
      expect(matching, 'Navigation offers the translated counterpart').toBe(true);
    }
  });
}

for (const path of ['/', '/it/', '/tickets', '/it/tickets']) {
  for (const outcome of ['success', 'failure']) test(`${path}: reminder ${outcome} with a stubbed response`, async ({ page }, testInfo) => {
    const requests = [];
    await page.route('https://script.google.com/**', route => {
      requests.push(route.request().url());
      return route.fulfill({ status: outcome === 'success' ? 200 : 503, contentType: 'text/plain', body: outcome });
    });
    await page.goto(path);
    const form = page.locator('#reminder-form');
    await expect(form).toHaveCount(1);
    await page.evaluate(() => {
      window.reminderSourcesForTest = [];
      window.mscAnalytics = { trackReminder: source => window.reminderSourcesForTest.push(source) };
    });
    await page.evaluate(() => document.fonts.ready);
    // Let the long page jump paint before interacting with the form.
    await form.evaluate(async el => {
      el.scrollIntoView({ block: 'center', behavior: 'instant' });
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    await form.locator('input[type="email"]').fill('audit@example.invalid');
    const submit = form.locator('button[type="submit"]');
    // Exercise the input type configured for each device profile.
    if (testInfo.project.use.hasTouch) await submit.tap();
    else await submit.click();
    if (outcome === 'success') {
      await expect(page.locator('#reminder-container')).toContainText(path.startsWith('/it') ? 'Grazie' : 'Thank you');
      if (!path.includes('tickets')) await expect(page.locator('#reminder-container')).toContainText(path.startsWith('/it') ? 'La tua richiesta di promemoria è stata salvata.' : 'Your reminder request is saved.');
    }
    else {
      await expect(page.getByRole('alert')).toBeVisible();
      await expect(form.locator('button[type="submit"]')).toBeEnabled();
      await expect(form.locator('input[type="email"]')).toHaveValue('audit@example.invalid');
    }
    expect(requests.length).toBe(1);
    const analyticsSource = `${path.includes('tickets') ? 'Tickets' : 'Home'} - ${path.startsWith('/it') ? 'IT' : 'EN'}`;
    const submitted = new URL(requests[0]);
    expect(submitted.searchParams.get('email')).toBe('audit@example.invalid');
    expect(submitted.searchParams.get('source')).toBe(path.includes('tickets') ? analyticsSource : `${analyticsSource} | 2027 early bird`);
    expect(await page.evaluate(() => window.reminderSourcesForTest)).toEqual(outcome === 'success' ? [analyticsSource] : []);
    if (!path.includes('tickets')) {
      const feedback = outcome === 'success' ? page.locator('#reminder-container') : page.getByRole('alert');
      expect(await feedback.evaluate(el => {
        const bounds = el.getBoundingClientRect();
        return bounds.width > 0 && bounds.left >= 0 && bounds.right <= document.documentElement.clientWidth + 1 && el.scrollWidth <= el.clientWidth + 1;
      }), 'The homepage confirmation or retry message remains readable without horizontal overflow').toBe(true);
    }
  });
}

test('Missing URLs return a usable, noindex 404', async ({ page }) => {
  const response = await page.goto('/missing-page-for-quality-check');
  expect(response.status()).toBe(404);
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
});

for (const path of ['/', '/it/']) test(`${path}: reduced motion retains the poster without video autoplay`, async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(path);
  await expect(page.locator('h1')).toBeVisible();
  await page.locator('#heroVideo').scrollIntoViewIfNeeded();
  await expect(page.locator('.premiere-poster-image')).toBeVisible();
  await expect(page.locator('#heroVideo')).toHaveAttribute('data-poster', /wordmark-hero-poster-v07\.webp$/);
  expect(await page.locator('#heroVideo, #heroAmbientVideo').evaluateAll(videos => videos.map(video => ({ source: video.getAttribute('src'), paused: video.paused })))).toEqual([{ source: null, paused: true }, { source: null, paused: true }]);
});

for (const path of ['/', '/it/', '/news/bachata-workshop-levels-guide-congress', '/it/news/livelli-workshop-bachata-congresso', '/news/bachata-congress-alone-solo-dancer-guide', '/it/news/congresso-bachata-da-soli-guida-ballerini', '/news/bachata-festivals-milan-2026-2027', '/it/news/festival-bachata-milano-2026-2027']) {
  test(`${path}: content with JavaScript disabled`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    const page = await context.newPage();
    await page.goto(baseURL + path);
    await expect(page.locator('h1')).toBeVisible();
    const display = await page.locator('h1').evaluate(el => getComputedStyle(el).opacity);
    expect(Number(display)).toBe(1);
    await context.close();
  });
}
