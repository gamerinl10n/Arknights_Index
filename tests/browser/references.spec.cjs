const {test,expect}=require('@playwright/test');
test('target-first reference research on all viewports preserves empty speaker and auditable source',async({page})=>{
 const item={story:'synthetic',lang:'ko_KR',path:'synthetic',ordinal:2,speaker:'A',text:'저 녀석을 보라.',branch:'main',revision:'fixture',source:'fixture',references:[{status:'candidate',basis:'nearby_turn',lang:'ko_KR',expressions:['저 녀석'],anchor:{story:'synthetic',lang:'ko_KR',path:'synthetic',ordinal:1,speaker:'아미야',text:'Synthetic target turn',branch:'main',revision:'fixture',source:'fixture'}}]};
 await page.route('**/api/suggestions?*',r=>r.fulfill({json:[]}));
 await page.route('**/api/search?*',r=>r.fulfill({json:{total:1,items:[item]}}));
 await page.goto('/?ui=ko');
 await page.locator('#third-party').selectOption('reference_candidates');
 await expect(page.locator('#interlocutor-field')).toBeHidden();await expect(page.locator('#swap')).toBeHidden();
 await page.locator('#target').fill('아미야');
 const target=await page.locator('#target').boundingBox(),speaker=await page.locator('#speaker').boundingBox();
 if(page.viewportSize().width<=640)expect(target.y).toBeLessThan(speaker.y);else expect(target.x).toBeLessThan(speaker.x);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 const pending=page.waitForRequest(r=>r.url().includes('/api/search?'));await page.locator('#submit-search').click();
 const url=new URL((await pending).url());expect(url.searchParams.get('speaker')).toBe('');expect(url.searchParams.get('q')).toBe('');expect(url.searchParams.get('mention_mode')).toBe('reference_candidates');
 await expect(page.locator('.reference-highlight')).toHaveText('저 녀석');await expect(page.locator('.reference-evidence')).toContainText('지칭 표현 후보');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.locator('.reference-evidence .info-button').click();await expect(page.locator('#info-content')).toContainText('fixture');await page.keyboard.press('Escape');
 await page.reload();await expect(page.locator('#third-party')).toHaveValue('reference_candidates');await expect(page.locator('#target')).toHaveValue('아미야');
});
