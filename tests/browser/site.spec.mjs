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
    const carousel = page.locator('#carousel');
    if (await carousel.count()) {
      const controls = page.locator('button[onclick*="scrollBy"]');
      await carousel.scrollIntoViewIfNeeded();
      await controls.last().click();
      await expect.poll(() => carousel.evaluate(el => el.scrollLeft / el.clientWidth)).toBeGreaterThan(.95);
      await controls.first().click();
      await expect.poll(() => carousel.evaluate(el => el.scrollLeft)).toBe(0);
      // Visit every horizontally lazy-loaded slide as a visitor can.
      const slides = await carousel.locator(':scope > div').count();
      for (let index = 1; index < slides; index++) {
        await controls.last().click();
        await expect.poll(() => carousel.evaluate(el => el.scrollLeft / el.clientWidth)).toBeGreaterThan(index - .05);
      }
      await expect.poll(() => carousel.locator('img').evaluateAll(images => images.every(im => im.complete && im.naturalWidth > 0))).toBe(true);
      await carousel.evaluate(el => el.scrollTo({ left: 0, behavior: 'instant' }));
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
  for (const outcome of ['success', 'failure']) test(`${path}: reminder ${outcome} with a stubbed response`, async ({ page }) => {
    const requests = [];
    await page.route('https://script.google.com/**', route => {
      requests.push(route.request().url());
      return route.fulfill({ status: outcome === 'success' ? 200 : 503, contentType: 'text/plain', body: outcome });
    });
    await page.goto(path);
    const form = page.locator('#reminder-form');
    await page.evaluate(() => document.fonts.ready);
    // Finish positioning before focus/click can start competing smooth scrolls.
    await form.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await form.locator('input[type="email"]').fill('audit@example.invalid');
    await form.locator('button[type="submit"]').click();
    if (outcome === 'success') await expect(page.locator('#reminder-container')).toContainText(path.startsWith('/it') ? 'Grazie' : 'Thank you');
    else {
      await expect(page.getByRole('alert')).toBeVisible();
      await expect(form.locator('button[type="submit"]')).toBeEnabled();
      await expect(form.locator('input[type="email"]')).toHaveValue('audit@example.invalid');
    }
    expect(requests.length).toBe(1);
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
  expect(await page.locator('#heroVideo').getAttribute('src')).toBeNull();
  expect(await page.locator('#heroVideo').evaluate(video => video.paused)).toBe(true);
});

for (const path of ['/', '/it/', '/news/bachata-workshop-levels-guide-congress', '/it/news/livelli-workshop-bachata-congresso', '/news/bachata-congress-alone-solo-dancer-guide', '/it/news/congresso-bachata-da-soli-guida-ballerini']) {
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
