import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const copy of [
  { path: '/', title: 'Devero Hotel – 4 Star Superior Venue', previousTitle: /Stay close\.\s*Feel at home\./, dates: /19–21\s+November\s+2027/, transfer: '/transfer', transferLabel: 'Transfer details', bookingLabel: 'Book via WhatsApp', roomCaption: '4-star Superior comfort', departures: 'Departures', times: ['3pm', '6pm', '8pm'] },
  { path: '/it/', title: 'Devero Hotel – Location 4 Stelle Superior', previousTitle: /Resta vicino\.\s*Sentiti a casa\./, dates: /19–21\s+novembre\s+2027/, transfer: '/it/transfer', transferLabel: 'Informazioni sui transfer', bookingLabel: 'Prenota su WhatsApp', roomCaption: 'Comfort 4 stelle Superior', departures: 'Partenze', times: ['15:00', '18:00', '20:00'] },
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

    const photos = section.locator('img');
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
    await expect(transfer.locator('#venue-transfer-title .venue-transfer-destinations strong')).toHaveText(['Devero Hotel', 'AS Hotel Cambiago']);
    const booking = transfer.locator('.venue-transfer-booking');
    await expect(booking.getByRole('heading')).toContainText('BGY / LIN');
    await expect(booking).toContainText('Bergamo Orio al Serio');
    await expect(booking).toContainText('Linate');
    await expect(booking.getByRole('heading').locator('.venue-transfer-destinations strong')).toHaveText(['Devero Hotel', 'AS Hotel Cambiago']);
    await expect(booking.locator('time'), 'MXP departure times do not apply to BGY or LIN').toHaveCount(0);
    const whatsapp = booking.getByRole('link', { name: copy.bookingLabel, exact: true });
    await expect(whatsapp).toHaveAttribute('href', 'https://wa.me/393662073769');
    await whatsapp.evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await expect(whatsapp).toBeVisible();
    expect((await whatsapp.boundingBox()).height + .01, 'WhatsApp booking retains a usable touch target').toBeGreaterThanOrEqual(44);
    await whatsapp.focus();
    await expect(whatsapp).toBeFocused();
    await expect(transfer.locator('.venue-transfer-departures > p')).toHaveText(copy.departures);
    const departures = transfer.locator('.venue-transfer-departures time');
    await expect(departures).toHaveText(copy.times);
    expect(await departures.evaluateAll(times => times.map(time => time.getAttribute('datetime')))).toEqual(['15:00', '18:00', '20:00']);
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
