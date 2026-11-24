import { test, expect } from '@playwright/test';

for (const base of ['/', '/it/']) {
  test(`${base}: masterclass discovery connects all three 2027 ticket options`, async ({ page }) => {
    await page.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
    await page.goto(base);
    await page.locator('.learning-masterclass-title a').click();
    await expect(page).toHaveURL(new RegExp(`${base}masterclass$`));
    await expect(page.locator('h1')).toBeVisible();
    const expected = [
      ['three-masterclasses', ['Gero y Migle', 'Klau y Ros', 'Pablo y Raquel']],
      ['ladystyle', ['Alba']],
      ['dominican-bachata', ['Aitor Gomez']],
    ];
    for (const [id, artists] of expected) {
      const option = page.locator(`#${id}`);
      for (const name of artists) await expect(option).toContainText(name);
      await option.getByRole('link').click();
      await expect(page).toHaveURL(/#booking$/);
      await expect(page.locator('#booking')).toBeInViewport();
    }
    // The old 2026 course and its €59 offer must not be sold as a 2027 option.
    await expect(page.locator('main')).not.toContainText('€59');
    const graph = JSON.parse(await page.locator('script[type="application/ld+json"]').textContent());
    expect(graph['@graph'].some(node => node['@type'] === 'Course' && node.hasCourseInstance?.startDate?.startsWith('2026'))).toBe(false);
    await expect(page.locator('#booking')).toContainText(base === '/it/' ? 'saranno annunciati' : 'will be announced');
  });
}
