const { test } = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { resolve, join } = require('node:path');
const { spawnSync } = require('node:child_process');

const repository = resolve(__dirname, '..');

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'lighthouse-resume-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const directory of ['css', 'js', 'fonts', 'images', 'vendor', 'scripts']) mkdirSync(join(root, directory));
  for (const file of ['index.html', 'robots.txt', 'package-lock.json', 'scripts/site-server.mjs',
    'scripts/lighthouse.mjs', 'scripts/quality-results.mjs', 'scripts/site-pages.mjs',
    'scripts/site_files.py', 'scripts/generation_support.py']) writeFileSync(join(root, file), 'unchanged fixture');
  return { root, output: join(root, 'reports') };
}

// Run the actual CLI with synthetic audits and no browser, server or external requests.
function run({ root, output }, extra = [], browser = {}) {
  const configuration = { repository, root, output, extra,
    chromePath: browser.path || '/fixture/chrome', chromeVersion: browser.version ?? 'Chrome 100.0' };
  const source = `
    import { mock } from 'node:test';
    import { pathToFileURL } from 'node:url';
    import { writeFileSync } from 'node:fs';
    const configuration = ${JSON.stringify(configuration)};
    const events = [];
    const moduleURL = name => pathToFileURL(configuration.repository + '/scripts/' + name).href;
    mock.module(moduleURL('site-pages.mjs'), { namedExports: {
      root: configuration.root,
      sitePages: () => [{ file: 'index.html', path: '/', indexable: true }],
      selectPages: pages => pages,
    }});
    mock.module(moduleURL('site-server.mjs'), { namedExports: {
      startServer: async () => {
        events.push('server');
        return { address: () => ({ port: 4173 }), close: callback => callback() };
      },
    }});
    mock.module('chrome-launcher', { namedExports: {
      getChromePath: () => configuration.chromePath,
      launch: async options => {
        events.push({ launch: options.chromePath });
        return { port: 9222, kill: async () => { events.push('kill'); } };
      },
    }});
    mock.module('lighthouse', { defaultExport: async () => {
      events.push('audit');
      return { lhr: {
        categories: Object.fromEntries(['performance', 'accessibility', 'best-practices', 'seo'].map(name => [name, { score: 1 }])),
        audits: {}, lighthouseVersion: 'fixture', environment: { hostUserAgent: configuration.chromeVersion },
      }, report: ['', '<html>fixture</html>'] };
    }});
    globalThis.fetch = async url => {
      if (url !== 'http://127.0.0.1:9222/json/version') throw new Error('External requests are forbidden');
      events.push('version');
      return { ok: true, json: async () => ({ Browser: configuration.chromeVersion }) };
    };
    delete process.env.CHROME_PATH;
    process.argv = ['node', configuration.repository + '/scripts/lighthouse.mjs',
      '--profiles=phone', '--pages=index.html', '--runs=1', '--output=' + configuration.output, ...configuration.extra];
    try { await import(moduleURL('lighthouse.mjs')); }
    catch (error) { console.error(error.message); process.exitCode = 1; }
    finally { writeFileSync(configuration.root + '/events.json', JSON.stringify(events)); }
  `;
  const result = spawnSync(process.execPath, ['--experimental-test-module-mocks', '--input-type=module'], {
    cwd: repository, input: source, encoding: 'utf8', timeout: 30000,
  });
  assert.equal(result.error, undefined, result.error?.message);
  return { ...result, events: JSON.parse(readFileSync(join(root, 'events.json'), 'utf8')) };
}

test('Remote reports cannot be resumed even when local sources and the URL are unchanged', t => {
  const files = fixture(t);
  assert.equal(run(files, ['--base-url=https://fixture.invalid']).status, 0);
  const result = run(files, ['--base-url=https://fixture.invalid', '--resume']);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Cannot resume.*remote/i);
  assert.deepEqual(result.events, []);
});

test('Local resume records the chosen Chrome identity and reuses unchanged audit results', t => {
  const files = fixture(t);
  const first = run(files);
  assert.equal(first.status, 0, first.stderr);
  const manifest = JSON.parse(readFileSync(join(files.output, 'manifest.json'), 'utf8'));
  assert.deepEqual(manifest.chrome, { path: '/fixture/chrome', version: 'Chrome 100.0' });
  assert.deepEqual(first.events.find(event => event.launch), { launch: '/fixture/chrome' });
  const resumed = run(files, ['--resume']);
  assert.equal(resumed.status, 0, resumed.stderr);
  assert.equal(resumed.events.includes('audit'), false);
  assert.equal(JSON.parse(readFileSync(join(files.output, 'summary.json'), 'utf8')).complete, true);
});

test('Local resume rejects a Chrome upgrade or another executable without overwriting reports', t => {
  for (const browser of [{ version: 'Chrome 101.0' }, { path: '/fixture/other-chrome' }]) {
    const files = fixture(t);
    assert.equal(run(files).status, 0);
    const before = readFileSync(join(files.output, 'manifest.json'), 'utf8');
    const result = run(files, ['--resume'], browser);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /Cannot resume/);
    assert.equal(result.events.includes('audit'), false);
    assert.equal(readFileSync(join(files.output, 'manifest.json'), 'utf8'), before);
  }
});

test('A failed Chrome identity probe closes its browser and preserves existing reports', t => {
  const files = fixture(t);
  assert.equal(run(files).status, 0);
  const before = readFileSync(join(files.output, 'manifest.json'), 'utf8');
  const result = run(files, ['--resume'], { version: '' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Chrome did not report its version/);
  assert.equal(result.events.at(-1), 'kill');
  assert.equal(result.events.includes('audit'), false);
  assert.equal(readFileSync(join(files.output, 'manifest.json'), 'utf8'), before);
});
