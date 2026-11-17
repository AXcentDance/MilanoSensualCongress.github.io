import {test,expect} from '@playwright/test';

test.beforeEach(async ({context})=>{
 await context.route('https://**/*',r=>r.fulfill({status:200,body:''}));
});
for(const path of ['/parties','/parties.html']) {
 test(`Schedule redirect: ${path} preserves query and day anchor`,async({page})=>{
  await page.goto(path+'?utm_source=saved-link#saturday');
  await expect(page).toHaveURL(/\/schedule\?utm_source=saved-link#saturday$/);
  await expect(page.locator('h1')).toHaveText('Schedule 2026');
  await expect(page.locator('.schedule-artwork img')).toHaveCount(3);
 });
}
test('Schedule redirect works without JavaScript',async({browser,baseURL},info)=>{
 const context=await browser.newContext({javaScriptEnabled:false,viewport:info.project.use.viewport});
 try{
  const page=await context.newPage();await page.goto(baseURL+'/parties');
  await expect(page).toHaveURL(/\/schedule$/);
  await expect(page.locator('h1')).toHaveText('Schedule 2026');
 }finally{await context.close();}
});
test('Schedule canonical and translated links use the new URL',async({page})=>{
 await page.goto('/schedule');
 await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href','https://milanosensualcongress.com/schedule');
 await expect(page.locator('link[hreflang="it"]')).toHaveAttribute('href','https://milanosensualcongress.com/it/party');
 await page.goto('/it/party');
 await expect(page.locator('link[hreflang="en"]')).toHaveAttribute('href','https://milanosensualcongress.com/schedule');
 const menu=page.locator('button[aria-controls="mobile-menu"]');
 if(await menu.isVisible()) await menu.click();
 const english=page.locator('nav a[href="../schedule"],nav a[href="/schedule"]').filter({visible:true}).first();
 await english.click();await expect(page).toHaveURL(/\/schedule$/);
});
