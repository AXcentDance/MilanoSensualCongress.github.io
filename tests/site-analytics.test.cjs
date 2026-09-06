const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const script = readFileSync(resolve(__dirname, '../js/site-analytics.js'), 'utf8');

function mount({ prerendering = false, complete = false, idleCallback = true,
  language = 'en', url = 'https://milanosensualcongress.com/' } = {}) {
  const events = {}, requests = [], idle = [];
  const listen = (name, callback) => { (events[name] ||= []).push(callback); };
  const document = {
    prerendering, readyState: complete ? 'complete' : 'interactive',
    documentElement: { lang: language },
    referrer: 'https://www.google.com/search?q=bachata&email=private@example.com',
    addEventListener: listen,
    createElement: tag => { assert.equal(tag, 'script'); return {}; },
    head: { appendChild: node => requests.push(node.src) }
  };
  const context = {
    document, location: new URL(url), URL, Date,
    addEventListener: listen,
    setTimeout: callback => { idle.push(callback); }
  };
  if (idleCallback) context.requestIdleCallback = callback => { idle.push(callback); };
  context.window = context;
  vm.runInNewContext(script, context);
  const fire = (name, event = {}) => (events[name] || []).forEach(callback => callback(event));
  return {
    context, document, requests, fire,
    hasIdle: () => idle.length > 0,
    idle: () => { while (idle.length) idle.shift()(); },
    load: () => { document.readyState = 'complete'; fire('load'); },
    commands: () => Array.from(context.dataLayer, args => Array.from(args)),
    tracks: () => Array.from(context.fbq?.queue || [], args => Array.from(args)),
    clickTicket(href = 'https://lasalsadelbaile.com/MSC2026') {
      fire('click', { target: { closest: () => ({ href }) } });
    },
    reminder: source => context.mscAnalytics.trackReminder(source)
  };
}

for (const idleCallback of [true, false]) {
  test('tracking starts automatically after load and idle, exactly once: ' + idleCallback, () => {
    const page = mount({ idleCallback });
    assert.equal(page.requests.length, 0);
    assert.equal(page.hasIdle(), false);
    page.load();
    assert.equal(page.requests.length, 0);
    page.idle();
    assert.equal(page.requests.length, 2);
    assert.ok(page.requests.some(url => url === 'https://www.googletagmanager.com/gtag/js?id=G-YR3PM2QG8J'));
    page.context.startMetaPixel();
    page.fire('load');
    page.idle();
    assert.equal(page.requests.length, 2);
    assert.equal(page.commands().filter(args => args[0] === 'config').length, 1);
    assert.equal(page.tracks().filter(args => args[1] === 'PageView').length, 1);
  });
}

test('prerendering suppresses requests and conversions until the page is activated', () => {
  const page = mount({ prerendering: true, complete: true });
  page.context.startMetaPixel();
  page.clickTicket();
  page.reminder('Home - EN');
  assert.equal(page.requests.length, 0);
  assert.equal(page.hasIdle(), false);
  page.document.prerendering = false;
  page.fire('prerenderingchange');
  assert.equal(page.requests.length, 0);
  page.idle();
  assert.equal(page.requests.length, 2);
  assert.equal(page.commands().filter(args => args[0] === 'event').length, 0);
});

test('activation before window load still waits for rendering', () => {
  const page = mount({ prerendering: true });
  page.document.prerendering = false;
  page.fire('prerenderingchange');
  assert.equal(page.hasIdle(), false);
  page.load();
  page.idle();
  assert.equal(page.requests.length, 2);
});

test('ticket events only identify the actual destination and never report a purchase', () => {
  const page = mount({ complete: true });
  page.clickTicket('https://lasalsadelbaile.com.evil.example/MSC2026');
  page.clickTicket('https://example.com/?next=lasalsadelbaile.com/MSC2026');
  page.fire('click', { target: {} });
  assert.equal(page.requests.length, 0);
  page.clickTicket('https://lasalsadelbaile.com/MSC2026?email=private@example.com');
  page.idle();
  const events = page.commands().filter(args => args[0] === 'event');
  assert.equal(events.length, 1);
  assert.equal(events[0][1], 'ticket_click');
  assert.equal(events[0][2].link_url, 'https://lasalsadelbaile.com/MSC2026');
  assert.equal(page.requests.length, 2);
  assert.equal(page.tracks().filter(args => args[1] === 'InitiateCheckout').length, 1);
  assert.equal(page.commands().filter(args => args[0] === 'config').length, 1);
});

test('reminder conversions send the known form source without contact details', () => {
  const page = mount({ complete: true });
  page.reminder('private@example.com');
  assert.equal(page.requests.length, 0);
  page.reminder('Home - EN');
  const event = page.commands().find(args => args[0] === 'event');
  assert.equal(event[1], 'generate_lead');
  assert.deepEqual(Object.keys(event[2]).sort(), ['form_id', 'lead_type', 'source']);
  assert.equal(event[2].source, 'Home - EN');
  assert.equal(JSON.stringify(page.commands()).includes('private@example.com'), false);
  assert.equal(page.tracks().filter(args => args[1] === 'Lead').length, 1);
});

for (const language of ['en', 'it']) {
  test(language + ': page reporting preserves UTM campaigns and removes other query strings', () => {
    const path = language === 'it' ? '/it/' : '/';
    const page = mount({
      complete: true, language,
      url: 'https://milanosensualcongress.com' + path + '?utm_source=instagram&utm_campaign=congress&email=private@example.com#secret'
    });
    page.idle();
    const config = page.commands().find(args => args[0] === 'config');
    assert.equal(config[1], 'G-YR3PM2QG8J');
    assert.equal(config[2].page_location, 'https://milanosensualcongress.com' + path + '?utm_source=instagram&utm_campaign=congress');
    assert.equal(config[2].page_referrer, 'https://www.google.com/search');
    assert.equal(config[2].content_group, language === 'it' ? 'Italian' : 'English');
    assert.equal(config[2].allow_google_signals, false);
    assert.equal(config[2].allow_ad_personalization_signals, false);
    assert.equal('debug_mode' in config[2], false);
  });
}

test('local previews only send analytics when debug mode is explicitly requested', () => {
  const page = mount({ complete: true, url: 'http://localhost:8765/' });
  page.idle();
  page.clickTicket();
  assert.equal(page.requests.length, 0);
  const debug = mount({ complete: true, url: 'http://localhost:8765/?analytics_debug=1' });
  debug.idle();
  assert.equal(debug.requests.length, 1);
  assert.equal(debug.commands().find(args => args[0] === 'config')[2].debug_mode, true);
});
