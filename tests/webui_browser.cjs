// Copyright (c) 2026 OpenAI
// SPDX-License-Identifier: LGPL-3.0-or-later
// Browser regression checks for both generated reports, with and without Chart.js.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const fixtures=path.resolve(process.argv[2]);
const chartScript=path.resolve(process.argv[3]);
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE || undefined,headless:true,args:['--no-sandbox']});
 let scenarios=0;
 for (const offline of [false,true]) {
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('https://cdn.jsdelivr.net/**',r=>offline?r.abort():r.fulfill({path:chartScript,contentType:'application/javascript'}));
 for(const tool of ['bake','oelint']){
  const open=async(name)=>{await page.goto(pathToFileURL(path.join(fixtures, `${tool}-${name}.html`)).href);};
  const click=async(severity)=>page.locator('.filter-btn[data-severity="'+severity+'"]').click();
  const text=async(id)=>page.locator('#'+id).textContent();
  await open('zero');
  assert.equal(await text('qs-error-rate'),'0.0%');
  assert.match(await page.locator('#qs-error-rate').evaluate(e=>e.parentElement.className),/success-highlight/);
  await page.locator('[data-tab="statistics"]').click();await page.waitForTimeout(200);
  assert.equal(await page.locator('#chart-unavailable').isVisible(),offline);
  await page.waitForTimeout(1000);
  await page.screenshot({path:`${fixtures}/${tool}-${offline?'offline':'charts'}.png`,fullPage:true});
  await open('mixed');
  const health=await text('healthValue');
  await click('error'); // Filter before first chart creation.
  assert.equal(await text('qs-total-issues'),'2');
  assert.equal(await page.locator('.filter-btn[data-severity=error]').getAttribute('aria-pressed'),'false');
  assert.equal(await page.locator('#rules .badge.error').count(),0);
  assert.equal(await text('qs-error-rate'),'—');
  assert.equal(await text('healthValue'),health);
  assert.equal(await page.locator('.stat.error .stat-value').textContent(),'1');
  await page.locator('[data-tab="statistics"]').click();await page.waitForTimeout(200);
  assert.equal(await text('qs-total-issues'),'2');
  assert.equal(await text('healthValue'),health);
  if(!offline) assert.deepEqual(await page.evaluate(()=>window.linterCharts.severityPie.data.datasets[0].data),[0,1,1]);
  await click('warning');await click('info');
  assert.equal(await text('qs-total-issues'),'0');
  assert.equal(await text('healthValue'),health);
  assert.match(await page.locator('.status-badge').textContent(),/3 Issue/);
  await page.locator('[data-tab="rules"]').click();
  assert.equal(await page.locator('#rules .filter-empty').isVisible(),true);
  for(const severity of ['error','warning','info']) await click(severity);
  assert.equal(await text('qs-total-issues'),'3');
  assert.equal(await text('qs-error-rate'),'33.3%');
  assert.equal(await page.locator('#rules .filter-empty').isVisible(),false);
  await page.locator('.rule-help-link:visible').first().focus();
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('.rule-docs-close').evaluate(e=>document.activeElement===e),true);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#rule-docs-modal').isVisible(),false);
  if (tool === 'bake') {
    await open('incomplete');
    assert.equal(await text('qs-error-rate'),'—');
    assert.equal(await text('healthValue'),'—');
    assert.match(await page.locator('.status-badge').textContent(), /incomplete/);
  }
  await open('unscanned');assert.match(await page.locator('.status-badge').textContent(),/No files/);assert.equal(await text('healthValue'),'—');assert.equal(await text('qs-error-rate'),'—');
  await open('clean');assert.equal(await text('healthValue'),'100');assert.equal(await text('qs-error-rate'),'0.0%');
  await open('info');assert.match(await page.locator('.summary').getAttribute('class'),/info/);
  await page.setViewportSize({width:390,height:844});
  await page.locator('[data-tab="statistics"]').click();await page.waitForTimeout(200);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  assert.equal(overflow,false,tool+' mobile overflow');
  await page.waitForTimeout(1000);
  await page.screenshot({path:`${fixtures}/${tool}-mobile-${offline}.png`,fullPage:true});
  await page.setViewportSize({width:1280,height:900});
  assert.deepEqual(errors,[]);
  scenarios++;console.log('PASS',tool,offline?'offline':'charts');
 }
 await page.close();
 }
 await browser.close();console.log(scenarios+' browser scenarios passed');
})().catch(e=>{console.error(e);process.exit(1)});
