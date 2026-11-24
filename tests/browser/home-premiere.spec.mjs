import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function expectIntegratedHeroBelowNavigation(page) {
  const nav = await page.locator('.e27-nav').boundingBox();
  const media = await page.locator('.premiere-media').boundingBox();
  expect(media.y).toBeGreaterThanOrEqual(nav.y + nav.height - 1);
  await expect(page.locator('.premiere-star-trails')).toBeVisible();
  await expect(page.locator('.premiere-hero video, .premiere-film-control')).toHaveCount(0);
  const dates = await page.locator('#edition-facts').boundingBox();
  const panel = await page.locator('#early-bird').boundingBox();
  expect(dates.y + dates.height).toBeLessThanOrEqual(panel.y);
}

for (const path of ['/', '/it/']) {
  test(`${path}: Static image homepage preserves confirmed facts and immediate artist discovery`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator('body')).toHaveClass(/\bhome-premiere\b/);
    const heading = page.locator('.premiere-hero h1.premiere-statement');
    await expect(heading).toBeVisible();
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(heading).toHaveText('Milano Sensual Congress');
    await expect(page.locator('.premiere-subtitle')).toHaveText(path === '/it/' ? 'Il mondo della bachata si incontra a Milano' : 'The Bachata World Meets in Milano');
    await expect(page.locator('.premiere-lineup-action, #artist-showcase .e27-section-head')).toHaveCount(0);
    await expect(heading).toHaveCSS('opacity', '1');

    const media = page.locator('.premiere-hero .premiere-media');
    await expect(media.locator('video')).toHaveCount(0);
    await expect(page.locator('.premiere-copy')).toHaveCSS('opacity', '1');
    const bounds = await media.boundingBox();
    expect(bounds.height, 'The hero has a reserved visible area').toBeGreaterThan(150);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'The hero and heading fit the viewport').toBe(true);
    await expectIntegratedHeroBelowNavigation(page);

    const facts = page.locator('main #edition-facts');
    await expect(facts).toBeVisible();
    await expect(facts.locator('.premiere-venue')).toHaveCount(0);
    await expect(facts).toContainText('2027');
    await expect(facts.locator('time[datetime]')).toHaveCount(2);
    await expect(facts.locator('time[datetime="2027-11-19"]')).toBeVisible();
    await expect(facts.locator('time[datetime="2027-11-21"]')).toBeVisible();
    expect(await facts.evaluate(dates => Boolean(dates.compareDocumentPosition(document.getElementById('early-bird')) & Node.DOCUMENT_POSITION_FOLLOWING)), 'The event dates introduce the signup in reading order').toBe(true);
    const heroTicket = page.locator('#early-bird').getByRole('link', { name: path === '/it/' ? 'ACQUISTA IL TUO BIGLIETTO' : 'BUY YOUR TICKET', exact: true });
    await expect(heroTicket).toBeVisible();
    await expect(heroTicket).toHaveAttribute('href', 'https://lasalsadelbaile.com/MSC2027');
    const heroTicketBounds = await heroTicket.boundingBox();
    const signupBounds = await page.locator('#early-bird').boundingBox();
    expect(heroTicketBounds.height, 'The hero ticket link retains a usable touch target').toBeGreaterThanOrEqual(44);
    expect(heroTicketBounds.y, 'Ticket purchase is inside the early-bird panel').toBeGreaterThan(signupBounds.y);
    expect(heroTicketBounds.y + heroTicketBounds.height).toBeLessThan(signupBounds.y + signupBounds.height);
    const reminderBounds = await page.locator('#reminder-form').boundingBox();
    if (page.viewportSize().width <= 700) expect(heroTicketBounds.y + heroTicketBounds.height, 'Ticket purchase precedes the reminder form').toBeLessThanOrEqual(reminderBounds.y);
    else expect(heroTicketBounds.x + heroTicketBounds.width).toBeLessThanOrEqual(reminderBounds.x);


    await expect(page.locator('.scene-home, .e27-spark, .home-play-seal, .premiere-poster, #congress-film')).toHaveCount(0);
    expect(await page.locator('#artist-showcase').evaluate(artists => {
      const facts = document.getElementById('edition-facts');
      return Boolean(facts.compareDocumentPosition(artists) & Node.DOCUMENT_POSITION_FOLLOWING);
    }), 'Artist discovery follows the edition details').toBe(true);
    await expect(page.locator('#artist-showcase .e27-artist')).toHaveCount(10);
    await expect(page.locator('#artist-showcase [data-artist-preview]')).toHaveCount(0);
    await expect(page.locator('#artist-more')).toHaveCount(0);
    const lineupBox = await page.locator('#artist-showcase').boundingBox();
    const copyBox = await page.locator('.premiere-copy').boundingBox();
    const dateBox = await facts.boundingBox();
    expect(dateBox.y + dateBox.height, 'The date introduces the full lineup').toBeLessThanOrEqual(lineupBox.y);
    expect(copyBox.y, 'Booking follows the entire lineup at every width').toBeGreaterThanOrEqual(lineupBox.y + lineupBox.height);
    if (page.viewportSize().width > 700) {
      const cards = await page.locator('#artist-showcase .e27-artist').evaluateAll(items => items.map(item => item.getBoundingClientRect().toJSON()));
      expect(Math.abs(cards[0].y - cards[4].y)).toBeLessThan(1);
      expect(Math.abs(cards[5].y - cards[9].y)).toBeLessThan(1);
      expect(cards[5].y).toBeGreaterThan(cards[0].bottom);
      expect(cards[2].y).toBeLessThan(cards[1].y);
      expect(cards[1].y).toBeLessThan(cards[0].y);
    }
    const learning = page.locator('#your-level');
    const italian = path === '/it/';
    expect(await learning.evaluate(section => [section.previousElementSibling?.id, section.nextElementSibling?.id]), 'Workshop levels follow the artists and introduce the hotel').toEqual(['home-nations', 'your-stay']);
    await learning.scrollIntoViewIfNeeded();
    const learningTitle = learning.getByRole('heading', { level: 2 });
    await expect(learningTitle).toBeVisible();
    await expect(learningTitle).toHaveText(italian ? 'Un congresso per ogni stile e livello.' : 'A congress for every style and level.');
    const titleBounds = await learningTitle.boundingBox();
    const introBounds = await learning.locator('.learning-intro').boundingBox();
    const boardBounds = await learning.locator('.learning-board').boundingBox();
    expect(titleBounds.y + titleBounds.height, 'The heading introduces the workshop copy without overlap').toBeLessThanOrEqual(introBounds.y);
    if (page.viewportSize().width > 1000) {
      expect(titleBounds.x + titleBounds.width, 'The invitation leaves space for the timetable beside it').toBeLessThanOrEqual(boardBounds.x);
    } else {
      const programmeBounds = await learning.locator('.learning-program').boundingBox();
      expect(programmeBounds.y + programmeBounds.height, 'The timetable follows the invitation on smaller screens').toBeLessThanOrEqual(boardBounds.y);
    }
    await expect(learning.locator('.learning-room-count')).toHaveCount(0);
    await expect(learning.locator('.learning-intro strong')).toHaveText(italian
      ? ['tre sale', 'tre stili diversi', 'tre livelli ogni ora']
      : ['three rooms', 'three different styles', 'three levels every hour']);
    await expect(learning.locator('.learning-intro')).toContainText(italian
      ? 'ci impegniamo a proporre' : 'we make every effort to offer');
    const levels = italian ? ['Principianti', 'Intermedio', 'Avanzato'] : ['Beginner', 'Intermediate', 'Advanced'];
    for (const level of levels) {
      await expect(learning.getByRole('heading', { level: 3, name: level, exact: true }), 'Workshop levels are readable without relying on their colors').toBeVisible();
    }
    const timetable = learning.getByRole('table', { name: italian ? /Schema illustrativo/i : /Illustrative timetable/i });
    await expect(timetable, 'The example is identified as an illustrative timetable').toBeVisible();
    await expect(timetable.locator('caption')).toHaveCount(0);
    await expect(learning.locator('#learning-timetable-note')).toHaveCount(0);
    expect(await timetable.getAttribute('aria-describedby')).toBeNull();
    await expect(timetable).toHaveAttribute('aria-label', italian
      ? 'Schema illustrativo: livelli e stili. Programma definitivo 2027 in arrivo.'
      : 'Illustrative timetable: levels and styles. Final 2027 schedule to follow.');
    for (const room of ['01', '02', '03']) {
      await expect(timetable.getByRole('columnheader', { name: `${italian ? 'Sala' : 'Room'} ${room}`, exact: true })).toBeVisible();
    }
    const workshopSlots = timetable.locator('tbody tr:not(.learning-masterclass-row)');
    await expect(workshopSlots).toHaveCount(3);
    await expect(timetable.locator('tbody tr')).toHaveCount(3);
    await expect(timetable.getByRole('rowheader')).toHaveText(['19:00', '20:00', '21:00']);
    await expect(learning.locator('.learning-board-title')).toHaveText(italian ? 'Scegli il livello giusto per te.' : 'Attend the right level for you.');
    for (const [index, slot] of (await workshopSlots.all()).entries()) {
      const cells = slot.getByRole('cell');
      await expect(cells).toHaveCount(3);
      const choices = await cells.locator('strong').allTextContents();
      const expected = index === 2 ? [levels[0], levels[1], 'Masterclass'] : levels;
      expect(choices.map(text => text.trim()).sort(), 'The last illustrative row includes the masterclass').toEqual([...expected].sort());
    }
    await expect(timetable.locator('.learning-masterclass-row')).toHaveCount(0);
    const masterclassRow = timetable.locator('tbody tr').nth(2);
    const masterclassSlot = masterclassRow.getByRole('cell').nth(1).locator('.learning-masterclass-slot');
    await expect(masterclassSlot.locator('strong')).toHaveText('Masterclass');
    await expect(masterclassSlot).toHaveText('Masterclass');
    const masterclassColors = await masterclassSlot.evaluate(slot => {
      const rgb = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
      const luminance = values => values.map(value => {
        value /= 255;
        return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
      }).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
      const background = rgb(getComputedStyle(slot).backgroundColor);
      const backgroundLight = luminance(background);
      return { background, textContrast: [...slot.querySelectorAll('strong, span')].map(element => {
        const foregroundLight = luminance(rgb(getComputedStyle(element).color));
        return (Math.max(foregroundLight, backgroundLight) + .05) / (Math.min(foregroundLight, backgroundLight) + .05);
      }) };
    });
    expect(masterclassColors.background[0], 'The masterclass uses the red accent').toBeGreaterThan(Math.max(...masterclassColors.background.slice(1)));
    for (const contrast of masterclassColors.textContrast) expect(contrast, 'Masterclass text stays readable on its red background').toBeGreaterThanOrEqual(4.5);
    await expect(learning.locator('.learning-program')).toHaveText(italian ? 'Programma in arrivo' : 'Programme out soon');
    await expect(page.locator('a[href="/program"], a[href="/it/programma"]')).toHaveCount(0);
    const ticketLinks = page.locator('a.premiere-ticket');
    expect(await ticketLinks.count(), 'Pass purchase retains the ticket graphic').toBeGreaterThan(0);
    expect(await ticketLinks.evaluateAll(links => links.map(link => link.getAttribute('href'))))
      .toEqual(expect.arrayContaining(['https://lasalsadelbaile.com/MSC2027']));
    expect(await ticketLinks.evaluateAll(links => links.every(link => ['https://lasalsadelbaile.com/MSC2027'].includes(link.getAttribute('href')))), 'Only ticket purchases use ticket graphics').toBe(true);
    const ambassador = page.locator('#promoter-invitation a');
    await expect(ambassador).toHaveClass('e27-button');
    await expect(ambassador).toHaveAttribute('href', italian ? '/it/promoters' : '/promoters');
    expect((await ambassador.boundingBox()).height, 'The Ambassador invitation retains a usable touch target').toBeGreaterThanOrEqual(44);
    const masterclasses = learning.locator('.learning-masterclass');
    await expect(masterclasses.getByRole('heading', { level: 3 })).toHaveText(italian ? 'Biglietti masterclass.' : 'Masterclass tickets.');
    await expect(masterclasses.locator('.learning-masterclass-artists li')).toHaveText(['Gero y Migle', 'Pablo y Raquel', 'Klau y Ros', 'Alba', 'Aitor Gomez']);
    const options = masterclasses.locator('.learning-masterclass-option');
    await expect(options).toHaveCount(3);
    const optionBounds = [];
    for (const option of await options.all()) {
      const ticket = option.locator('.learning-masterclass-ticket');
      await expect(ticket).toHaveAttribute('href', 'https://lasalsadelbaile.com/MSC2027');
      expect((await ticket.boundingBox()).height).toBeGreaterThanOrEqual(44);
      await expect(option.locator('.learning-masterclass-details')).toHaveAttribute('href', /masterclass#(three-masterclasses|ladystyle|dominican-bachata)$/);
      optionBounds.push(await option.boundingBox());
    }
    if (page.viewportSize().width > 1100) {
      expect(Math.abs(optionBounds[0].y - optionBounds[2].y)).toBeLessThan(2);
      expect(optionBounds[1].x).toBeGreaterThanOrEqual(optionBounds[0].x + optionBounds[0].width - 1);
      expect(optionBounds[2].x).toBeGreaterThanOrEqual(optionBounds[1].x + optionBounds[1].width - 1);
    } else if (page.viewportSize().width > 600) {
      expect(optionBounds[1].y).toBeGreaterThanOrEqual(optionBounds[0].y + optionBounds[0].height - 1);
      expect(Math.abs(optionBounds[1].y - optionBounds[2].y)).toBeLessThan(2);
      expect(optionBounds[2].x).toBeGreaterThanOrEqual(optionBounds[1].x + optionBounds[1].width - 1);
    } else {
      expect(optionBounds[1].y).toBeGreaterThanOrEqual(optionBounds[0].y + optionBounds[0].height - 1);
      expect(optionBounds[2].y).toBeGreaterThanOrEqual(optionBounds[1].y + optionBounds[1].height - 1);
    }
    const masterclassTitle = masterclasses.getByRole('heading', { level: 3 });
    const headingBox = await masterclassTitle.boundingBox();
    const sectionBox = await masterclasses.boundingBox();
    expect(Math.abs((headingBox.x + headingBox.width / 2) - (sectionBox.x + sectionBox.width / 2)), 'Masterclass title is centered').toBeLessThan(2);
    const portraits = masterclasses.locator('.learning-masterclass-artists img');
    await expect(portraits).toHaveCount(5);
    for (const portrait of await portraits.all()) {
      await portrait.scrollIntoViewIfNeeded();
      await expect.poll(() => portrait.evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
    }
    await expect(portraits.nth(3)).toHaveAttribute('src', /alba-masterclass-portrait/);
    await expect(portraits.nth(4)).toHaveAttribute('src', /aitor-gomez-masterclass-portrait/);
    await page.evaluate(() => document.fonts.ready);
    const clippedLearning = await learning.locator('h2, h3, h4, p, a, table, caption, th, td, .learning-workshop strong, .learning-workshop span, .learning-masterclass-slot strong, .learning-masterclass-slot span').evaluateAll(elements => elements.filter(element => {
      const { left, right } = element.getBoundingClientRect();
      return left < -1 || right > document.documentElement.clientWidth + 1 || element.scrollWidth > element.clientWidth + 1;
    }).map(element => element.textContent.trim()));
    expect(clippedLearning, 'Workshop levels, explanations and invitations stay readable within the viewport').toEqual([]);
    await expect(page.locator('#the-congress, #home-journal')).toHaveCount(0);
    const stylesheet = page.locator('head style[data-inline="css/home-premiere.css"]');
    await expect(stylesheet).toHaveCount(1);
    expect(await stylesheet.textContent()).toMatch(/\.home-premiere\b/);
  });

  test(`${path}: a wide short desktop preserves the hero and text below the header`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.use.viewport.width < 1000, 'Additional desktop geometry; standard phone and tablet are covered above');
    await page.setViewportSize({ width: 2048, height: 720 });
    await page.goto(path);
    await page.evaluate(() => document.fonts.ready);
    await expectIntegratedHeroBelowNavigation(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  });
}
