import { test, expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

const destination = 'https://wa.me/41799668481';
test.beforeEach(async ({ context }) => {
  // No test details leave the browser, including the prepared WhatsApp draft.
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

for (const path of ['/promoters', '/it/promoters']) {
  const italian = path.startsWith('/it/');
  test(`${path}: ambassador application prepares a complete draft without sending it`, async ({ page }, testInfo) => {
    const drafts = [];
    await page.route('https://wa.me/**', route => {
      drafts.push(new URL(route.request().url()));
      return route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Local intercepted draft</title>' });
    });
    await page.goto(path);
    await expect(page.locator('.promoters-kicker, .promoters-start')).toHaveCount(0);
    await expect(page.locator('.promoters-hero-logo')).toBeVisible();
    await expect(page.locator('.promoters-join')).toHaveAttribute('href', '#ambassador-application');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    const layout = await page.evaluate(() => {
      const rect = selector => {
        const { x, y, width, height } = document.querySelector(selector).getBoundingClientRect();
        return { x, y, width, height };
      };
      return { viewport: window.innerWidth, scrollWidth: document.documentElement.scrollWidth,
        hero: rect('.promoters-hero'), logo: rect('.promoters-hero-logo'), form: rect('.promoters-application') };
    });
    await testInfo.attach('layout', { body: JSON.stringify(layout), contentType: 'application/json' });
    await writeFile(testInfo.outputPath('layout.json'), JSON.stringify(layout, null, 2));
    await page.screenshot({ path: testInfo.outputPath('application-page.png'), fullPage: true, animations: 'disabled' });
    await page.locator('#promoter-name').fill('Alex & Test');
    await page.locator('#promoter-email').fill('alex@example.test');
    await page.locator('#promoter-phone').fill('+41 00 000 00 00');
    await page.locator('#promoter-country').fill('Switzerland');
    await page.locator('#promoter-city').fill('Zürich');
    await page.locator('#promoter-social').fill('@test_dancers');
    await page.locator('#promoter-role').selectOption('teacher');
    await page.locator('#promoter-community').fill('Test Dance School');
    await page.locator('#promoter-message').fill('Teaching Bachata.\nBringing a group & sharing the event.');
    await expect(page.locator('#application-handoff')).toContainText(italian ? 'Non sarà inviata' : 'Nothing is sent');
    await Promise.all([
      page.waitForURL(url => url.origin + url.pathname === destination),
      page.locator('.promoters-application-submit').click(),
    ]);
    expect(drafts).toHaveLength(1);
    expect([...drafts[0].searchParams.keys()]).toEqual(['text']);
    const text = drafts[0].searchParams.get('text');
    for (const value of ['Alex & Test', 'alex@example.test', '+41 00 000 00 00', 'Switzerland', 'Zürich', '@test_dancers', 'Test Dance School', 'Bringing a group & sharing the event.']) expect(text).toContain(value);
    expect(text).toContain(italian ? 'Il tuo ruolo: Insegnante' : 'Your role: Teacher');
  });

  test(`${path}: ambassador validation preserves unfinished applications`, async ({ page }) => {
    const handoffs = [];
    await page.route('https://wa.me/**', route => { handoffs.push(route.request().url()); return route.fulfill({ status: 200, body: '' }); });
    await page.goto(path);
    await page.locator('#promoter-name').fill('   ');
    await page.locator('#promoter-email').fill('alex@example.test');
    await page.locator('#promoter-country').fill('Switzerland');
    await page.locator('#promoter-city').fill('Zürich');
    await page.locator('#promoter-message').fill('I would like to collaborate.');
    await page.locator('.promoters-application-submit').click();
    expect(handoffs).toHaveLength(0);
    expect(await page.locator('#promoter-name').evaluate(input => input.validity.customError)).toBe(true);
    await page.locator('#promoter-name').fill('Alex');
    expect(await page.locator('#promoter-name').evaluate(input => input.validity.valid)).toBe(true);
    await expect(page.locator('#promoter-message')).toHaveValue('I would like to collaborate.');
    await page.locator('#promoter-email').fill('invalid');
    await page.locator('.promoters-application-submit').click();
    expect(handoffs).toHaveLength(0);
    expect(await page.locator('#promoter-email').evaluate(input => input.validity.typeMismatch)).toBe(true);
  });
}
