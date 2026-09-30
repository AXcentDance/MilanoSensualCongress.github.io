import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const edition = JSON.parse(readFileSync(new URL('../../data/editions/2027.json', import.meta.url), 'utf8'));

// Functional checks never contact form, analytics or embedded-video services.
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

function renderedLineCount(element) {
  const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  const lineCenters = [];
  let node;
  while ((node = walker.nextNode())) {
    if (!node.textContent.trim()) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    for (const rect of range.getClientRects()) {
      const center = rect.top + rect.height / 2;
      if (!lineCenters.some(existing => Math.abs(existing - center) < lineHeight / 2)) lineCenters.push(center);
    }
  }
  return lineCenters.length;
}

for (const copy of [
  { path: '/', title: 'Don’t miss the early bird price.', description: 'Get a reminder before the price goes up.', label: 'Your email address', button: 'Remind me', source: 'Home - EN' },
  { path: '/it/', title: 'Non perdere il prezzo early bird.', description: 'Ricevi un promemoria prima che il prezzo salga.', label: 'Il tuo indirizzo email', button: 'Ricordamelo', source: 'Home - IT' }
]) {
  test(`${copy.path}: early-bird email signup is readable in the homepage hero`, async ({ page, browserName }) => {
    // Keep the published timer in its active state regardless of when this
    // regression runs; its target must agree with the confirmed edition record.
    const now = Date.parse('2026-12-29T20:58:55Z');
    await page.clock.setFixedTime(now);
    await page.goto(copy.path);
    await page.evaluate(() => document.fonts.ready);
    const panel = page.locator('.premiere-hero #early-bird');
    const form = page.locator('#reminder-form');
    await expect(panel).toHaveCount(1);
    await expect(form).toHaveCount(1);
    await expect(panel.locator('#reminder-form')).toHaveCount(1);
    const heading = panel.getByRole('heading', { name: copy.title, exact: true });
    await expect(heading).toBeVisible();
    const italic = heading.locator('em');
    await expect(italic).toHaveCSS('font-style', 'italic');
    expect(await italic.evaluate(renderedLineCount), 'The italic offer phrase remains intact on every screen size').toBe(1);
    if (page.viewportSize().width >= 700) {
      expect(await heading.evaluate(renderedLineCount), 'The complete offer headline fits on one line on tablet and desktop').toBe(1);
    }
    await expect(panel.locator('#early-bird-description')).toHaveText(copy.description);
    const timer = panel.locator('[data-early-bird-countdown]');
    await expect(timer).toHaveAttribute('data-deadline', edition.earlyBird.countdownDeadline);
    const status = panel.locator('[data-countdown-status]');
    await expect(status.locator('time')).toHaveAttribute('datetime', edition.earlyBird.endsOn);
    await expect(status).toHaveAttribute('aria-live', 'polite');
    await expect(status).toHaveClass(/\bsr-only\b/);
    const statusBounds = await status.boundingBox();
    expect(statusBounds.width, 'The date remains available to assistive technology without a visible deadline row').toBeLessThanOrEqual(1);
    expect(statusBounds.height).toBeLessThanOrEqual(1);
    await expect(timer.locator('[data-countdown-unit]')).toHaveCount(4);
    await expect.poll(async () => (await timer.locator('[data-countdown-unit]').allTextContents()).every(value => /^\d{2,}$/.test(value))).toBe(true);
    const displayedSeconds = await timer.locator('[data-countdown-unit]').evaluateAll(units => units.reduce((total, unit, index) => total + Number(unit.textContent) * [86400, 3600, 60, 1][index], 0));
    expect(displayedSeconds, 'The live browser countdown uses the confirmed Italian cutoff').toBe((Date.parse(edition.earlyBird.countdownDeadline) - now) / 1000);
    await expect(form).toHaveAttribute('data-analytics-source', copy.source);
    await expect(form.locator('input[name="source"]')).toHaveValue(`${copy.source} | 2027 early bird`);

    const email = panel.getByRole('textbox', { name: copy.label, exact: true });
    const button = panel.getByRole('button', { name: new RegExp(`^${copy.button}`) });
    await expect(email).toHaveAttribute('type', 'email');
    await expect(email).toHaveAttribute('required', '');
    await expect(email).toHaveAttribute('autocomplete', 'email');
    await expect(email).toHaveAttribute('aria-describedby', 'early-bird-description');
    await panel.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await expect(email).toBeInViewport();
    await expect(button).toBeInViewport();
    for (const control of [email, button]) {
      const bounds = await control.boundingBox();
      expect(bounds.height).toBeGreaterThanOrEqual(44);
      expect(bounds.width).toBeGreaterThanOrEqual(44);
      expect(bounds.x).toBeGreaterThanOrEqual(0);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(page.viewportSize().width);
    }
    await email.focus();
    await expect(email).toBeFocused();
    // Match the existing navigation tests: macOS WebKit uses Option-Tab
    // to include buttons and links with its default keyboard preferences.
    await page.keyboard.press(browserName === 'webkit' && process.platform === 'darwin' ? 'Alt+Tab' : 'Tab');
    await expect(button).toBeFocused();
    expect(await panel.evaluate(el => {
      const dates = document.getElementById('edition-facts');
      const artists = document.getElementById('artist-showcase');
      const follows = Node.DOCUMENT_POSITION_FOLLOWING;
      return !!(dates.compareDocumentPosition(el) & follows) && !!(el.compareDocumentPosition(artists) & follows);
    }), 'Signup follows the event details and precedes the artists').toBe(true);
    expect(await panel.evaluate(el => {
      for (let parent = el; parent; parent = parent.parentElement) {
        const css = getComputedStyle(parent);
        if (css.visibility !== 'visible' || Number(css.opacity) < 1) return false;
      }
      // Decorative glow pseudo-elements may intentionally exceed the section;
      // measure readable content and page overflow instead of that glow box.
      const width = document.documentElement.clientWidth;
      return document.documentElement.scrollWidth <= width + 1 &&
        [...el.querySelectorAll('h2, h2 em, p:not(.sr-only), [role="timer"], input:not([type="hidden"]), button')].every(content => {
          const bounds = content.getBoundingClientRect();
          return bounds.left >= 0 && bounds.right <= width + 1 && content.scrollWidth <= content.clientWidth + 1;
        });
    }), 'Signup remains opaque and its readable contents fit the viewport').toBe(true);
  });
}
