const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const script = readFileSync(resolve(__dirname, '../js/early-bird-countdown.js'), 'utf8');

function mount({ deadline, now = '2026-12-29T20:58:55Z', hidden = false,
  expiredMessage = 'Early bird has ended.', expiredHeading, expiredDescription } = {}) {
  let time = Date.parse(now);
  let nextId = 0;
  let visibility;
  const intervals = new Map();
  const fields = Object.fromEntries(['days', 'hours', 'minutes', 'seconds']
    .map(unit => [unit, { textContent: '--' }]));
  const attributes = {};
  const status = { textContent: 'Time until early bird ends.' };
  const heading = { textContent: 'Don’t miss the early bird price.' };
  const description = { textContent: 'Get a reminder before the price goes up.' };
  const root = {
    dataset: { deadline, expiredMessage, expiredHeading, expiredDescription },
    querySelector: selector => fields[/"(\w+)"/.exec(selector)[1]],
    parentElement: { querySelector: selector => ({
      '[data-countdown-status]': status, h2: heading, '#early-bird-description': description
    })[selector] },
    setAttribute: (name, value) => { attributes[name] = value; }
  };
  const document = {
    hidden,
    querySelectorAll: () => [root],
    addEventListener: (event, listener) => { assert.equal(event, 'visibilitychange'); visibility = listener; }
  };
  class Clock extends Date { static now() { return time; } }
  vm.runInNewContext(script, {
    document, Date: Clock,
    setInterval: (callback, delay) => {
      assert.equal(delay, 1000);
      intervals.set(++nextId, callback);
      return nextId;
    },
    clearInterval: id => intervals.delete(id)
  });
  return {
    attributes, status, heading, description,
    display: () => Object.values(fields).map(field => field.textContent).join(':'),
    ticking: () => intervals.size,
    advance: milliseconds => { time += milliseconds; [...intervals.values()].forEach(tick => tick()); },
    visibility: isHidden => { document.hidden = isHidden; visibility?.(); }
  };
}

test('early-bird timer uses the supplied timezone offset, not the viewer timezone', () => {
  const timer = mount({ deadline: '2026-12-30T23:00:00+01:00' });
  assert.equal(timer.display(), '01:01:01:05');
  timer.advance(1000);
  assert.equal(timer.display(), '01:01:01:04');
  assert.equal(timer.ticking(), 1);
  assert.deepEqual(timer.attributes, { role: 'timer', 'aria-live': 'off' });
  assert.equal(mount({ deadline: '2026-12-30T22:00:00Z' }).display(), '01:01:01:05');
  assert.equal(mount({ deadline: '2026-12-30T17:00:00-05:00' }).display(), '01:01:01:05');
});

test('early-bird timer stays positive during its last fraction of a second', () => {
  const timer = mount({ deadline: '2026-12-29T20:58:55.001Z' });
  assert.equal(timer.display(), '00:00:00:01');
  timer.advance(1);
  assert.equal(timer.display(), '00:00:00:00');
  assert.equal(timer.ticking(), 0);
});

for (const deadline of [undefined, '', 'not a date', '2026-12-30', '2026-12-30T23:00:00',
  '2026-02-30T23:00:00+01:00', '2026-12-30T24:00:00+01:00', '2026-12-30T23:00:00+25:00']) {
  test(`early-bird timer does not invent a deadline for ${JSON.stringify(deadline)}`, () => {
    const timer = mount({ deadline });
    assert.equal(timer.display(), '--:--:--:--');
    assert.equal(timer.ticking(), 0);
    assert.equal(timer.status.textContent, 'Time until early bird ends.');
  });
}

test('early-bird timer clamps at expiry and shows the localised message', () => {
  const timer = mount({ deadline: '2026-12-29T20:59:00Z', expiredMessage: 'La tariffa early bird è terminata.' });
  timer.advance(7000);
  assert.equal(timer.display(), '00:00:00:00');
  assert.equal(timer.status.textContent, 'La tariffa early bird è terminata.');
  assert.equal(timer.ticking(), 0);
  timer.advance(86400000);
  assert.equal(timer.display(), '00:00:00:00');
});

test('early-bird timer never starts an interval when already expired', () => {
  for (const deadline of ['2026-12-29T20:58:55Z', '2026-12-29T20:58:54Z']) {
    const timer = mount({ deadline });
    assert.equal(timer.display(), '00:00:00:00');
    assert.equal(timer.ticking(), 0);
    assert.equal(timer.status.textContent, 'Early bird has ended.');
  }
});

test('early-bird timer updates optional expiry copy only when the offer has ended', () => {
  const timer = mount({ deadline: '2026-12-29T20:59:00Z',
    expiredHeading: 'Ci vediamo a Milano.', expiredDescription: 'Scopri il congresso.' });
  assert.equal(timer.heading.textContent, 'Don’t miss the early bird price.');
  assert.equal(timer.description.textContent, 'Get a reminder before the price goes up.');
  timer.advance(5000);
  assert.equal(timer.heading.textContent, 'Ci vediamo a Milano.');
  assert.equal(timer.description.textContent, 'Scopri il congresso.');
});

test('early-bird timer leaves optional copy unchanged when no expiry copy is configured', () => {
  const timer = mount({ deadline: '2026-12-29T20:58:55Z' });
  assert.equal(timer.heading.textContent, 'Don’t miss the early bird price.');
  assert.equal(timer.description.textContent, 'Get a reminder before the price goes up.');
});

test('early-bird timer suspends while hidden and resumes from the current clock', () => {
  const timer = mount({ deadline: '2026-12-29T21:00:00Z' });
  timer.visibility(true);
  assert.equal(timer.ticking(), 0);
  timer.advance(30000);
  assert.equal(timer.display(), '00:00:01:05');
  timer.visibility(false);
  assert.equal(timer.display(), '00:00:00:35');
  assert.equal(timer.ticking(), 1);
  timer.visibility(false);
  assert.equal(timer.ticking(), 1);
});

test('early-bird timer refreshes to zero after a hidden tab crosses the deadline', () => {
  const timer = mount({ deadline: '2026-12-29T20:59:00Z', hidden: true });
  assert.equal(timer.ticking(), 0);
  timer.advance(10000);
  timer.visibility(false);
  assert.equal(timer.display(), '00:00:00:00');
  assert.equal(timer.ticking(), 0);
  assert.equal(timer.status.textContent, 'Early bird has ended.');
});
