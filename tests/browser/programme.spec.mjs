import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const edition = JSON.parse(readFileSync(new URL('../../data/editions/2027.json', import.meta.url)));

for (const path of ['/program', '/it/programma']) {
  test(`${path}: provisional programme keeps estimates distinct from confirmed event facts`, async ({ page }) => {
    await page.route('https://**/*', route => route.fulfill({ status: 200, body: '' }));
    await page.goto(path);
    const italian = path.startsWith('/it/');
    const main = page.locator('main');
    await expect(main.locator('.stage-weekend-orbit, .stage-program-jump, .stage-date')).toHaveCount(0);
    await expect(main.locator('h1')).toBeVisible();
    await expect(main).not.toContainText('2026');
    const schedule = main.locator('.stage-itinerary');
    await expect(schedule.locator('h2')).toHaveText(italian ? 'Programma provvisorio.' : 'Provisional programme.');
    const days = schedule.locator('.stage-route-stop');
    await expect(days).toHaveCount(3);
    for (const [i, day] of edition.provisionalProgramme.days.entries()) {
      const card = days.nth(i);
      await card.scrollIntoViewIfNeeded();
      await expect(card.locator('.stage-stop-date')).toHaveText(`${day.date.slice(-2)} NOV / 2027`);
      await expect(card.locator('.experience-day-note')).toHaveText(italian ? 'Orari indicativi' : 'Estimated times');
      await expect(card.locator('.experience-timetable time')).toHaveText(day.sessions.map(session => `${session.start} – ${session.end}`));
    }
    await expect(main.locator('.stage-pending dd')).toHaveText(Array(3).fill(italian ? 'Da confermare' : 'To be confirmed'));
    await expect(main.locator('.stage-pending dt')).toHaveText([italian ? 'Masterclass' : 'Masterclasses', 'Check-in', 'Chill']);
    const graph = JSON.parse(await page.locator('script[type="application/ld+json"]').textContent())['@graph'];
    const event = graph.find(node => node['@id'] === edition.eventId);
    expect(event.startDate).toBe(edition.startDate);
    expect(event.endDate).toBe(edition.endDate);
    expect(event.subEvent).toBeUndefined();
    expect(graph.find(node => node['@type'] === 'WebPage').mainEntity['@id']).toBe(edition.eventId);
    const answers = await main.locator('.experience-faq-item p').allTextContents();
    expect(graph.find(node => node['@type'] === 'FAQPage').mainEntity.map(question => question.acceptedAnswer.text)).toEqual(answers);
    expect(await main.locator('h1,h2,h3,p,li,dt,dd,a').evaluateAll(nodes => nodes.filter(node => {
      const box = node.getBoundingClientRect();
      return box.width && (box.left < -1 || box.right > document.documentElement.clientWidth + 1 || node.scrollWidth > node.clientWidth + 1);
    }).map(node => node.textContent)), 'Programme stays readable at each viewport').toEqual([]);
  });
}
