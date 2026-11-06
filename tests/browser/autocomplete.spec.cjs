const {test, expect} = require('@playwright/test');

async function open(page, ui = 'en') {
  const loaded = page.waitForResponse(r => r.url().includes('/api/suggestions') && r.ok());
  await page.goto(`/?ui=${ui}`);
  await loaded;
}
async function activate(locator, isMobile) {
  if (isMobile) await locator.tap();
  else await locator.click();
}
async function settleAnimations(page) {
  await page.evaluate(async () => {
    // A view transition starts after its DOM update callback; wait for paint,
    // then for actual animation completion rather than sleeping a fixed time.
    await new Promise(requestAnimationFrame);
    await new Promise(requestAnimationFrame);
    await Promise.all(document.getAnimations().map(a => a.finished.catch(() => {})));
  });
}
async function swipeUp(page) {
  const cdp = await page.context().newCDPSession(page);
  const {width, height} = page.viewportSize();
  const x = Math.floor(width / 2), start = Math.floor(height * 0.6);
  const distance = Math.min(250, Math.floor(height * 0.4));
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchStart', touchPoints: [{x, y: start, id: 1}],
  });
  for (let step = 1; step <= 10; step++) {
    await cdp.send('Input.dispatchTouchEvent', {
      type: 'touchMove', touchPoints: [{x, y: start - distance * step / 10, id: 1}],
    });
    await page.evaluate(() => new Promise(requestAnimationFrame));
  }
  await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
  await cdp.detach();
}
async function noHorizontalOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}

test('ArrowUp wraps to the final suggestion; composition keys cannot select or dismiss', async ({page}) => {
  await open(page);
  for (const id of ['speaker', 'target']) {
    const input = page.locator(`#${id}`), list = page.locator(`#${id}-options`);
    await input.focus();
    await expect(list.getByRole('option')).toHaveCount(12);
    await input.press('ArrowUp');
    await expect(input).toHaveAttribute('aria-activedescendant', `${id}-option-11`);
    const lastValue = await list.getByRole('option').last().locator('span:not(.portrait)').innerText();
    for (const key of ['Enter', 'Escape', 'ArrowUp', 'ArrowDown']) {
      for (const mode of ['composing', 'legacy']) {
        const result = await input.evaluate((element, {key, mode}) => {
          const event = new KeyboardEvent('keydown', {
            key, bubbles: true, cancelable: true,
            isComposing: mode === 'composing', keyCode: mode === 'legacy' ? 229 : 0,
          });
          element.dispatchEvent(event);
          return event.defaultPrevented;
        }, {key, mode});
        expect(result).toBe(false);
        await expect(input).toHaveValue('');
        await expect(input).toHaveAttribute('aria-activedescendant', `${id}-option-11`);
        await expect(list).toBeVisible();
      }
    }
    await input.press('Enter');
    await expect(input).toHaveValue(lastValue);
    await expect(list).toBeHidden();
    await input.fill('');
    await input.press('ArrowDown');
    await expect(input).toHaveAttribute('aria-activedescendant', `${id}-option-0`);
    await input.press('ArrowUp');
    await expect(input).toHaveAttribute('aria-activedescendant', `${id}-option-11`);
    await input.press('Escape');
    await expect(list).toBeHidden();
    await input.press('Tab');
  }
});

