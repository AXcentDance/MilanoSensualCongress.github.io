import { readFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';

const { countries } = JSON.parse(readFileSync(new URL('../../data/community-2026.json', import.meta.url), 'utf8'));
const country = code => countries.find(entry => entry.code === code);
const isPhone = page => page.viewportSize().width <= 600;
const phoneAtlasSource = '/images/europe-community-sculpted-emerald-country-borders.svg';
const widerAtlasSource = '/images/europe-community-sculpted-emerald-coastlines.svg';
const percentage = (value, lang) => value === null
  ? (lang === 'en' ? 'To be confirmed' : 'Da confermare')
  : new Intl.NumberFormat(lang, { maximumSignificantDigits: 15, useGrouping: false }).format(value) + '%';

async function stubExternal(context, baseURL) {
  const localOrigin = new URL(baseURL).origin;
  await context.route(/^https?:\/\//, route => new URL(route.request().url()).origin === localOrigin
    ? route.continue()
    : route.fulfill({ status: 200, contentType: 'text/plain', body: '' }));
}

function collectErrors(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  return errors;
}

async function expectFits(page, section) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'No horizontal page overflow').toBe(true);
  const selectors = isPhone(page)
    ? '.nations-pocket-heading, .nations-pocket-select:visible, .nations-pocket-status, .nations-pocket-note, .nations-pocket-pin:visible'
    : '#nations-title:visible, .nations-intro:visible, .nations-country:visible, .nations-selected-name:visible, .nations-search:visible, .nations-stats:visible, #congress-facts strong:visible, #congress-facts small:visible';
  const overflowing = await section.locator(selectors).evaluateAll(elements => elements.filter(element => {
    const box = element.getBoundingClientRect();
    return box.left < -1 || box.right > document.documentElement.clientWidth + 1 || element.scrollWidth > element.clientWidth + 1;
  }).map(element => element.textContent.trim()));
  expect(overflowing, 'The heading, introduction, country names, statistics and search remain readable within the viewport').toEqual([]);
}

async function routeGeometry(section) {
  return section.evaluate(element => {
    const route = element.querySelector('.nations-route-active');
    const origin = element.querySelector('.nations-origin');
    return {
      coordinates: route.getAttribute('d').match(/-?\d+(?:\.\d+)?/g).map(Number),
      origin: [Number(origin.getAttribute('cx')), Number(origin.getAttribute('cy'))],
    };
  });
}

async function countryOrigin(section, code) {
  return section.locator(`[data-country="${code}"]`).evaluate(button => [Number(button.dataset.mapX), Number(button.dataset.mapY)]);
}

function expectMovingOrigin(geometry, from, to, destination) {
  expect(geometry.origin, 'The capital marker follows the moving route origin').toEqual(geometry.coordinates.slice(0, 2));
  for (let axis = 0; axis < 2; axis += 1) {
    expect(geometry.origin[axis], 'The route moves through an intermediate position').toBeGreaterThan(Math.min(from[axis], to[axis]));
    expect(geometry.origin[axis]).toBeLessThan(Math.max(from[axis], to[axis]));
  }
  expect(geometry.coordinates.slice(-2), 'Milano remains fixed during the transition').toEqual(destination);
}

async function expectNumbersSection(page, section, lang) {
  await expect(section.locator('#nations-title')).toHaveText(lang === 'en' ? 'Our Congress in Numbers' : 'Il nostro congresso in numeri');
  expect(await section.evaluate(element => element.previousElementSibling?.classList.contains('premiere-hero')), 'The numbers section directly follows the opening scene').toBe(true);
  expect(await section.evaluate(element => element.nextElementSibling?.id), 'Artist discovery follows the numbers section').toBe('artist-showcase');
  await expect(page.locator('.scene-progress, .home-facts')).toHaveCount(0);
  await expect(page.locator('#congress-facts')).toHaveCount(1);
  const facts = section.locator('#congress-facts');
  if (isPhone(page)) {
    await expect(facts).toBeHidden();
    await expect(section.locator('.nations-stage')).toBeHidden();
    await expect(section.locator('.nations-mobile')).toBeVisible();
  } else {
    await expect(facts).toBeVisible();
    await expect(section.locator('.nations-mobile')).toBeHidden();
  }
  await expect(facts.locator('strong')).toHaveText([lang === 'en' ? '1,000+' : '1.000+', '20+', '20+']);
  await expect(facts.locator('small')).toHaveText(lang === 'en' ? ['dancers', 'nations', 'social hours'] : ['ballerini', 'nazioni', 'ore di social']);
}

