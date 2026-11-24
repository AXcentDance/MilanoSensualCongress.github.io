import {test, expect} from '@playwright/test';

const endpoint = 'https://script.google.com/macros/s/**/exec';
test.beforeEach(async ({context}) => {
  // Never submit test data to Google or the congress team.
  await context.route('https://**/*', route => route.abort());
});

async function requiredFields(page) {
  for (const [name, value] of Object.entries({name:'Alex & Test',phone:'+00123',country:'Italy',city:'Milano'}))
    await page.locator('#promoter-' + name).fill(value);
}

for (const path of ['/promoters','/it/promoters']) {
  const italian = path.startsWith('/it/');
  test(path + ': application includes all fields and confirms a matching receipt', async ({page}, testInfo) => {
    let request;
    await page.route(endpoint, route => {
      expect(route.request().method()).toBe('POST');
      request = Object.fromEntries(new URLSearchParams(route.request().postData()));
      return route.fulfill({json:{ok:true,submissionId:request.submissionId}});
    });
    await page.goto(path);
    await expect(page.locator('.promoters-hero-logo')).toBeVisible();
    await expect(page.locator('.promoters-join')).toHaveAttribute('href','#ambassador-application');
    await expect(page.locator('#promoter-email, #promoter-social, option[value="dancer"]')).toHaveCount(0);
    await expect(page.locator('#promoter-phone')).toHaveJSProperty('required',true);
    await expect(page.locator('#promoter-message')).toHaveJSProperty('required',false);
    await page.evaluate(() => document.fonts.ready);
    const bounds = await page.locator('.promoters-application-fields > div').evaluateAll(fields =>
      fields.map(field => { const r = field.getBoundingClientRect(); return {top:r.top,left:r.left,right:r.right}; }));
    expect(bounds).toHaveLength(6);
    const width = page.viewportSize().width;
    bounds.forEach((r, i) => {
      expect(r.right).toBeLessThanOrEqual(width);
      if (!i) return;
      if (width > 600 && i % 2) expect(r.top).toBeCloseTo(bounds[i-1].top,0);
      else expect(r.top).toBeGreaterThan(bounds[i-1].top);
    });
    await page.locator('#ambassador-application').screenshot({path:testInfo.outputPath('application-form.png'),animations:'disabled'});
    await requiredFields(page);
    await page.locator('#promoter-role').selectOption('teacher');
    await page.locator('#promoter-community').fill('Dance School');
    await page.locator('#promoter-message').fill('Local classes.\nSchool events.');
    const submit = page.locator('.promoters-application-submit');
    await submit.click();
    await expect(page.getByRole('status')).toContainText(italian ? 'Abbiamo ricevuto' : 'We received');
    await expect(submit).toBeDisabled();
    expect(request).toEqual({name:'Alex & Test',phone:'+00123',country:'Italy',city:'Milano',role:'teacher',
      community:'Dance School',message:'Local classes.\nSchool events.',website:'',language:italian ? 'it':'en',
      response:'json',submissionId:expect.stringMatching(/^[0-9a-f-]{36}$/)});
  });

  test(path + ': empty phone blocks submission and an unconfirmed receipt can be retried', async ({page}) => {
    const posts = [];
    await page.route(endpoint, route => {
      const data = new URLSearchParams(route.request().postData());
      posts.push(data);
      return route.fulfill({json:{ok:true,submissionId:posts.length === 1 ? 'different' : data.get('submissionId')}});
    });
    await page.goto(path);
    await requiredFields(page);
    const phone = page.locator('#promoter-phone');
    const submit = page.locator('.promoters-application-submit');
    await phone.fill('');
    await submit.click();
    expect(await phone.evaluate(input => input.validity.valueMissing)).toBe(true);
    await phone.fill('   ');
    await submit.click();
    expect(await phone.evaluate(input => input.validity.customError)).toBe(true);
    expect(posts).toHaveLength(0);
    await phone.fill('+00123');
    await submit.click();
    await expect(page.getByRole('status')).toContainText(italian ? 'Invio non confermato' : 'could not confirm');
    await expect(phone).toHaveValue('+00123');
    await submit.click();
    await expect(submit).toBeDisabled();
    expect(posts).toHaveLength(2);
    expect(posts[1].get('submissionId')).toBe(posts[0].get('submissionId'));
    for (const name of ['role','community','message']) expect(posts[1].get(name)).toBe('');
  });

  test(path + ': native form submits all details without JavaScript', async ({browser}) => {
    const context = await browser.newContext({javaScriptEnabled:false,baseURL:'http://127.0.0.1:4173'});
    try {
      await context.route('https://**/*', route => route.abort());
      const page = await context.newPage();
      let request;
      await page.route(endpoint, route => {
        request = new URLSearchParams(route.request().postData());
        return route.fulfill({contentType:'text/plain',body:'Received'});
      });
      await page.goto(path);
      await requiredFields(page);
      await page.locator('.promoters-application-submit').press('Enter');
      await expect(page.locator('body')).toContainText('Received');
      expect(request.get('phone')).toBe('+00123');
      expect(request.get('language')).toBe(italian ? 'it':'en');
    } finally { await context.close(); }
  });
}
