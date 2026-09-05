const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const script = readFileSync(resolve(__dirname, '../js/site-analytics.js'), 'utf8');

function mount({ prerendering = false, complete = false, idleCallback = true } = {}) {
  const events = {}, requests = [], tracks = [];
  let idle;
  const document = {
    prerendering,
    readyState: complete ? 'complete' : 'loading',
    addEventListener: (name, callback) => { events[name] = callback; },
    createElement: () => ({}),
    getElementsByTagName: () => [{ parentNode: { insertBefore: node => requests.push(node.src) } }]
  };
  const context = {
    document,
    addEventListener: (name, callback) => { events[name] = callback; },
    setTimeout: callback => { idle = callback; },
  };
  if (idleCallback) context.requestIdleCallback = callback => { idle = callback; };
  context.window = context;
  vm.runInNewContext(script, context);
  return {
    document, requests, events,
    start: () => context.startMetaPixel(),
    idle: () => idle(),
    hasIdle: () => !!idle,
    tracks: () => context.fbq?.queue || tracks,
    click: isTicket => events.click({ target: { closest: () => isTicket ? {} : null } })
  };
}

for (const idleCallback of [true, false]) {
  test(`pixel waits for load and idle (idle callback: ${idleCallback})`, () => {
    const page = mount({ idleCallback });
    assert.equal(page.requests.length, 0);
    assert.equal(page.hasIdle(), false);
    page.events.load();
    assert.equal(page.requests.length, 0);
    page.idle();
    assert.equal(page.requests.length, 1);
    assert.deepEqual(Array.from(page.tracks(), args => Array.from(args)), [
      ['init', '2083020305980459'], ['track', 'PageView']
    ]);
    page.start();
    assert.equal(page.requests.length, 1);
    assert.equal(page.tracks().length, 2);
  });
}

test('prerendering neither loads the pixel nor records a page view', () => {
  const page = mount({ prerendering: true, complete: true });
  page.start();
  assert.equal(page.requests.length, 0);
  assert.equal(page.hasIdle(), false);
  page.document.prerendering = false;
  page.events.prerenderingchange();
  assert.equal(page.requests.length, 0);
  page.idle();
  assert.equal(page.requests.length, 1);
});

test('checkout before idle starts the pixel once and records the checkout', () => {
  const page = mount({ complete: true });
  page.click(false);
  assert.equal(page.requests.length, 0);
  page.click(true);
  assert.deepEqual(Array.from(page.tracks(), args => Array.from(args)), [
    ['init', '2083020305980459'], ['track', 'PageView'], ['track', 'InitiateCheckout']
  ]);
  page.idle();
  assert.equal(page.requests.length, 1);
  assert.equal(page.tracks().length, 3);
});
