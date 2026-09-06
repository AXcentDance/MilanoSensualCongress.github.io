const { test } = require('node:test');
const assert = require('node:assert/strict');

const result = (performance, other = {}) => ({ file: 'index.html', profile: 'phone', indexable: true,
  scores: { performance, accessibility: 100, 'best-practices': 100, seo: 100 }, ...other });

test('A misspelled requested page fails instead of silently reducing audit coverage', async () => {
  const { selectPages } = await import('../scripts/site-pages.mjs');
  const pages = [{ file: 'hotel.html', path: '/hotel' }, { file: 'it/hotel.html', path: '/it/hotel' }];
  assert.deepEqual(selectPages(pages), pages);
  assert.deepEqual(selectPages(pages, 'hotel.html, /it/hotel'), pages);
  assert.throws(() => selectPages(pages, 'hotel.html,it/hotell.html'), /Unknown audit pages: it\/hotell.html/);
  assert.throws(() => selectPages(pages, ''), /Unknown audit pages: \(empty\)/);
});

test('Lighthouse gate uses the median and preserves a bad run in the range', async () => {
  const { aggregateResults, belowTarget } = await import('../scripts/quality-results.mjs');
  const [summary] = aggregateResults([result(91), result(94), result(100)]);
  assert.equal(summary.scores.performance, 94);
  assert.deepEqual(summary.ranges.performance, [91, 100]);
  assert.equal(belowTarget(summary), true);
});

test('A missing or errored Lighthouse category cannot pass', async () => {
  const { aggregateResults, belowTarget } = await import('../scripts/quality-results.mjs');
  assert.equal(belowTarget(aggregateResults([result(100), result(null), result(100)])[0]), true);
  assert.equal(belowTarget(result(100, { runtimeError: { code: 'NO_FCP' } })), true);
});

test('An intermittent integration error cannot be averaged into a pass', async () => {
  const { aggregateResults, belowTarget } = await import('../scripts/quality-results.mjs');
  const failed = result(99);
  failed.scores['best-practices'] = 92;
  const [summary] = aggregateResults([result(99), failed, result(99)]);
  assert.equal(summary.scores['best-practices'], 92);
  assert.equal(belowTarget(summary), true);
});

test('Intentional noindex only exempts SEO, preserving all other quality targets', async () => {
  const { belowTarget } = await import('../scripts/quality-results.mjs');
  const errorPage = result(100, { file: '404.html', indexable: false });
  errorPage.scores.seo = 70;
  assert.equal(belowTarget(errorPage), false);
  errorPage.scores.accessibility = 90;
  assert.equal(belowTarget(errorPage), true);
});
