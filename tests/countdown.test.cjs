const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

function mount(file, remaining) {
  const html = readFileSync(resolve(__dirname, '..', file), 'utf8');
  const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
    .map(match => match[1]).find(value => value.includes('function updateCountdown'));
  assert.ok(script, `${file} contains its countdown`);
  const deadline = Date.parse(/new Date\("([^"]+)"\)/.exec(script)[1]);
  let now = deadline - remaining;
  let tick;
  const fields = Object.fromEntries(['days', 'hours', 'minutes', 'seconds']
    .map(name => [name, { innerText: '00' }]));
  class Clock extends Date {
    constructor(value) { super(value === undefined ? now : value); }
  }
  vm.runInNewContext(script, {
    Date: Clock,
    document: { getElementById: id => fields[id] },
    setInterval: callback => { tick = callback; },
  });
  return {
    display: () => Object.values(fields).map(field => field.innerText).join(':'),
    advance(milliseconds) { now += milliseconds; tick(); },
  };
}

for (const file of ['index.html', 'tickets.html', 'it/index.html', 'it/tickets.html']) {
  test(`${file}: countdown preserves units and updates before the deadline`, () => {
    const countdown = mount(file, (86400 + 3600 + 60 + 5) * 1000);
    assert.equal(countdown.display(), '01:01:01:05');
    countdown.advance(1000);
    assert.equal(countdown.display(), '01:01:01:04');
  });

  test(`${file}: countdown clears stale time when a suspended tab crosses expiry`, () => {
    const countdown = mount(file, 5000);
    assert.equal(countdown.display(), '00:00:00:05');
    countdown.advance(10000);
    assert.equal(countdown.display(), '00:00:00:00');
    countdown.advance(86400000);
    assert.equal(countdown.display(), '00:00:00:00');
  });

  test(`${file}: countdown is zero at expiry and on a fresh visit after expiry`, () => {
    assert.equal(mount(file, 0).display(), '00:00:00:00');
    assert.equal(mount(file, -86400000).display(), '00:00:00:00');
  });
}
