const {test,expect}=require('@playwright/test');

test('new-version notice stays content-sized and can be dismissed',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.route('**/version.json?*',route=>route.fulfill({json:{version:'synthetic-new-version'}}));
 await page.goto('/?ui=ko');
 const banner=page.locator('.site-update');await expect(banner).toBeVisible();
 const box=await banner.boundingBox();
 expect(box.height).toBeLessThan(160);
 expect(Math.abs(box.y+box.height/2-page.viewportSize().height/2)).toBeLessThan(4);
 expect(box.width).toBeLessThanOrEqual(page.viewportSize().width-18);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await banner.locator('.site-update-later').click();await expect(banner).toBeHidden();
});

test('missing mentioned person focuses that field while dialogue remains optional',async({page})=>{
 await page.route('**/api/suggestions?*',route=>route.fulfill({json:[]}));
 await page.route('**/api/search?*',route=>route.fulfill({json:{total:0,items:[]}}));
 await page.goto('/?ui=ko');
 await page.locator('#speaker').fill('아미야');await page.locator('#third-party').check();
 await page.locator('#interlocutor').fill('켈시');await page.locator('#submit-search').click();
 await expect(page.locator('#target')).toBeFocused();
 expect(await page.locator('#query').evaluate(el=>el.validationMessage)).toBe('');
 await page.locator('#target').fill('Mon3tr');
 await page.locator('#submit-search').click();
 await expect(page).toHaveURL(/\/search\?/);
 await expect(page.locator('#query')).toHaveValue('');
});
