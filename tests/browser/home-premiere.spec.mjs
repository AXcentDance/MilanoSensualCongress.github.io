import { test, expect } from '@playwright/test';

test.beforeEach(async ({ context }) => {
  await context.route('https://**/*', route => route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
});

async function expectUncroppedHeroBelowNavigation(page) {
  const nav = await page.locator('.e27-nav').boundingBox();
  const media = await page.locator('.premiere-media').boundingBox();
  const viewportWidth = await page.evaluate(() => document.documentElement.clientWidth);
  if (viewportWidth > 1000) {
    const leftMargin = media.x;
    const rightMargin = viewportWidth - media.x - media.width;
    expect(Math.abs(leftMargin - rightMargin), 'The desktop film has balanced margins').toBeLessThanOrEqual(1);
    expect(leftMargin, 'The desktop film leaves a visible margin for its soft fade').toBeGreaterThan(viewportWidth * .02);
    expect(media.width, 'The desktop reduction keeps the film prominent').toBeGreaterThanOrEqual(Math.min(viewportWidth * .86, 1500));
    expect(media.width, 'The film stays comfortably bounded on wide desktops').toBeLessThanOrEqual(1601);
  } else {
    expect(Math.abs(media.x), 'The phone and tablet scene starts at the viewport’s left edge').toBeLessThanOrEqual(1);
    expect(Math.abs(media.width - viewportWidth), 'The phone and tablet scene spans the viewport').toBeLessThanOrEqual(1);
  }
  expect(media.y, 'The opening film starts below the navigation, not underneath it').toBeGreaterThanOrEqual(nav.y + nav.height - 1);

  // The title is baked into both 1920×1080 films and the matching 16:9 poster.
  // Measure how the browser fits that source, rather than asserting a CSS
  // aspect-ratio declaration that could still be overridden by a height cap.
  const frames = await page.locator('.premiere-media > :is(img,video)').evaluateAll(elements => elements.map(el => {
    const { x, y, width, height } = el.getBoundingClientRect();
    const css = getComputedStyle(el);
    const sourceWidth = Number(el.getAttribute('width'));
    const sourceHeight = Number(el.getAttribute('height'));
    const scale = css.objectFit === 'contain'
      ? Math.min(width / sourceWidth, height / sourceHeight)
      : Math.max(width / sourceWidth, height / sourceHeight);
    return {
      name: el.id || 'poster',
      bounds: { x, y, width, height },
      fit: css.objectFit,
      sourceRatio: sourceWidth / sourceHeight,
      clippedWidth: sourceWidth * scale - width,
      clippedHeight: sourceHeight * scale - height,
    };
  }));
  expect(frames).toHaveLength(3);
  for (const frame of frames) {
    expect(['cover', 'contain'], `${frame.name} preserves the source proportions`).toContain(frame.fit);
    expect(frame.sourceRatio).toBeCloseTo(16 / 9, 5);
    expect(frame.clippedWidth, `${frame.name}: no part of the source frame is cut off horizontally`).toBeLessThanOrEqual(1);
    expect(frame.clippedHeight, `${frame.name}: the title and Duomo are not cropped vertically`).toBeLessThanOrEqual(1);
    expect(Math.abs(frame.bounds.x - media.x), `${frame.name}: the actual frame aligns with the scene’s left edge`).toBeLessThanOrEqual(1);
    expect(Math.abs(frame.bounds.x + frame.bounds.width - media.x - media.width), `${frame.name}: the actual frame aligns with the scene’s right edge`).toBeLessThanOrEqual(1);
    expect(Math.abs(frame.bounds.height - frame.bounds.width / frame.sourceRatio), `${frame.name}: the frame retains its natural height without letterboxing`).toBeLessThanOrEqual(1);
    expect(frame.bounds.y, `${frame.name}: the top edge is below navigation`).toBeGreaterThanOrEqual(nav.y + nav.height - 1);
    expect(frame.bounds.y + frame.bounds.height, `${frame.name}: the scene does not clip the bottom of the film`).toBeLessThanOrEqual(media.y + media.height + 1);
  }

  const film = frames.find(frame => frame.name === 'heroVideo').bounds;
  const dates = await page.locator('#edition-facts').boundingBox();
  const panel = await page.locator('#early-bird').boundingBox();
  const offer = await page.locator('#early-bird-title').boundingBox();
  // The baked title ends at approximately 66.5% of the exported source frame.
  // The dates now introduce the offer; the panel can extend below the film on
  // smaller screens. Anchor against the source frame, not the taller stage.
  expect(dates.y, 'The event dates clear the baked congress title').toBeGreaterThanOrEqual(film.y + film.height * .68);
  expect(dates.y, 'The event dates begin over the lower part of the scene').toBeLessThan(film.y + film.height);
  expect(dates.y + dates.height, 'The dates stay above the early-bird panel without overlapping').toBeLessThanOrEqual(panel.y + 1);
  expect(offer.y, 'The early-bird heading clears the baked congress title').toBeGreaterThanOrEqual(film.y + film.height * .68);
}

for (const path of ['/', '/it/']) {
  test(`${path}: cinematic homepage preserves confirmed facts and immediate artist discovery`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator('body')).toHaveClass(/\bhome-premiere\b/);
    const heading = page.locator('.premiere-hero h1.premiere-statement');
    await expect(heading).toBeVisible();
    await expect(heading).toHaveCSS('opacity', '1');

    const media = page.locator('.premiere-hero .premiere-media');
    await expect(media.locator('#heroVideo')).toHaveCount(1);
    await expect(media.locator('#heroAmbientVideo')).toHaveCount(1);
    const bounds = await media.boundingBox();
    expect(bounds.height, 'The opening film has a reserved visible area').toBeGreaterThan(150);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'The film and heading fit the viewport').toBe(true);
    await expectUncroppedHeroBelowNavigation(page);

    const facts = page.locator('main #edition-facts');
    await expect(facts).toBeVisible();
    await expect(facts).toContainText('Devero Hotel');
    await expect(facts).toContainText('2027');
    await expect(facts.locator('time[datetime]')).toHaveCount(2);
    await expect(facts.locator('time[datetime="2027-11-19"]')).toBeVisible();
    await expect(facts.locator('time[datetime="2027-11-21"]')).toBeVisible();
    expect(await facts.evaluate(dates => Boolean(dates.compareDocumentPosition(document.getElementById('early-bird')) & Node.DOCUMENT_POSITION_FOLLOWING)), 'The event dates introduce the signup in reading order').toBe(true);
    const heroTicket = facts.getByRole('link', { name: path === '/it/' ? 'Acquista il tuo biglietto' : 'Buy your Ticket', exact: true });
    await expect(heroTicket).toBeVisible();
    await expect(heroTicket).toHaveAttribute('href', path === '/it/' ? '/it/tickets' : '/tickets');
    const heroStub = heroTicket.locator('.premiere-ticket-stub');
    await expect(heroStub).toHaveAttribute('aria-hidden', 'true');
    const heroStubBounds = await heroStub.boundingBox();
    const heroLabelBounds = await heroTicket.locator('.premiere-ticket-label').boundingBox();
    expect(heroStubBounds.x + heroStubBounds.width, 'The hero ticket stub sits to the left of its readable label').toBeLessThanOrEqual(heroLabelBounds.x + 1);
    const heroTicketBounds = await heroTicket.boundingBox();
    const venueBounds = await facts.locator('.premiere-venue').boundingBox();
    const signupBounds = await page.locator('#early-bird').boundingBox();
    expect(heroTicketBounds.height, 'The hero ticket link retains a usable touch target').toBeGreaterThanOrEqual(44);
    expect(heroTicketBounds.y, 'Ticket purchase follows the venue information').toBeGreaterThanOrEqual(venueBounds.y + venueBounds.height - 1);
    expect(heroTicketBounds.y + heroTicketBounds.height, 'Ticket purchase precedes the reminder panel without overlap').toBeLessThanOrEqual(signupBounds.y + 1);

    await expect(page.locator('.scene-home, .e27-spark, .home-play-seal, .premiere-poster, #congress-film')).toHaveCount(0);
    expect(await page.locator('#artist-showcase').evaluate(artists => {
      const facts = document.getElementById('edition-facts');
      return Boolean(facts.compareDocumentPosition(artists) & Node.DOCUMENT_POSITION_FOLLOWING);
    }), 'Artist discovery follows the edition details').toBe(true);
    await expect(page.locator('#artist-showcase [data-artist-video]')).toHaveCount(8);
    const learning = page.locator('#your-level');
    const italian = path === '/it/';
    expect(await learning.evaluate(section => [section.previousElementSibling?.id, section.nextElementSibling?.id]), 'Workshop levels follow the artists and introduce the hotel').toEqual(['artist-showcase', 'your-stay']);
    await learning.scrollIntoViewIfNeeded();
    const learningTitle = learning.getByRole('heading', { level: 2 });
    await expect(learningTitle).toBeVisible();
    await expect(learningTitle).toHaveText(italian ? 'Un congresso per ogni stile e livello.' : 'A congress for every style and level.');
    const titleBounds = await learningTitle.boundingBox();
    const layoutBounds = await learning.locator('.learning-layout').boundingBox();
    expect(titleBounds.y + titleBounds.height, 'The learning heading sits above the copy and timetable').toBeLessThanOrEqual(layoutBounds.y);
    expect(titleBounds.width, 'The learning heading spans the complete section grid').toBeGreaterThanOrEqual(layoutBounds.width - 1);
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
    await expect(timetable.locator('tbody tr')).toHaveCount(4);
    await expect(timetable.getByRole('rowheader')).toHaveText(['19:00', '20:00', '21:00', '22:00']);
    for (const slot of await workshopSlots.all()) {
      const cells = slot.getByRole('cell');
      await expect(cells).toHaveCount(3);
      const choices = await cells.locator('strong').allTextContents();
      expect(choices.map(text => text.trim()).sort(), 'Each illustrated workshop slot offers all three levels').toEqual([...levels].sort());
    }
    const masterclassRow = timetable.locator('.learning-masterclass-row');
    await expect(masterclassRow.getByRole('rowheader')).toHaveText('22:00');
    await expect(masterclassRow.getByRole('cell')).toHaveCount(1);
    await expect(masterclassRow.getByRole('cell')).toHaveAttribute('colspan', '3');
    await expect(masterclassRow.locator('.learning-workshop')).toHaveCount(0);
    const masterclassSlot = masterclassRow.locator('.learning-masterclass-slot');
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
    const programme = learning.getByRole('link', { name: italian ? 'Esplora il programma' : 'Explore the programme', exact: true });
    await expect(programme).toBeVisible();
    await expect(programme).toHaveAttribute('href', italian ? '/it/programma' : '/program');
    await expect(programme).toHaveClass(/\be27-text-link\b/);
    // Firefox can report 43.99997px for a 44px box after coordinate subtraction.
    expect((await programme.boundingBox()).height + .01, 'The programme link retains a usable touch target').toBeGreaterThanOrEqual(44);
    const ticketLinks = page.locator('a.premiere-ticket');
    expect(await ticketLinks.count(), 'Pass purchase retains the ticket graphic').toBeGreaterThan(0);
    expect(await ticketLinks.evaluateAll(links => links.map(link => link.getAttribute('href'))))
      .toEqual(expect.arrayContaining([italian ? '/it/tickets' : '/tickets']));
    expect(await ticketLinks.evaluateAll(links => links.every(link => ['/tickets', '/it/tickets'].includes(link.getAttribute('href')))), 'Only ticket purchases use ticket graphics').toBe(true);
    const ambassador = page.locator('#promoter-invitation a');
    await expect(ambassador).toHaveClass('e27-button');
    await expect(ambassador).toHaveAttribute('href', italian ? '/it/promoters' : '/promoters');
    expect((await ambassador.boundingBox()).height, 'The Ambassador invitation retains a usable touch target').toBeGreaterThanOrEqual(44);
    const masterclasses = learning.locator('.learning-masterclass');
    await expect(masterclasses.getByRole('heading', { level: 3 })).toHaveText(italian ? 'Biglietti masterclass.' : 'Masterclass tickets.');
    await expect(masterclasses.locator('.learning-masterclass-artists li')).toHaveText(['Gero y Migle', 'Klau y Ros', 'Pablo y Raquel']);
    const masterclassTicket = masterclasses.getByRole('link', { name: italian ? 'Prendi il tuo biglietto' : 'Take your ticket', exact: true });
    await expect(masterclassTicket).toBeVisible();
    await expect(masterclassTicket).toHaveAttribute('href', italian ? '/it/tickets' : '/tickets');
    expect((await masterclassTicket.boundingBox()).height, 'The masterclass ticket link retains a usable touch target').toBeGreaterThanOrEqual(44);
    await page.evaluate(() => document.fonts.ready);
    const clippedLearning = await learning.locator('h2, h3, p, a, table, caption, th, td, .learning-workshop strong, .learning-workshop span, .learning-masterclass-slot strong, .learning-masterclass-slot span').evaluateAll(elements => elements.filter(element => {
      const { left, right } = element.getBoundingClientRect();
      return left < -1 || right > document.documentElement.clientWidth + 1 || element.scrollWidth > element.clientWidth + 1;
    }).map(element => element.textContent.trim()));
    expect(clippedLearning, 'Workshop levels, explanations and invitations stay readable within the viewport').toEqual([]);
    await expect(page.locator('#the-congress, #home-journal')).toHaveCount(0);
    const stylesheet = page.locator('head style[data-inline="css/home-premiere.css"]');
    await expect(stylesheet).toHaveCount(1);
    expect(await stylesheet.textContent()).toMatch(/\.home-premiere\b/);
  });

  test(`${path}: a wide short desktop preserves the complete film title below the header`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.use.viewport.width < 1000, 'Additional desktop geometry; standard phone and tablet are covered above');
    await page.setViewportSize({ width: 2048, height: 720 });
    await page.goto(path);
    await page.evaluate(() => document.fonts.ready);
    await expectUncroppedHeroBelowNavigation(page);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  });
}
