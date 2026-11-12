import {test,expect} from '@playwright/test';
const endpoint='https://script.google.com/macros/s/TEST_INSURANCE_RECEIVER/exec';
const data={lastName:'Test',firstName:'Example',dateOfBirth:'1990-02-15',placeOfBirth:'Switzerland',address:'Test street 1',postalCode:'00123',municipality:'Switzerland',email:'test@example.com'};
test.beforeEach(async({context})=>{await context.route('https://**/*',route=>route.fulfill({status:200,body:''}));});
for(const path of ['/insurance','/it/insurance']) {
 test(`${path}: insurance nine bilingual fields and unavailable state`,async({page})=>{
  await page.route(`**${path}`,async route=>{const r=await route.fetch(); await route.fulfill({response:r,body:(await r.text()).replace(/data-endpoint="[^"]*"/, 'data-endpoint=""')});});
  await page.goto(path);
  await expect(page.locator('#insurance-form [required]')).toHaveCount(9);
  await expect(page.locator('.insurance-field label span[lang=it]')).toHaveCount(9);
  await expect(page.locator('.insurance-field label span[lang=en]')).toHaveCount(9);
  await expect(page.locator('input[type=tel]')).toHaveCount(0);
  await expect(page.locator('#insurance-form button')).toBeDisabled();
  await expect(page.locator('#placeOfBirth-hint')).toContainText('Stato di nascita');
  await expect(page.locator('#municipality-hint')).toContainText('indicare la nazione');
 });
 test(`${path}: insurance acknowledged POST, retry, no duplicates`,async({page})=>{
  await page.route(`**${path}`,async route=>{const r=await route.fetch(); await route.fulfill({response:r,body:(await r.text()).replace(/data-endpoint="[^"]*"/,`data-endpoint="${endpoint}"`)});});
  const posts=[];
  await page.route(endpoint,async route=>{
   const req=route.request(); expect(req.method()).toBe('POST'); expect(req.url()).not.toContain('email');
   posts.push(new URLSearchParams(req.postData()));
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(posts.length===1 ? {ok:false} : {ok:true,submissionId:posts.at(-1).get('submissionId')})});
  });
  await page.goto(path);
  await page.locator('#insurance-form button').click(); expect(posts).toHaveLength(0);
  for(const [name,value] of Object.entries(data)) await page.locator(`[name=${name}]`).fill(value);
  await page.locator('[name=sex]').selectOption('F');
  await page.locator('[name=dateOfBirth]').fill('2999-01-01');
  await page.locator('#insurance-form button').click(); expect(posts).toHaveLength(0);
  await page.locator('[name=dateOfBirth]').fill(data.dateOfBirth);
  await page.locator('#insurance-form button').click();
  await expect(page.locator('#insurance-status')).toHaveAttribute('data-state','error');
  await expect(page.locator('[name=email]')).toHaveValue(data.email);
  await page.locator('#insurance-form button').click();
  await expect(page.locator('#insurance-status')).toHaveAttribute('data-state','success');
  expect(posts).toHaveLength(2);
  expect(posts[0].get('submissionId')).toBe(posts[1].get('submissionId'));
  expect(posts[1].get('postalCode')).toBe('00123');
  expect(posts[1].has('phone')).toBe(false);
  await expect(page.locator('#insurance-form button')).toBeDisabled();
 });
}