async function expectPocketGeometry(page, section) {
  const geometry = await section.evaluate(element => {
    const box = element.querySelector('.nations-pocket-view').getBoundingClientRect();
    const pins = [...element.querySelectorAll('.nations-pocket-pin')].filter(pin => !pin.hidden).map(pin => {
      const { left, top, right, bottom, width, height } = pin.getBoundingClientRect();
      return { code: pin.dataset.mobileCountry, left, top, right, bottom, width, height };
    });
    return { height: element.getBoundingClientRect().height, map: { left: box.left, top: box.top, right: box.right, bottom: box.bottom }, pins };
  });
  expect(geometry.height, 'The closed phone section remains compact').toBeLessThanOrEqual(600);
  expect(geometry.pins.length, 'The selected crop retains country context').toBeGreaterThanOrEqual(1);
  expect(geometry.pins.length).toBeLessThanOrEqual(12);
  for (const pin of geometry.pins) {
    expect(pin.left, `${pin.code} stays inside the map`).toBeGreaterThanOrEqual(geometry.map.left - 1);
    expect(pin.right).toBeLessThanOrEqual(geometry.map.right + 1);
    expect(pin.top).toBeGreaterThanOrEqual(geometry.map.top - 1);
    expect(pin.bottom).toBeLessThanOrEqual(geometry.map.bottom + 1);
    expect(pin.width, `${pin.code} is a usable touch target`).toBeGreaterThanOrEqual(44);
    expect(pin.height).toBeGreaterThanOrEqual(44);
  }
  for (let i = 0; i < geometry.pins.length; i += 1) {
    for (const other of geometry.pins.slice(i + 1)) {
      const pin = geometry.pins[i];
      const overlaps = Math.min(pin.right, other.right) - Math.max(pin.left, other.left) > 1 &&
        Math.min(pin.bottom, other.bottom) - Math.max(pin.top, other.top) > 1;
      expect(overlaps, `${pin.code} and ${other.code} pins do not overlap`).toBe(false);
    }
  }
  await expectFits(page, section);
}

async function expectPocketCountry(section, code, lang, value = country(code).statistics.dancerPercent) {
  await expect(section.locator('.nations-pocket-select')).toHaveValue(code);
  const status = section.locator('.nations-pocket-status');
  await expect(status).toContainText(country(code).name[lang]);
  await expect(status).toContainText(percentage(value, lang));
  await expect(status).toHaveAttribute('aria-live', 'polite');
  const pin = section.locator(`[data-mobile-country="${code}"]`);
  await expect(pin).toHaveAttribute('aria-pressed', 'true');
  await expect(section.locator('.nations-pocket-pin[aria-pressed="true"]')).toHaveCount(1);
}

async function expectPocketDemo(section, lang) {
  await expect(section.locator('.nations-pocket-note')).toBeVisible();
  await expect(section.locator('.nations-pocket-note')).toHaveText(lang === 'en'
    ? 'Country share · Preview figures' : 'Quota per paese · Dati dimostrativi');
}

async function expectCountryNamesFit(section) {
  const overflowing = await section.evaluate(element => {
    const title = element.querySelector('.nations-selected-name');
    const original = title.textContent;
    const reservedHeight = title.getBoundingClientRect().height;
    const tooTall = [];
    for (const button of element.querySelectorAll('[data-country]')) {
      title.textContent = button.dataset.countryName;
      if (title.getBoundingClientRect().height > reservedHeight + 1) tooTall.push(button.dataset.countryName);
    }
    title.textContent = original;
    return tooTall;
  });
  expect(overflowing, 'Every country name fits the space reserved in the result panel').toEqual([]);
}

async function panelLayout(section) {
  return section.evaluate(element => {
    const bounds = selector => {
      const { x, y, width, height } = element.querySelector(selector).getBoundingClientRect();
      return { x, y, width, height };
    };
    return { scroll: { x: window.scrollX, y: window.scrollY }, listScroll: element.querySelector('.nations-list').scrollTop, panel: bounds('.nations-panel'), map: bounds('.nations-atlas') };
  });
}

