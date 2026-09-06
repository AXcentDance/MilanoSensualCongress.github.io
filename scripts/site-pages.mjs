import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { execFileSync } from 'node:child_process';

export const root = resolve(import.meta.dirname, '..');

export function selectPages(pages, requested) {
  if (requested === undefined) return pages;
  const names = requested.split(',').map(name => name.trim());
  const matches = (page, name) => page.file === name || page.path === name;
  const unknown = names.filter(name => !pages.some(page => matches(page, name)));
  if (unknown.length) throw new Error(`Unknown audit pages: ${unknown.map(name => name || '(empty)').join(', ')}`);
  return pages.filter(page => names.some(name => matches(page, name)));
}

export function sitePages() {
  const files = JSON.parse(execFileSync('python3', [resolve(root, 'scripts/site_files.py')], { encoding: 'utf8' }));
  return files.map(file => {
    const html = readFileSync(resolve(root, file), 'utf8');
    const path = '/' + file.replace(/index\.html$/, '').replace(/\.html$/, '');
    return { file, path, indexable: !/<meta\b[^>]*\bcontent=["'][^"']*\bnoindex\b/i.test(html) };
  }).sort((a, b) => a.path.localeCompare(b.path));
}
