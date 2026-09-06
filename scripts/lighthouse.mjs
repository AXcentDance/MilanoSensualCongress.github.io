// Serial, unmodified Lighthouse audits. No third-party requests or audits are hidden.
import lighthouse from 'lighthouse';
import { launch } from 'chrome-launcher';
import { mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { parseArgs } from 'node:util';
import { createHash } from 'node:crypto';
import { platform, arch } from 'node:os';
import desktopConfig from 'lighthouse/core/config/desktop-config.js';
import { root, sitePages } from './site-pages.mjs';
import { startServer } from './site-server.mjs';
import { categories, belowTarget, aggregateResults } from './quality-results.mjs';

const { values: args } = parseArgs({ options: {
  'base-url': { type: 'string' }, profiles: { type: 'string', default: 'phone,tablet,desktop' },
  pages: { type: 'string' }, output: { type: 'string', default: '.quality/lighthouse' },
  runs: { type: 'string', default: 'auto' }, resume: { type: 'boolean', default: false },
} });
const profiles = {
  phone: {},
  tablet: { screenEmulation: { mobile: true, width: 768, height: 1024, deviceScaleFactor: 2, disabled: false } },
  desktop: { ...desktopConfig.settings, screenEmulation: { ...desktopConfig.settings.screenEmulation, width: 1440, height: 900 } },
};
const selected = args.profiles.split(',');
if (selected.some(p => !(p in profiles))) throw new Error('Profiles: phone, tablet, desktop');
const pages = sitePages().filter(p => !args.pages || args.pages.split(',').includes(p.file) || args.pages.split(',').includes(p.path));
if (!pages.length) throw new Error('No matching pages');
const automatic = args.runs === 'auto';
const runs = automatic ? 1 : Number(args.runs);
if (!Number.isInteger(runs) || runs < 1) throw new Error('--runs must be a positive integer');
mkdirSync(args.output, { recursive: true });
function sourceFingerprint() {
  const hash = createHash('sha256');
  function hashFile(file) { hash.update(file); hash.update(readFileSync(resolve(root, file))); }
  function hashDirectory(directory) {
    for (const entry of readdirSync(resolve(root, directory), { withFileTypes: true }).sort((a,b) => a.name.localeCompare(b.name))) {
      if (entry.name.startsWith('.')) continue;
      const file = directory + '/' + entry.name;
      if (entry.isDirectory()) hashDirectory(file); else hashFile(file);
    }
  }
  for (const page of sitePages()) hashFile(page.file);
  for (const directory of ['css', 'js', 'fonts', 'images', 'vendor']) hashDirectory(directory);
  for (const file of ['robots.txt', 'package-lock.json', 'scripts/site-server.mjs', 'scripts/lighthouse.mjs', 'scripts/quality-results.mjs', 'scripts/site-pages.mjs', 'scripts/site_files.py']) hashFile(file);
  return hash.digest('hex');
}
const manifest = { sourceHash: sourceFingerprint(), profiles: Object.fromEntries(selected.map(p => [p, profiles[p]])),
  pages: pages.map(p => p.file), runs: args.runs, base: args['base-url'] || 'local preview', node: process.version, platform: platform(), arch: arch() };
const manifestPath = resolve(args.output, 'manifest.json');
if (args.resume && (!existsSync(manifestPath) || JSON.stringify(JSON.parse(readFileSync(manifestPath, 'utf8'))) !== JSON.stringify(manifest))) {
  throw new Error('Cannot resume: source or audit configuration changed. Use a new output directory.');
}
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
const server = args['base-url'] ? null : await startServer(0);
const base = args['base-url'] || `http://127.0.0.1:${server.address().port}`;
let chrome;
const results = [];
async function cleanup() {
  if (chrome) { await chrome.kill(); chrome = null; }
  if (server) await new Promise(accept => server.close(accept));
}
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => { await cleanup(); process.exit(130); });
try {
  for (const page of pages) for (const profile of selected) {
   let count = runs;
   for (let run = 1; run <= count; run++) {
    const name = `${page.file.replaceAll('/', '__').replace('.html', '')}.${profile}.${run}`;
    const destination = resolve(args.output, name + '.json');
    let lhr;
    if (args.resume && existsSync(destination)) lhr = JSON.parse(readFileSync(destination, 'utf8'));
    else {
      console.log(`Auditing ${page.path} [${profile} ${run}/${count}]`);
      chrome = await launch({ chromePath: process.env.CHROME_PATH, chromeFlags: ['--headless=new', '--no-first-run'], logLevel: 'silent' });
      let result;
      try {
        result = await lighthouse(new URL(page.path, base).href, {
          port: chrome.port, logLevel: 'error', output: ['json', 'html'],
          onlyCategories: categories, ...profiles[profile],
        });
      } finally { await chrome.kill(); chrome = null; }
      lhr = result.lhr;
      writeFileSync(destination, JSON.stringify(lhr));
      writeFileSync(resolve(args.output, name + '.html'), result.report[1]);
    }
    const scores = Object.fromEntries(categories.map(c => [c, Number.isFinite(lhr.categories?.[c]?.score) ? Math.round(lhr.categories[c].score * 100) : null]));
    const failedAudits = Object.values(lhr.audits).filter(a => a.score !== null && a.score < 1).map(a => ({ id: a.id, title: a.title, score: a.score, displayValue: a.displayValue }));
    const item = { ...page, profile, run, scores, lcp: lhr.audits['largest-contentful-paint']?.numericValue, cls: lhr.audits['cumulative-layout-shift']?.numericValue, tbt: lhr.audits['total-blocking-time']?.numericValue, lighthouseVersion: lhr.lighthouseVersion, browser: lhr.environment?.hostUserAgent, fetchTime: lhr.fetchTime, finalUrl: lhr.finalDisplayedUrl, runtimeError: lhr.runtimeError, failedAudits, report: name + '.html' };
    results.push(item);
    if (automatic && run === 1 && (belowTarget(item) || scores.performance < 97)) count = 3;
    writeFileSync(resolve(args.output, 'summary.json'), JSON.stringify({ base, manifest, complete: false, results, pages: aggregateResults(results) }, null, 2));
    console.log(`${page.file} ${profile}: ${categories.map(c => `${c}=${scores[c]}`).join(' ')} LCP=${Math.round(item.lcp)}ms CLS=${item.cls?.toFixed(3)}`);
   }
  }
} finally {
  await cleanup();
}
if (sourceFingerprint() !== manifest.sourceHash) {
  throw new Error('Sources changed during the audit. Reports are incomplete; run again against the final files.');
}
// Keep the intentional noindex page's raw SEO score visible; it is not an indexability target.
const summaries = aggregateResults(results);
const failures = summaries.filter(belowTarget);
writeFileSync(resolve(args.output, 'summary.json'), JSON.stringify({ base, manifest, complete: true, results, pages: summaries }, null, 2));
console.log(`${results.length} reports for ${summaries.length} page/profile pairs; ${failures.length} below target. Raw reports: ${resolve(args.output)}`);
process.exitCode = failures.length ? 1 : 0;