async function expectStablePanel(page, section, before, action) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const after = await panelLayout(section);
  expect(after.scroll, `${action} leaves the viewport in place`).toEqual(before.scroll);
  expect(after.listScroll, `${action} keeps the flag picker at its current scroll position`).toEqual(before.listScroll);
  for (const area of ['panel', 'map']) {
    for (const dimension of ['x', 'y', 'width', 'height']) {
      // Browser subpixel rounding is allowed, visible movement is not.
      expect(Math.abs(after[area][dimension] - before[area][dimension]), `${action} keeps the ${area} stable (${dimension})`).toBeLessThanOrEqual(0.1);
    }
  }
}

async function chooseFlagWithoutMoving(page, section, code, input = 'pointer') {
  const button = section.locator(`[data-country="${code}"]`);
  await expect(section.locator('.nations-directory')).toBeVisible();
  // Center the control before measuring: a merely visible flag can sit under
  // the sticky header, making Playwright scroll again before dispatching click.
  await button.evaluate(element => element.scrollIntoView({ block: 'center', behavior: 'instant' }));
  if (input === 'keyboard') await button.focus();
  const before = await panelLayout(section);
  if (input === 'keyboard') await page.keyboard.press('Space');
  else await button.click();
  await expect(section.locator('.nations-directory')).toBeVisible();
  await expect(section.locator('.nations-passport')).toBeVisible();
  await expect(button, 'Selection keeps focus on the chosen flag').toBeFocused();
  await expectStablePanel(page, section, before, `Selecting ${code} with ${input}`);
}

// These deliberately synthetic figures exercise the interface without turning
// unconfirmed attendance data into public facts.
async function fixtureStatistics(page, baseURL, path) {
  const origin = new URL(baseURL).origin;
  await page.route(url => url.origin === origin && url.pathname === path, async route => {
    const response = await route.fetch();
    let body = await response.text();
    for (const [code, attributes] of Object.entries({
      CH: { 'data-dancer-percent': '0', 'data-guest-artists': '0' },
      DE: { 'data-dancer-percent': '12.5', 'data-guest-artists': '2' },
      GB: { 'data-dancer-percent': '', 'data-guest-artists': '', 'data-map-x': '24', 'data-map-y': '362.42', 'data-map-approximate': 'true' },
    })) {
      body = body.replace(new RegExp(`<button\\b[^>]*data-country="${code}"[^>]*>`), button => {
        for (const [name, value] of Object.entries(attributes)) {
          const attribute = new RegExp(`${name}="[^"]*"`);
          if (!attribute.test(button)) throw new Error(`Missing generated ${name} attribute for ${code}`);
          button = button.replace(attribute, `${name}="${value}"`);
        }
        return button;
      });
    }
    await route.fulfill({ response, body });
  });
}

test.beforeEach(async ({ context, baseURL }) => stubExternal(context, baseURL));

