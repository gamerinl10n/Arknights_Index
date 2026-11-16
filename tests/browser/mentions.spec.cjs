const {test, expect} = require('@playwright/test');

test('third-party filter reuses the form on desktop and touch widths', async ({page}) => {
  // Synthetic UI responses, never official dialogue or live-data evidence.
  await page.route('**/api/suggestions?*', route => route.fulfill({json:[
    {value:'A',label:'A',count:1},{value:'B',label:'B',count:1},{value:'C',label:'C',count:1}
  ]}));
  await page.route('**/api/search?*', route => route.fulfill({json:{total:0,items:[]}}));
  await page.goto('/?ui=en');
  await expect(page.locator('#interlocutor-field')).toBeHidden();
  await page.locator('#third-party').check();
  await expect(page.locator('#interlocutor-field')).toBeVisible();
  await page.locator('#speaker').fill('A');
  await page.locator('#target').fill('B');
  await page.locator('#interlocutor').fill('C');
  await page.locator('#interlocutor').press('ArrowDown');
  await page.locator('#interlocutor').press('Enter');
  await expect(page.locator('#interlocutor')).toHaveValue('C');
  const request = page.waitForRequest(r=>r.url().includes('/api/search?'));
  await page.locator('#submit-search').click();
  const url = new URL((await request).url());
  expect(url.searchParams.get('mention_mode')).toBe('third_party_candidate');
  expect(url.searchParams.get('interlocutor')).toBe('C');
  await expect(page.locator('#empty-state')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
  await page.reload();
  await expect(page.locator('#third-party')).toBeChecked();
  await expect(page.locator('#interlocutor')).toHaveValue('C');
  await page.locator('#reset-search').click();
  await expect(page.locator('#interlocutor-field')).toBeHidden();
  await expect(page.locator('#third-party')).not.toBeChecked();
});
