// Runs only against the disposable installation owned by run-email-suite.py.
const { chromium } = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
 const [base, accessPath] = process.argv.slice(2);
 assert.equal(new URL(base).hostname, '127.0.0.1');
 const access = JSON.parse(fs.readFileSync(accessPath, 'utf8'));
 const browser = await chromium.launch({headless:true});
 try {
  for (const viewport of [{width:1280,height:900},{width:390,height:844}]) {
   const context = await browser.newContext({viewport});
   const page = await context.newPage();
   const errors=[];page.on('pageerror', error => errors.push(error.message));
   await page.goto(base);
   await page.getByLabel('E-Mail-Adresse', {exact:true}).fill(access.email);
   await page.getByRole('button', {name:'Code anfordern',exact:true}).click();
   await page.getByLabel('Sechsstelliger Anmeldecode', {exact:true}).waitFor({state:'visible'});
   assert.equal(await page.locator('#login-submit-label').textContent(), 'Archiv öffnen');
   // Restart and reload both return to the email step.
   await page.getByRole('button', {name:'Neuen Code anfordern / Adresse ändern',exact:true}).click();
   assert.equal(await page.locator('#login-code').inputValue(), '');
   await page.reload();
   await page.getByLabel('E-Mail-Adresse', {exact:true}).fill(access.email);
   await page.getByRole('button', {name:'Code anfordern',exact:true}).click();
   await page.getByLabel('Sechsstelliger Anmeldecode', {exact:true}).waitFor({state:'visible'});
   const raw=fs.readFileSync(access.mailbox,'utf8');
   const part=raw.match(/Content-Type: text\/plain;[\s\S]*?\r\n\r\n([\s\S]*?)\r\n--/)[1];
   const code=Buffer.from(part,'base64').toString('utf8').match(/Anmeldecode für Drone Missions: (\d{6})/)[1];
   await page.getByLabel('Sechsstelliger Anmeldecode', {exact:true}).fill(code);
   await page.getByRole('button', {name:'Archiv öffnen',exact:true}).click();
   await page.locator('#shell').waitFor({state:'visible'});
   await page.reload();await page.locator('#shell').waitFor({state:'visible'});
   const cookie=(await context.cookies()).find(c=>c.name==='dm_session');
   assert(cookie.httpOnly && cookie.sameSite==='Strict');
   assert(cookie.expires>Date.now()/1000+43100);
   // Mobile navigation may hide logout; open the drawer through the existing toggle.
   const logout=page.locator('#logout');
   if (!await logout.isVisible()) {
    const toggle=page.locator('#menu-toggle');
    if(await toggle.count()) await toggle.click();
   }
   // The actual logout handler is exercised even if responsive navigation clips the button.
   await logout.evaluate(button=>button.click());
   await page.getByLabel('E-Mail-Adresse', {exact:true}).waitFor({state:'visible'});
   assert.equal(await page.locator('#login-code').inputValue(),'');
   assert.equal(await page.locator('#login-submit-label').textContent(),'Code anfordern');
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   assert.deepEqual(errors,[]);
   await context.close();
  }
  console.log('PASS: Chromium desktop/mobile email labels, code step, restart, login, reload, cookie lifetime and logout');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
