import { defineConfig } from '@playwright/test';

const sizes = { phone: { width: 375, height: 812 }, tablet: { width: 768, height: 1024 }, desktop: { width: 1440, height: 900 } };
export default defineConfig({
  testDir: './tests/browser',
  outputDir: '.quality/browser-artifacts',
  timeout: 30000,
  retries: 0,
  workers: 3,
  reporter: [['list'], ['json', { outputFile: '.quality/browser-results.json' }]],
  use: { baseURL: 'http://127.0.0.1:4173', screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  projects: ['chromium', 'firefox', 'webkit'].flatMap(browserName => Object.entries(sizes).map(([size, viewport]) => ({
    name: `${browserName}-${size}`, use: { browserName, viewport, hasTouch: size !== 'desktop', isMobile: browserName !== 'firefox' && size !== 'desktop', deviceScaleFactor: size === 'desktop' ? 1 : 2 },
  }))),
  webServer: { command: 'node scripts/site-server.mjs', url: 'http://127.0.0.1:4173', reuseExistingServer: !process.env.CI },
});