for (const [ui, text] of [['ko', '아미야'], ['zh', '阿米娅'], ['ja', 'アーミヤ']]) {
  test(`Chromium CDP composition and commit preserve ${ui} input`, async ({page, context}) => {
    await open(page, ui);
    const input = page.locator('#speaker');
    await input.focus();
    await input.evaluate(element => {
      window.qaComposition = [];
      for (const type of ['compositionstart', 'compositionupdate', 'compositionend', 'input']) {
        element.addEventListener(type, e => window.qaComposition.push({type: e.type, composing: e.isComposing, trusted: e.isTrusted}));
      }
    });
    const cdp = await context.newCDPSession(page);
    await cdp.send('Input.imeSetComposition', {text, selectionStart: text.length, selectionEnd: text.length});
    await expect(input).toHaveValue(text);
    await expect(input).not.toHaveAttribute('aria-activedescendant', /.+/);
    await expect(page.locator('#results-panel')).toBeHidden();
    await cdp.send('Input.insertText', {text});
    // Chromium emits the CDP commit's compositionend with isTrusted=false.
    // This is protocol-driven coverage, not a real OS input-method test.
    await expect.poll(() => page.evaluate(() => window.qaComposition.some(e => e.type === 'compositionend'))).toBe(true);
    await expect(input).toHaveValue(text);
    const events = await page.evaluate(() => window.qaComposition);
    expect(events.some(e => e.type === 'compositionstart' && e.trusted)).toBe(true);
    expect(events.some(e => e.type === 'input' && e.composing && e.trusted)).toBe(true);
    expect(events.some(e => e.type === 'compositionend')).toBe(true);
    await expect(page.locator('#results-panel')).toBeHidden();
    await expect(page.locator('#speaker-options')).toBeVisible();
    await input.press('ArrowDown');
    await input.press('Enter');
    await expect(input).toHaveValue(text);
    await expect(page.locator('#speaker-options')).toBeHidden();
    await cdp.detach();
  });
}

test('touch or pointer search, languages, context, dialogs, history and footer', async ({page, isMobile}) => {
  if (isMobile) {
    // Verify the touch driver independently before attributing failures to the app.
    const control = await page.context().newPage();
    await control.setContent('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><main style="height:3000px">Synthetic scroll-driver control</main>');
    await swipeUp(control);
    await expect.poll(() => control.evaluate(() => scrollY), {message: 'Touch driver must scroll its isolated control page'}).toBeGreaterThan(0);
    await control.close();
  }
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await open(page);
  await noHorizontalOverflow(page);
  await activate(page.locator('#speaker'), isMobile);
  await expect(page.locator('#speaker-options')).toBeVisible();
  const chosen = await page.locator('#speaker-option-0 span:not(.portrait)').innerText();
  await activate(page.locator('#speaker-option-0'), isMobile);
  await expect(page.locator('#speaker')).toHaveValue(chosen);
  await expect(page.locator('#speaker-options')).toBeHidden();
  await page.locator('#speaker').fill('');
  await page.locator('#query').fill('안녕');
  await activate(page.locator('#submit-search'), isMobile);
  await expect(page.locator('#results article').first()).toBeVisible();
  await expect(page.locator('#result-count')).toContainText(/[1-9][0-9]*/);
  await noHorizontalOverflow(page);
  for (const lang of ['ko_KR', 'zh_CN', 'ja_JP']) {
    const button = page.locator(`[data-translation-lang="${lang}"]`);
    await activate(button, isMobile);
    await expect(button).toHaveAttribute('aria-pressed', 'true');
  }
  const first = page.locator('#results article').first();
  await activate(first.locator('summary'), isMobile);
  await expect(first.locator('.context-line').first()).toBeVisible();
  await noHorizontalOverflow(page);
  await activate(first.locator('.info-button').first(), isMobile);
  await expect(page.locator('#info-dialog')).toBeVisible();
  await activate(page.locator('#info-dialog [data-close-dialog]'), isMobile);
  await expect(page.locator('#info-dialog')).toBeHidden();
  for (let repeat = 0; repeat < 2; repeat++) {
    await activate(page.locator('#help-button'), isMobile);
    await expect(page.locator('#help-dialog')).toBeVisible();
    await noHorizontalOverflow(page);
    await activate(page.locator('#help-dialog [data-close-dialog]'), isMobile);
    await expect(page.locator('#help-dialog')).toBeHidden();
  }
  await activate(page.locator('#themeButton'), isMobile);
  await expect(page.locator('#themeButton')).toHaveAttribute('aria-pressed', 'true');
  await page.goBack();
  await expect(page.locator('#results-panel')).toBeHidden();
  await settleAnimations(page);
  await page.goForward();
  await expect(page.locator('#results article').first()).toBeVisible();
  await settleAnimations(page);
  if (isMobile) {
    await page.evaluate(() => scrollTo(0, 0));
    await swipeUp(page);
    await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(0);
  }
  await page.locator('footer').scrollIntoViewIfNeeded();
  await expect(page.locator('footer')).toBeVisible();
  await noHorizontalOverflow(page);
  expect(errors).toEqual([]);
});