for (const [lang, path] of [['en', '/'], ['it', '/it/']]) {
  test(`${path}: homepage nations keep country exploration compact and usable at each width`, async ({ page, browserName }) => {
    const errors = collectErrors(page);
    const requestedFlags = new Set();
    let requestedAtlas = false;
    page.on('request', request => {
      if ([phoneAtlasSource, widerAtlasSource].includes(new URL(request.url()).pathname)) requestedAtlas = true;
      const match = new URL(request.url()).pathname.match(/\/flags\/([a-z]{2})\.webp$/);
      if (match) requestedFlags.add(match[1].toUpperCase());
    });
    await page.goto(path);
    expect(requestedAtlas, 'The offscreen atlas does not compete with the opening film').toBe(false);
    expect([...requestedFlags], 'Offscreen flags do not compete with the opening film').toEqual([]);
    const section = page.locator('#home-nations');
    await section.scrollIntoViewIfNeeded();
    const atlas = section.locator('[data-nations-map-src]:visible');
    await expect(atlas).toHaveAttribute('src', isPhone(page) ? phoneAtlasSource : widerAtlasSource);
    await expect.poll(() => atlas.evaluate(image => image.complete && image.naturalWidth === 800), { message: 'The actual shared SVG decodes' }).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    await expectNumbersSection(page, section, lang);
    if (isPhone(page)) {
      const picker = section.locator('.nations-pocket-select');
      await expect(picker).toBeEnabled();
      await expect(picker).toHaveAccessibleName(lang === 'en' ? 'Choose a country' : 'Scegli un paese');
      await expect(picker.locator('option')).toHaveCount(countries.length);
      expect(await picker.locator('option').allTextContents()).toEqual(expect.arrayContaining(countries.map(entry => entry.name[lang])));
      await expectPocketDemo(section, lang);
      await expectPocketCountry(section, 'IT', lang);
      expect(await section.locator('.nations-pocket-pin:visible').count()).toBeGreaterThanOrEqual(6);
      await expectPocketGeometry(page, section);
      await section.locator('[data-mobile-country="DE"]').tap();
      await expectPocketCountry(section, 'DE', lang);
      const spanishPin = section.locator('[data-mobile-country="ES"]');
      await spanishPin.focus();
      await page.keyboard.press('Space');
      await expectPocketCountry(section, 'ES', lang);
      await expect(spanishPin).toBeFocused();
      // The native picker reaches every country, including unpinned/off-map
      // entries, while retaining the map's scale and bounded controls.
      const crop = await section.locator('.nations-pocket-lines').getAttribute('viewBox');
      for (const entry of countries) {
        await picker.selectOption(entry.code);
        await expectPocketCountry(section, entry.code, lang);
        await expectPocketGeometry(page, section);
        await expect(section.locator('.nations-pocket-lines')).toHaveAttribute('viewBox', crop);
      }
      await picker.selectOption('IT');
      await page.setViewportSize({ width: 429, height: 812 });
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await expectPocketGeometry(page, section);
      await expectPocketDemo(section, lang);
      expect(errors).toEqual([]);
      return;
    }
    const flags = section.locator('[data-country]');
    const visibleFlags = section.locator('[data-country]:visible');
    const search = section.getByRole('searchbox');
    const result = section.locator('.nations-result');
    const route = section.locator('.nations-route-active');
    const directory = section.locator('.nations-directory');
    const passport = section.locator('.nations-passport');

    await expect(section.locator('.nations-footer')).toHaveCount(0);
    await expect(section.locator('.nations-intro')).toContainText('2026');
    if (page.viewportSize().width >= 1024) {
      const wrapped = await section.locator('#nations-title, .nations-intro').evaluateAll(elements => elements.filter(element => {
        const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        const lineCenters = [];
        let node;
        // Inter and the italic accent have different glyph boxes on the same
        // baseline. Group text fragments by line instead of using block height.
        while ((node = walker.nextNode())) {
          if (!node.textContent.trim()) continue;
          const range = document.createRange();
          range.selectNodeContents(node);
          for (const rect of range.getClientRects()) {
            const center = rect.top + rect.height / 2;
            if (!lineCenters.some(existing => Math.abs(existing - center) < lineHeight / 2)) lineCenters.push(center);
          }
        }
        return lineCenters.length !== 1;
      }).map(element => element.textContent.trim()));
      expect(wrapped, 'The desktop heading and introduction each fit on one rendered line').toEqual([]);
    }
    await expect(flags).toHaveCount(countries.length);
    await expect(visibleFlags).toHaveCount(countries.length);
    await expect(directory).toBeVisible();
    await expect(passport).toBeVisible();
    const picker = section.locator('.nations-list');
    const pickerLayout = await picker.evaluate(list => {
      const styles = getComputedStyle(list);
      const padding = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
      const row = parseFloat(styles.gridAutoRows);
      const gap = parseFloat(styles.rowGap);
      return {
        rows: (list.clientHeight - padding + gap) / (row + gap),
        overflows: list.scrollHeight > list.clientHeight,
        overflowY: styles.overflowY,
      };
    });
    expect(pickerLayout, 'Four flag rows are visible and the remaining countries scroll inside the picker').toEqual({ rows: 4, overflows: true, overflowY: 'auto' });
    expect(await section.evaluate(element => {
      const stats = element.querySelector('.nations-passport').getBoundingClientRect();
      const picker = element.querySelector('.nations-directory').getBoundingClientRect();
      return stats.bottom <= picker.top && Math.abs(stats.left - picker.left) < 1;
    }), 'Statistics stay above the picker in the same column').toBe(true);
    await expect(section.locator('.nations-expand')).toHaveCount(0);
    expect(await flags.evaluateAll(elements => elements.map(element => ({ title: element.title, name: element.textContent.trim() }))))
      .toEqual(expect.arrayContaining(countries.map(entry => ({ title: entry.name[lang], name: entry.name[lang] }))));
    await expect(section.getByRole('button', { name: country('DE').name[lang], exact: true })).toBeVisible();
    await expect(result).toHaveText('');
    await expect(result).toHaveClass(/\bsr-only\b/);
    await expect(result).toHaveAttribute('aria-live', 'polite');
    await expect(section).not.toHaveAttribute('data-total-label');
    await expect(section.locator('.nations-edition')).toHaveCount(0);
    await expect(section.locator('.nations-stats dt').last()).toHaveText(lang === 'en' ? 'Artists representing the country' : 'Artisti che rappresentano il paese');
    await expect(search).toBeVisible();
    const selectedFlag = section.locator('.nations-selected-flag img');
    await selectedFlag.scrollIntoViewIfNeeded();
    await expect(selectedFlag, 'The current country flag loads when its statistics are in view').toHaveAttribute('src', '/images/flags/es.webp');
    const flagImages = flags.locator('img');
    for (const image of [flagImages.first(), flagImages.last()]) {
      await image.scrollIntoViewIfNeeded();
      const code = await image.evaluate(element => element.closest('[data-country]').dataset.country);
      await expect.poll(() => requestedFlags.has(code), { message: 'Viewing a directory flag loads its image' }).toBe(true);
      await expect.poll(() => image.evaluate(element => element.complete && element.naturalWidth > 1)).toBe(true);
    }
    await flags.first().focus();
    await expect(flags.first()).toBeFocused();
    const nextFlag = browserName === 'webkit' && process.platform === 'darwin' ? 'Alt+Tab' : 'Tab';
    for (let index = 1; index < countries.length; index += 1) {
      await page.keyboard.press(nextFlag);
      await expect(flags.nth(index), `Country ${index + 1} remains in the keyboard sequence`).toBeFocused();
    }
    await expect(flags.last(), 'Every country remains reachable through the scrollable picker by keyboard').toBeFocused();
    expect(await picker.evaluate(list => list.scrollTop), 'Keyboard navigation scrolls to the remaining flags').toBeGreaterThan(0);
    await expect(flags.last()).toBeInViewport();
    await expectFits(page, section);

    // Localized labels, accent-free spelling, English aliases and country codes
    // should all lead to a useful result in either language.
    for (const [query, code] of [[country('DE').name[lang], 'DE'], ['turkiye', 'TR'], ['Turkey', 'TR'], ['KZ', 'KZ'], ['Kazakhstan', 'KZ']]) {
      await search.fill(query);
      await expect(visibleFlags).toHaveCount(1);
      await expect(visibleFlags).toHaveAttribute('data-country', code);
      await expect(result).toHaveText(/^1\b/);
    }

    const previousRoute = await route.getAttribute('d');
    await chooseFlagWithoutMoving(page, section, 'KZ');
    await expect(section.locator('.nations-back')).toHaveCount(0);
    await expect(section.locator('.nations-selected-name')).toHaveText(country('KZ').name[lang]);
    await expect(selectedFlag).toHaveAttribute('src', /\/flags\/kz\./);
    await expect.poll(() => selectedFlag.evaluate(image => image.complete && image.naturalWidth > 1)).toBe(true);
    await expect(route).not.toHaveAttribute('d', previousRoute);
    await expect(section.locator('[data-country][aria-pressed="true"]')).toHaveCount(1);
    await expect(section.locator('[data-country="KZ"]')).toHaveAttribute('aria-pressed', 'true');
    await expectCountryNamesFit(section);
    await expectFits(page, section);

    await expect(search).toHaveValue('Kazakhstan');
    await expect(visibleFlags).toHaveCount(1);
    await expect(visibleFlags).toHaveAttribute('data-country', 'KZ');
    await expect(result).toHaveText(/^1\b/);
    await chooseFlagWithoutMoving(page, section, 'KZ', 'keyboard');
    await expect(passport, 'The selected country statistics remain visible on repeated selection').toBeVisible();
    await expect(section.locator('.nations-selected-name')).toHaveText(country('KZ').name[lang]);

    await search.fill(country('BA').name[lang]);
    const longName = section.locator('[data-country="BA"]');
    await chooseFlagWithoutMoving(page, section, 'BA', 'keyboard');
    await expect(section.locator('.nations-selected-name')).toHaveText(country('BA').name[lang]);
    await expect(section.locator('[data-country][aria-pressed="true"]')).toHaveCount(1);
    await expect(longName).toHaveAttribute('aria-pressed', 'true');
    await expectFits(page, section);
    await expect(search).toHaveValue(country('BA').name[lang]);

    await search.fill('zz-no-country-matches');
    await expect(visibleFlags).toHaveCount(0);
    await expect(section.locator('.nations-empty')).toBeVisible();
    await section.locator('.nations-clear').click();
    await expect(search).toHaveValue('');
    await expect(search).toBeFocused();
    await expect(visibleFlags).toHaveCount(countries.length);
    await expect(section.locator('.nations-empty')).toBeHidden();
    await expect(result).toHaveText('');
    await expectFits(page, section);

    expect(errors).toEqual([]);
  });

  test(`${path}: homepage nations respect reduced motion while selection stays usable`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(path);
    const section = page.locator('#home-nations');
    if (isPhone(page)) {
      await section.scrollIntoViewIfNeeded();
      await section.locator('.nations-pocket-select').selectOption('CH');
      await expectPocketCountry(section, 'CH', lang);
      const pin = section.locator('[data-mobile-country="DE"]');
      await pin.focus();
      await page.keyboard.press('Space');
      await expectPocketCountry(section, 'DE', lang);
      await expect(pin).toHaveCSS('transition-duration', '0s');
      await expectPocketGeometry(page, section);
      expect(errors).toEqual([]);
      return;
    }
    await chooseFlagWithoutMoving(page, section, 'CH');
    await expect(section.locator('.nations-selected-name')).toHaveText(country('CH').name[lang]);
    const selectedOrigin = await countryOrigin(section, 'CH');
    const geometry = await routeGeometry(section);
    expect(geometry.origin, 'Reduced motion moves the capital marker immediately').toEqual(selectedOrigin);
    expect(geometry.coordinates.slice(0, 2), 'Reduced motion switches the route immediately').toEqual(selectedOrigin);
    await chooseFlagWithoutMoving(page, section, 'DE', 'keyboard');
    expect((await routeGeometry(section)).origin).toEqual(await countryOrigin(section, 'DE'));
    expect(errors).toEqual([]);
  });

  test(`${path}: homepage nations animate capital changes smoothly and can be interrupted`, async ({ page }) => {
    test.skip(isPhone(page), 'The phone map uses immediate country selection; the animated capital route belongs to the wider layout.');
    const errors = collectErrors(page);
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.clock.install({ time: new Date('2026-09-28T12:00:00Z') });
    await page.goto(path);
    const section = page.locator('#home-nations');
    await expect(section).toHaveClass(/\bnations-enhanced\b/);
    await page.clock.pauseAt(new Date('2026-09-28T12:01:00Z'));
    const initial = await routeGeometry(section);
    const destination = initial.coordinates.slice(-2);
    const berlin = await countryOrigin(section, 'DE');
    const bern = await countryOrigin(section, 'CH');

    // Dispatch while the animation clock is paused, so the exact state at each
    // selection and on successive frames can be compared on every browser.
    await section.locator('[data-country="DE"]').dispatchEvent('click');
    expect(await routeGeometry(section), 'Selecting another capital does not snap the curve').toEqual(initial);
    await page.clock.runFor(160);
    const firstTransition = await routeGeometry(section);
    expectMovingOrigin(firstTransition, initial.origin, berlin, destination);
    expect(firstTransition.coordinates.slice(2, 4), 'The curve bend moves with the origin').not.toEqual(initial.coordinates.slice(2, 4));

    await expect(section.locator('.nations-directory')).toBeVisible();
    expect(await routeGeometry(section), 'The visible picker does not reset an in-flight route').toEqual(firstTransition);
    await section.locator('[data-country="CH"]').dispatchEvent('click');
    expect(await routeGeometry(section), 'An interrupted transition restarts from the rendered curve').toEqual(firstTransition);
    await page.clock.runFor(160);
    expectMovingOrigin(await routeGeometry(section), firstTransition.origin, bern, destination);
    await page.clock.runFor(700);
    const completed = await routeGeometry(section);
    expect(completed.origin).toEqual(bern);
    expect(completed.coordinates.slice(0, 2)).toEqual(bern);
    expect(completed.coordinates.slice(-2)).toEqual(destination);
    await page.clock.runFor(900);
    expect(await routeGeometry(section), 'The earlier animation cannot overwrite the latest selection').toEqual(completed);

    await expect(section.locator('.nations-directory')).toBeVisible();
    await section.locator('[data-country="DE"]').dispatchEvent('click');
    await page.clock.runFor(160);
    expectMovingOrigin(await routeGeometry(section), bern, berlin, destination);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.clock.runFor(32);
    await expect.poll(async () => (await routeGeometry(section)).origin, { message: 'Enabling reduced motion completes the in-flight route' }).toEqual(berlin);
    const reduced = await routeGeometry(section);
    expect(reduced.coordinates.slice(-2)).toEqual(destination);
    await page.clock.runFor(900);
    expect(await routeGeometry(section), 'Reduced motion leaves no active transition behind').toEqual(reduced);
    expect(errors).toEqual([]);
  });

  test(`${path}: homepage nations show country statistics and keep off-map routes in the Europe view`, async ({ page, baseURL }) => {
    await fixtureStatistics(page, baseURL, path);
    const errors = collectErrors(page);
    await page.goto(path);
    const section = page.locator('#home-nations');
    await section.scrollIntoViewIfNeeded();
    if (isPhone(page)) {
      const picker = section.locator('.nations-pocket-select');
      const atlas = section.locator('.nations-pocket-base[data-nations-map-src]');
      const route = section.locator('.nations-pocket-route');
      await expect(atlas).toHaveAttribute('src', phoneAtlasSource);
      for (const [code, value] of [['CH', 0], ['DE', 12.5], ['GB', null]]) {
        await picker.selectOption(code);
        await expectPocketCountry(section, code, lang, value);
        if (value !== null) await expect(section.locator(`[data-mobile-country="${code}"] strong`)).toHaveText(percentage(value, lang));
        await expectPocketGeometry(page, section);
      }
      await expect(section.locator('.nations-pocket-status')).toContainText(lang === 'en' ? 'Outside this map view.' : 'Fuori da questa vista della mappa.');
      await expect(section.locator('[data-mobile-country="GB"]')).toBeHidden();
      await expect(route).toBeHidden();
      await expect(section.locator('.nations-pocket-lines')).toHaveAttribute('viewBox', '0 0 395 365');
      await expect(atlas).toHaveAttribute('src', phoneAtlasSource);
      await picker.selectOption('DE');
      await expectPocketCountry(section, 'DE', lang, 12.5);
      await expect(route).toBeVisible();
      await expectPocketDemo(section, lang);
      expect(errors).toEqual([]);
      return;
    }
    const stats = section.locator('.nations-stats');
    const dancers = stats.locator('[data-nations-stat="dancers"]');
    const artists = stats.locator('[data-nations-stat="artists"]');
    const map = section.locator('svg.nations-map');
    const route = section.locator('.nations-route-active');
    const origin = section.locator('.nations-origin');
    const atlas = section.locator('.nations-atlas [data-nations-map-src]');
    const pending = lang === 'en' ? 'To be confirmed' : 'Da confermare';
    await expect(stats).toHaveAttribute('aria-live', 'polite');
    const initialStats = country('ES').statistics;
    const initialPercent = String(initialStats.dancerPercent).replace('.', lang === 'it' ? ',' : '.');
    await expect(section.locator('.nations-passport')).toBeVisible();
    await chooseFlagWithoutMoving(page, section, 'ES');
    await expect(dancers).toHaveText(initialPercent + '%');
    await expect(artists).toHaveText(String(initialStats.guestArtists));

    await chooseFlagWithoutMoving(page, section, 'CH');
    await expect(dancers).toHaveText('0%');
    await expect(artists).toHaveText('0');
    await expect(origin).toBeVisible();
    await expect(route).toHaveAttribute('data-approximate', 'false');

    await chooseFlagWithoutMoving(page, section, 'DE');
    await expect(dancers).toHaveText(lang === 'en' ? '12.5%' : '12,5%');
    await expect(artists).toHaveText('2');
    await expectFits(page, section);

    const atlasBefore = await atlas.getAttribute('src');
    await chooseFlagWithoutMoving(page, section, 'GB');
    await expect(section.locator('.nations-selected-name')).toHaveText(country('GB').name[lang]);
    await expect(dancers).toHaveText(pending);
    await expect(artists).toHaveText(pending);
    await expect(route).toHaveAttribute('data-approximate', 'true');
    await expect(origin).toBeHidden();
    await expect(map).toHaveAttribute('viewBox', '0 0 800 620');
    await expect(atlas).toHaveAttribute('src', atlasBefore);
    await expect.poll(async () => (await routeGeometry(section)).coordinates.slice(0, 2), { message: 'The off-map transition reaches the supplied route origin' }).toEqual([24, 362.42]);
    const { coordinates } = await routeGeometry(section);
    expect(coordinates.slice(0, 2), 'An off-map route enters from the supplied direction').toEqual([24, 362.42]);
    expect(coordinates.slice(-2), 'Every route finishes at Milano').toEqual([319.76, 362.42]);
    for (let index = 0; index < coordinates.length; index += 2) {
      expect(coordinates[index], 'Route x coordinates stay inside the existing map').toBeGreaterThanOrEqual(24);
      expect(coordinates[index]).toBeLessThanOrEqual(776);
      expect(coordinates[index + 1], 'Route y coordinates stay inside the existing map').toBeGreaterThanOrEqual(24);
      expect(coordinates[index + 1]).toBeLessThanOrEqual(596);
    }
    await expectFits(page, section);

    await chooseFlagWithoutMoving(page, section, 'DE');
    await expect(dancers).toHaveText(lang === 'en' ? '12.5%' : '12,5%');
    await expect(artists).toHaveText('2');
    await expect(origin).toBeVisible();
    await expect(route).toHaveAttribute('data-approximate', 'false');
    expect(errors).toEqual([]);
  });

  test(`${path}: homepage nations remain readable without JavaScript`, async ({ browser, baseURL }, info) => {
    const { viewport, hasTouch, isMobile, deviceScaleFactor } = info.project.use;
    const context = await browser.newContext({ javaScriptEnabled: false, viewport, hasTouch, isMobile, deviceScaleFactor });
    try {
      await stubExternal(context, baseURL);
      const page = await context.newPage();
      const errors = collectErrors(page);
      await page.goto(baseURL + path);
      const section = page.locator('#home-nations');
      await section.scrollIntoViewIfNeeded();
      // Firefox can leave an evaluated fonts.ready promise pending when page
      // scripts are disabled, even after every requested font has loaded.
      await expect.poll(() => page.evaluate(() => document.fonts.status)).toBe('loaded');
      await expectNumbersSection(page, section, lang);
      if (isPhone(page)) {
        await expect(section.locator('.nations-pocket-controls')).toBeHidden();
        await expectPocketDemo(section, lang);
        await expectPocketGeometry(page, section);
        const pins = section.locator('.nations-pocket-pin:visible');
        for (const pin of await pins.all()) await expect(pin).toBeDisabled();
        const atlas = section.locator(`.nations-pocket-base[src="${phoneAtlasSource}"]`);
        await expect.poll(() => atlas.evaluate(image => image.complete && image.naturalWidth === 800)).toBe(true);
        const fallback = section.locator('.nations-pocket-fallback');
        await expect(fallback).toBeVisible();
        await expect(fallback).not.toHaveAttribute('open');
        await fallback.locator('summary').click();
        await expect(fallback).toHaveAttribute('open');
        await expect(fallback.locator('tbody tr')).toHaveCount(countries.length);
        expect(await fallback.locator('tbody tr').evaluateAll(rows => rows.map(row => [...row.children].map(cell => cell.textContent.trim()))))
          .toEqual(expect.arrayContaining(countries.map(entry => [entry.name[lang], percentage(entry.statistics.dancerPercent, lang)])));
        await fallback.locator('summary').click();
        await expect(fallback).not.toHaveAttribute('open');
        await expectPocketGeometry(page, section);
        expect(errors).toEqual([]);
        return;
      }
      await expect(section.locator('[data-country]:visible')).toHaveCount(countries.length);
      expect(await section.locator('[data-country] span').allTextContents()).toEqual(expect.arrayContaining(countries.map(entry => entry.name[lang])));
      await expect(section.locator('.nations-expand')).toHaveCount(0);
      await expect(section.locator('.nations-passport')).toBeHidden();
      await expect(section.locator('.nations-back')).toHaveCount(0);
      await expect(section.getByRole('searchbox')).toBeHidden();
      await expect(section.locator('.nations-statistics-note')).toHaveText(lang === 'en'
        ? 'Random demo figures for the layout preview.'
        : 'Dati dimostrativi casuali per l’anteprima del layout.');
      await expect(section.locator('.nations-statistics-note')).toBeVisible();
      await expect(section.locator('.nations-statistics-table tbody tr')).toHaveCount(countries.length);
      const flagImages = section.locator('.nations-country img');
      for (const image of [flagImages.first(), flagImages.last()]) {
        await image.scrollIntoViewIfNeeded();
        const code = await image.evaluate(element => element.closest('[data-country]').dataset.country.toLowerCase());
        await expect.poll(() => image.evaluate(element => element.currentSrc), { message: 'The no-JavaScript picture fallback selects the country flag' }).toBe(baseURL + `/images/flags/${code}.webp`);
        await expect.poll(() => image.evaluate(element => element.naturalWidth), { message: 'The no-JavaScript country flag decodes when viewed' }).toBeGreaterThan(1);
      }
      await expectFits(page, section);
      expect(errors).toEqual([]);
    } finally {
      await context.close();
    }
  });
}
