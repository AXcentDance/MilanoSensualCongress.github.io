const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, mkdirSync, writeFileSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join, dirname } = require('node:path');

function fixture(t, pages) {
  const root = mkdtempSync(join(tmpdir(), 'congress-page-policy-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const [name, head] of Object.entries(pages)) {
    const file = join(root, name);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, `<html><head>${head}</head><body>Congress information</body></html>`);
  }
  return root;
}

test('Browser discovery includes utility HTML and uses the shared indexing policy', async t => {
  const { sitePages } = await import('../scripts/site-pages.mjs');
  const root = fixture(t, {
    'index.html': '<meta name="description" content="A guide mentioning noindex">',
    '404.html': '<meta content="index" name="robots"><meta content="NOINDEX" name="ROBOTS">',
    'it/new/index.html': '',
    'news/myindex.html': '',
    'output/draft.html': '',
    '.agent/private.html': '',
    '.draft.html': '',
  });
  const pages = sitePages(root);
  assert.deepEqual(pages, [
    { file: 'index.html', path: '/', indexable: true },
    { file: '404.html', path: '/404', indexable: false },
    { file: 'it/new/index.html', path: '/it/new/', indexable: true },
    { file: 'news/myindex.html', path: '/news/myindex', indexable: true },
  ]);
  assert.equal(pages.filter(page => page.indexable).length, 3);
});

test('Browser discovery stops on accidental ticket noindex instead of dropping coverage', async t => {
  const { sitePages } = await import('../scripts/site-pages.mjs');
  const root = fixture(t, { 'tickets.html': '<meta name="robots" content="noindex">' });
  assert.throws(() => sitePages(root), /tickets.html: unexpected noindex on public page/);
});

test('Browser discovery rejects a utility page that loses its noindex directive', async t => {
  const { sitePages } = await import('../scripts/site-pages.mjs');
  const root = fixture(t, { '404.html': '<meta name="robots" content="index">' });
  assert.throws(() => sitePages(root), /approved nonindexed page must retain a head robots noindex/);
});
