import { test, expect } from '@playwright/test';

const destination = 'https://wa.me/41799668481';
const instagram = 'https://www.instagram.com/milanosensualcongress/';

// All external services are isolated, including the WhatsApp navigation.
// This suite verifies only the prepared draft and never transmits a message.
test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function interceptHandoff(page) {
  const requests = [];
  await page.route('https://wa.me/**', route => {
    requests.push(new URL(route.request().url()));
    return route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>Test draft</title><h1>WhatsApp draft intercepted locally</h1>' });
  });
  return requests;
}

for (const path of ['/contact', '/it/contact']) {
  const italian = path.startsWith('/it/');
  test(`${path}: contact composer encodes a draft and supports the promoters topic`, async ({ page }) => {
    const requests = await interceptHandoff(page);
    await page.goto(path + '?topic=promoters');
    await expect(page.locator('#contact-topic')).toHaveValue('promoters');
    await expect(page.locator('#contact-handoff-note')).toContainText(italian ? 'Non sarà inviato' : 'Nothing is sent');
    await page.locator('#contact-name').fill('Test Dancer & Partner');
    const message = 'Can our school join?\nWe dance bachata & salsa — 2027.';
    await page.locator('#contact-message').fill(message);
    await Promise.all([
      page.waitForURL(url => url.origin + url.pathname === destination),
      page.locator('#contact-whatsapp-form button[type="submit"]').click(),
    ]);
    expect(requests).toHaveLength(1);
    expect([...requests[0].searchParams.keys()]).toEqual(['text']);
    expect(requests[0].searchParams.get('text').replace(/\r\n/g, '\n')).toBe(italian
      ? `Ciao Milano Sensual Congress!\nMi chiamo Test Dancer & Partner.\nArgomento: Promoter e collaborazioni\n\n${message}`
      : `Hello Milano Sensual Congress!\nMy name is Test Dancer & Partner.\nTopic: Promoters & collaborations\n\n${message}`);
    await expect(page.locator('h1')).toHaveText('WhatsApp draft intercepted locally');
  });

  test(`${path}: contact composer rejects blank input and allows correction`, async ({ page }) => {
    const requests = await interceptHandoff(page);
    await page.goto(path);
    const message = page.locator('#contact-message');
    await message.fill('   \n   ');
    await page.locator('#contact-whatsapp-form button[type="submit"]').click();
    expect(requests).toHaveLength(0);
    await expect(page).toHaveURL(new RegExp(path + '$'));
    expect(await message.evaluate(element => element.validity.customError)).toBe(true);
    expect(await message.evaluate(element => element.validationMessage)).toBe(italian
      ? 'Scrivi un messaggio prima di continuare.'
      : 'Please write a message before continuing.');
    await message.fill('Please tell me about the congress.');
    expect(await message.evaluate(element => element.validity.valid)).toBe(true);
    await Promise.all([
      page.waitForURL(url => url.origin + url.pathname === destination),
      page.locator('#contact-whatsapp-form button[type="submit"]').click(),
    ]);
    expect(requests).toHaveLength(1);
    expect(requests[0].searchParams.get('text')).toContain('Please tell me about the congress.');
  });

  test(`${path}: direct channels and the native composer work without JavaScript`, async ({ browser, baseURL }, info) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: info.project.use.viewport });
    try {
      await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
      const page = await context.newPage();
      const requests = await interceptHandoff(page);
      await page.goto(baseURL + path);
      await expect(page.locator('.visit-quick-help a[href="' + destination + '"]')).toBeVisible();
      await expect(page.locator('.visit-quick-help a[href="' + instagram + '"]')).toBeVisible();
      await expect(page.locator('.visit-quick-help a[href="mailto:info@oltreilviaggio.net"]')).toBeVisible();
      await expect(page.locator('#contact-whatsapp-form')).toHaveAttribute('action', destination);
      await expect(page.locator('#contact-message')).toHaveAttribute('name', 'text');
      const message = 'Test Dancer: a question about travel & hotels.';
      await page.locator('#contact-message').fill(message);
      // Finish the native smooth scroll from focus before positioning the submit control.
      await page.locator('#contact-whatsapp-form button[type="submit"]').evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
      await Promise.all([
        page.waitForURL(url => url.origin + url.pathname === destination),
        page.locator('#contact-whatsapp-form button[type="submit"]').click(),
      ]);
      expect(requests).toHaveLength(1);
      expect(requests[0].searchParams.get('text')).toBe(message);
    } finally {
      await context.close();
    }
  });
}
