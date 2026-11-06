const {defineConfig} = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  expect: {timeout: 10000},
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {
    baseURL: 'http://127.0.0.1:8052',
    browserName: 'chromium',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {name: 'desktop', use: {viewport: {width: 1280, height: 800}}},
    ...[[320, 568], [375, 667], [390, 844], [430, 932], [844, 390]].map(([width, height]) => ({
      name: `touch-${width}x${height}`,
      use: {viewport: {width, height}, isMobile: true, hasTouch: true, deviceScaleFactor: 1},
    })),
  ],
  webServer: {
    command: 'python app.py --port 8052',
    env: {VERCEL: '1'},
    url: 'http://127.0.0.1:8052/api/status',
    timeout: 60000,
    reuseExistingServer: false,
  },
});
