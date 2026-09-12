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

export function sitePages(baseRoot = root) {
  return JSON.parse(execFileSync('python3', [resolve(root, 'scripts/site_files.py'),
    '--manifest', '--root', baseRoot], { encoding: 'utf8', stdio: 'pipe' }))
    .sort((a, b) => a.path.localeCompare(b.path));
}
