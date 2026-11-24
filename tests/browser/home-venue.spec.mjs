import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const copy of [
  { path: '/', title: /Two hotels\.\s*One congress\./, previousTitle: /Stay close\.\s*Feel at home\./, dates: /19–21\s+November\s+2027/, transfer: '/shuttle', transferLabel: 'MXP–Devero bus timetable', bookingLabel: 'Book via WhatsApp', roomCaption: '4-star Superior comfort', departureLabel: 'Departure time to be confirmed', mainTime: '5pm', secondaryTime: '4pm' },
  { path: '/it/', title: /Due hotel\.\s*Un congresso\./, previousTitle: /Resta vicino\.\s*Sentiti a casa\./, dates: /19–21\s+novembre\s+2027/, transfer: '/it/navetta', transferLabel: 'Orari della navetta MXP–Devero', bookingLabel: 'Prenota su WhatsApp', roomCaption: 'Comfort 4 stelle Superior', departureLabel: 'Orario di partenza da confermare', mainTime: '17:00', secondaryTime: '16:00' },
]) {
  test(`${copy.path}: homepage venue preserves confirmed facts, readable photos and travel links`, async ({ page }, info) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.goto(copy.path);
    await page.evaluate(() => document.fonts.ready);
    const section = page.locator('#your-stay');
    await section.scrollIntoViewIfNeeded();
    await expect(section).toHaveClass(/\bhome-venue\b/);
    await expect(section).toHaveAttribute('aria-labelledby', 'stay-title');
    const title = section.locator('.venue-meta > h2#stay-title');
    await expect(title).toHaveText(copy.title);
    await expect(title).toBeVisible();
    const minimumTitleSize = page.viewportSize().width >= 1024 ? 40 : 30;
    expect(await title.evaluate(element => parseFloat(getComputedStyle(element).fontSize)), 'The venue heading reads as a large section title').toBeGreaterThanOrEqual(minimumTitleSize);
    await expect(section.locator('h2')).toHaveCount(1);
    await expect(section).not.toContainText(copy.previousTitle);
    await expect(section.locator('.venue-copy, .venue-rating, .venue-stars, .venue-journey, .venue-journey-stamp')).toHaveCount(0);
    await expect(section.locator('.venue-date')).toHaveCount(0);
    await expect(section).not.toContainText(copy.dates);

    const arrangement = await section.locator('.venue-layout').evaluate(element => {
      const gallery = element.querySelector('.venue-gallery');
      const transfer = element.querySelector('.venue-transfer');
      const photoBounds = gallery.getBoundingClientRect();
      const transferBounds = transfer.getBoundingClientRect();
      return {
        galleryFirst: Boolean(gallery.compareDocumentPosition(transfer) & Node.DOCUMENT_POSITION_FOLLOWING),
        galleryRight: photoBounds.right,
        galleryBottom: photoBounds.bottom,
        transferLeft: transferBounds.left,
        transferTop: transferBounds.top,
      };
    });
    expect(arrangement.galleryFirst, 'The photos precede the bus information in reading order').toBe(true);
    if (page.viewportSize().width > 1000) {
      expect(arrangement.galleryRight, 'Desktop photos sit to the left of the bus information').toBeLessThanOrEqual(arrangement.transferLeft);
    } else {
      expect(arrangement.galleryBottom, 'Phone and tablet photos stack above the bus information').toBeLessThanOrEqual(arrangement.transferTop);
    }
    await expect(section.locator('.venue-room figcaption')).toHaveText(copy.roomCaption);

    const photos = section.locator('#hotel-devero img');
    await expect(photos).toHaveCount(2);
    const sources = [];
    const photoMetrics = [];
    for (const photo of await photos.all()) {
      await photo.scrollIntoViewIfNeeded();
      await expect(photo).toBeVisible();
      await expect(photo).toHaveAttribute('alt', /\S+/);
      await expect.poll(() => photo.evaluate(image => image.complete && image.naturalWidth > 1), { message: 'The venue photograph decodes when viewed' }).toBe(true);
      sources.push(await photo.evaluate(image => new URL(image.currentSrc).pathname));
      const bounds = await photo.evaluate(image => {
        const rect = image.getBoundingClientRect();
        return { source: new URL(image.currentSrc).pathname, width: rect.width, left: rect.left, right: rect.right, naturalWidth: image.naturalWidth };
      });
      expect(bounds.left, 'Venue photos and the room overlay stay within the left edge').toBeGreaterThanOrEqual(-1);
      expect(bounds.right, 'Venue photos and the room overlay stay within the right edge').toBeLessThanOrEqual(page.viewportSize().width + 1);
      photoMetrics.push(bounds);
    }
    expect(sources).toEqual(expect.arrayContaining([
      expect.stringMatching(/\/devero-hotel-pool-night(?:_\d+w)?\.webp$/),
      expect.stringMatching(/\/devero-hotel-room-interior(?:_\d+w)?\.webp$/),
    ]));

    const transfer = section.locator('.venue-transfer');
    await expect(transfer).toHaveAttribute('aria-labelledby', 'venue-transfer-label');
    await expect(transfer.locator('.venue-transfer-bus')).toBeVisible();
    await expect(transfer.locator('.venue-transfer-bus')).toHaveAttribute('aria-hidden', 'true');
    await expect(transfer.locator('.venue-transfer-point').first().locator('small')).toHaveText('Malpensa');
    await expect(transfer.locator('.venue-transfer-point').first().locator('strong')).toHaveText('MXP');
    const service = transfer.locator('.venue-transfer-departures:visible');
    for (const [choice, hotel, time, display] of [
      ['main', 'Devero Hotel', '17:00', copy.mainTime],
      ['secondary', 'AS Hotel Cambiago', '16:00', copy.secondaryTime],
    ]) {
      await section.locator(`label[for="hotel-${choice}"]`).click();
      await expect(service).toHaveCount(1);
      await expect(service.getByRole('heading')).toContainText(hotel);
      await expect(service.locator('p')).toHaveText(copy.departureLabel);
      await expect(service.locator('time')).toHaveText(display);
      await expect(service.locator('time')).toHaveAttribute('datetime', time);
    }
    await expect(transfer).not.toContainText(/BGY|LIN/);
    await expect(section.getByRole('link', { name: copy.bookingLabel, exact: true })).toHaveCount(0);
    await expect(section.locator('a[href*="wa.me"]')).toHaveCount(0);
    const link = transfer.getByRole('link', { name: copy.transferLabel, exact: true });
    await expect(link).toHaveAttribute('href', copy.transfer);
    await expect(link).toHaveClass(/\be27-text-link\b/);
    await expect(link).not.toHaveClass(/\bpremiere-ticket\b/);
    await link.evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await expect(link).toBeVisible();
    expect((await link.boundingBox()).height + .01, 'The transfer link retains a usable touch target').toBeGreaterThanOrEqual(44);
    expect(await link.evaluate(element => {
      const bounds = element.getBoundingClientRect();
      return element.contains(document.elementFromPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2));
    }), 'The localized transfer link remains directly clickable').toBe(true);
    await link.focus();
    await expect(link, 'Transfer details remain keyboard accessible').toBeFocused();

    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'The redesigned venue does not introduce horizontal page overflow').toBe(true);
    const overflowing = await section.locator('h2, h3, h4, p, small, figcaption, a, time, .venue-transfer-bus').evaluateAll(elements => elements.filter(element => {
      const bounds = element.getBoundingClientRect();
      return bounds.width > 0 && bounds.height > 0 && (bounds.left < -1 || bounds.right > document.documentElement.clientWidth + 1 || element.scrollWidth > element.clientWidth + 1);
    }).map(element => element.textContent.trim()));
    expect(overflowing, 'The venue title, facts and links remain readable inside the viewport').toEqual([]);
    expect(errors).toEqual([]);
    await info.attach('venue-image-metrics', {
      body: JSON.stringify({ path: copy.path, viewport: page.viewportSize(), arrangement, photos: photoMetrics }, null, 2),
      contentType: 'application/json',
    });
  });
}

