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
  await expect(page.locator('#target')).toHaveAttribute('placeholder','Character mentioned (e.g. Mon3tr)');
  await expect(page.locator('#interlocutor')).toHaveAttribute('placeholder','Conversation partner · optional (e.g. Doctor)');
  if(page.viewportSize().width > 640) {
    const filter = await page.locator('.mention-toggle').boundingBox();
    const spoilers = await page.locator('.spoiler-toggle').boundingBox();
    const partner = await page.locator('#interlocutor').boundingBox();
    const form = await page.locator('#search').boundingBox();
    expect(Math.abs(filter.y-spoilers.y)).toBeLessThan(4);
    expect(partner.y).toBeGreaterThan(filter.y+filter.height);
    expect(partner.width).toBeLessThan(form.width*.6);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
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

test('choice labels and empty-context recovery preserve the original search', async ({page}) => {
  const item = {story:'ko_KR:synthetic',lang:'ko_KR',path:'synthetic',ordinal:2,speaker:'',text:'Synthetic option one\nSynthetic option two',branch:'decision@2:(options="synthetic")',revision:'synthetic',source:'synthetic'};
  await page.route('**/api/suggestions?*', route => route.fulfill({json:[]}));
  await page.route('**/api/search?*', route => {
    const params = new URL(route.request().url()).searchParams;
    return route.fulfill({json:params.get('interlocutor')?{total:0,items:[]}:{total:1,items:[item]}});
  });
  await page.route('**/api/context?*', route => route.fulfill({json:{items:[item,{...item,ordinal:3,text:'Synthetic unnamed narration'}],has_more:false}}));
  await page.goto('/search?ui=en&speaker=Kaltsit&target=M3&q=synthetic&mention_mode=third_party_candidate&interlocutor=Doctor');
  await page.locator('#relax-interlocutor').click();
  await page.locator('#results .card-heading h2').waitFor();
  const url = new URL(page.url());
  expect(url.searchParams.get('speaker')).toBe('Kaltsit');
  expect(url.searchParams.get('target')).toBe('M3');
  expect(url.searchParams.get('q')).toBe('synthetic');
  expect(url.searchParams.get('interlocutor')).toBe('');
  expect(url.searchParams.get('mention_mode')).toBe('third_party_candidate');
  await expect(page.locator('#results .card-heading h2')).toHaveText('Choice · speaker unverified');
  await page.locator('#results details summary').click();
  await expect(page.locator('.context-heading strong').first()).toHaveText('Choice · speaker unverified');
  await expect(page.locator('.context-heading strong').last()).toHaveText('Unnamed');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1)).toBe(true);
  await page.goBack();
  await expect(page.locator('#interlocutor')).toHaveValue('Doctor');
  await expect(page.locator('#relax-interlocutor')).toBeVisible();
});
