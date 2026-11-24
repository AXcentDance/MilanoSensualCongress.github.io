import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function openHome(page, path) {
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
}

async function center(control) {
  await control.evaluate(async element => {
    element.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
}

for (const path of ['/', '/it/']) {
  test(`${path}: Mint block buttons respond without moving the link target`, async ({ page }, info) => {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await openHome(page, path);
    await expect(page.locator('body')).toHaveClass(/\be27-motion-on\b/);
    const links = page.locator('a.premiere-ticket');
    await expect(links).toHaveCount(3);
    for (const link of await links.all()) {
      await page.mouse.move(0, 0);
      await center(link);
      const before = await link.boundingBox();
      expect(before.height).toBeGreaterThanOrEqual(44);
      expect(before.x).toBeGreaterThanOrEqual(0);
      expect(before.x + before.width).toBeLessThanOrEqual(page.viewportSize().width + 1);
      await expect(link).toHaveAttribute('href', 'https://lasalsadelbaile.com/MSC2027');
      const surface = link.locator('.premiere-entry-surface');
      if (!info.project.use.hasTouch) {
        await link.hover({ position: { x: before.width * .8, y: before.height * .2 } });
        await expect(surface).toHaveCSS('background-color', 'rgb(221, 255, 240)');
        await expect(surface).not.toHaveCSS('transform', 'none');
        const after = await link.boundingBox();
        for (const dimension of ['x', 'y', 'width', 'height']) expect(Math.abs(after[dimension] - before[dimension]), `The clickable ${dimension} remains stable`).toBeLessThan(1);
        await page.mouse.down();
        await expect.poll(() => surface.evaluate(el => new DOMMatrix(getComputedStyle(el).transform).m42)).toBeGreaterThan(.5);
        // Release outside the link; navigation is checked separately with the keyboard.
        await page.mouse.move(0, 0);
        await page.mouse.up();
        await expect(surface).toHaveCSS('transform', 'none');
      }
      expect(await link.evaluate(el => [...el.querySelectorAll('.premiere-entry-copy, .premiere-entry-label')].every(child => child.scrollWidth <= child.clientWidth + 1)), 'Ticket text fits its surface').toBe(true);
    }
    const last = links.last();
    if (info.project.use.hasTouch) await last.tap();
    else {
      await page.keyboard.press('Tab');
      await last.focus();
      expect(await last.evaluate(el => el.matches(':focus-visible') && parseFloat(getComputedStyle(el).outlineWidth) >= 2)).toBe(true);
      await last.press('Enter');
    }
    await expect(page).toHaveURL('https://lasalsadelbaile.com/MSC2027');
  });

  test(`${path}: reminder bell rings on hover and click while the request is pending`, async ({ page }, info) => {
    let request;
    await page.route('https://script.google.com/**', route => { request = route; });
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await openHome(page, path);
    await expect(page.locator('body')).toHaveClass(/\be27-motion-on\b/);
    await page.locator('#early-bird-email').fill('audit@example.invalid');
    const button = page.locator('.premiere-submit');
    await center(button);
    const icon = await button.locator('.premiere-submit-icon').elementHandle();
    const ringing = () => icon.evaluate(el => el.getAnimations().map(animation => ({
      duration: animation.effect.getTiming().duration,
      rotation: Math.max(...animation.effect.getKeyframes().map(frame => Math.abs(parseFloat(frame.transform.match(/-?[\d.]+/)[0]))))
    })));
    if (!info.project.use.hasTouch) {
      await button.hover();
      expect((await ringing())[0]?.rotation, 'Hover swings the bell').toBeGreaterThan(15);
    }
    if (info.project.use.hasTouch) await button.tap();
    else await button.click();
    await expect(button).toBeDisabled();
    expect(await icon.evaluate(el => el.isConnected), 'Saving keeps the animated bell in the document').toBe(true);
    const clickAnimation = (await ringing())[0];
    expect(clickAnimation?.rotation, 'Click restarts a stronger ring').toBeGreaterThan(24);
    await expect(button.locator('.premiere-submit-label')).toHaveText(path === '/it/' ? 'Invio in corso...' : 'Processing...');
    await expect.poll(() => Boolean(request)).toBe(true);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await expect.poll(async () => (await ringing()).length, { message: 'A changed motion preference cancels the ring' }).toBe(0);
    await request.fulfill({ status: 503, contentType: 'text/plain', body: 'unavailable' });
    await expect(button).toBeEnabled();
    await expect(button.locator('.premiere-submit-label')).toHaveText(path === '/it/' ? 'Ricordamelo' : 'Remind me');
    expect(await icon.evaluate(el => el.isConnected), 'The same bell remains available for retry').toBe(true);
  });

  for (const preference of ['reduced', 'paused']) {
    test(`${path}: ticket and bell feedback respects ${preference} motion`, async ({ page }) => {
      await page.emulateMedia({ reducedMotion: preference === 'reduced' ? 'reduce' : 'no-preference' });
      if (preference === 'paused') await page.addInitScript(() => sessionStorage.setItem('msc-motion-paused', 'true'));
      await openHome(page, path);
      const ticket = page.locator('.premiere-hero-ticket');
      await center(ticket);
      await ticket.hover();
      await expect(ticket).toHaveCSS('transform', 'none');
      await page.keyboard.press('Tab');
      await ticket.focus();
      expect(await ticket.evaluate(el => parseFloat(getComputedStyle(el).outlineWidth) >= 2)).toBe(true);
      await expect(ticket).toHaveCSS('transform', 'none');
      const masterclass = page.locator('.learning-masterclass-ticket').first();
      await center(masterclass);
      await masterclass.hover();
      await expect(masterclass.locator('.premiere-entry-surface')).toHaveCSS('transform', 'none');
      const reminder = page.locator('.premiere-submit');
      await reminder.click();
      expect(await reminder.locator('.premiere-submit-icon').evaluate(el => el.getAnimations().length)).toBe(0);
    });
  }
}