for (const path of ['/', '/it/']) {
  test(`${path}: hotel choices support keyboard, direct links and no JavaScript`, async ({ page, browser }) => {
    await page.goto(path);
    const main = page.locator('#hotel-devero');
    const secondary = page.locator('#hotel-cambiago');
    await expect(main).toBeVisible();
    await expect(secondary).toBeHidden();
    await page.locator('label[for="hotel-secondary"]').click();
    await expect(secondary).toBeVisible();
    await expect(main).toBeHidden();
    await expect(page).toHaveURL(/#stay-cambiago$/);
    await secondary.locator('img').scrollIntoViewIfNeeded();
    expect(await secondary.locator('img').evaluate(async img => { await img.decode(); return img.naturalWidth > 0; })).toBe(true);
    await page.locator('#hotel-secondary').focus();
    await page.keyboard.press('ArrowLeft');
    await expect(main).toBeVisible();
    await expect(secondary).toBeHidden();
    await page.goto(path + '#stay-cambiago');
    await expect(secondary).toBeVisible();
    await expect(page.locator('.venue-transfer-departures:visible time')).toHaveAttribute('datetime', '16:00');
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: page.viewportSize() });
    const staticPage = await context.newPage();
    await staticPage.goto(new URL(path, page.url()).href);
    await staticPage.locator('label[for="hotel-secondary"]').click();
    await expect(staticPage.locator('#hotel-cambiago')).toBeVisible();
    await expect(staticPage.locator('#hotel-devero')).toBeHidden();
    await expect(staticPage.locator('.venue-transfer-departures:visible time')).toHaveAttribute('datetime', '16:00');
    await context.close();
  });
  test(`${path}: Jack and Jill introduces two divisions before the FAQ`, async ({ page }) => {
    await page.goto(path);
    const section = page.locator('#home-jnj');
    await expect(section.locator('h3')).toHaveText(['Amateur', 'Semi-pro']);
    expect(await section.evaluate(el => el.nextElementSibling.id)).toBe('home-questions');
    await expect(section.getByRole('link')).toHaveAttribute('href', `${path === '/it/' ? '/it' : ''}/jacknjill`);
    const date = page.locator('.premiere-date-line');
    expect(await date.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
    if (page.viewportSize().width >= 1000) {
      const signup = await page.locator('#early-bird').boundingBox();
      const artists = await page.locator('#artist-showcase').boundingBox();
      expect(signup.x + signup.width).toBeLessThan(artists.x);
    }
  });
}
