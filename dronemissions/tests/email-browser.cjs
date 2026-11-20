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
   if(viewport.width>1000){
    const saved=await page.evaluate(async()=>{
     const folder=(await api('folder',{name:'Synthetic smooth grid browser'})).id;
     const plan={name:'Synthetic video turns',type:'grid',cameraId:'mavic3',geometry:{type:'Polygon',coordinates:[[[16,48],[16.003,48],[16.003,48.003],[16,48.003],[16,48]]]},params:{captureMode:'video',height:70,gridMotion:'smooth',gridTurnRadius:10,speed:5,photoLimit:200,sectionOverlap:2,terrainMode:'off'}};
     const saved=await api('planner-save',{folder,plan});await refresh();return saved;
    });
    const preview=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.locator(`#saved-plans [data-planner-id="${saved.id}"]`).click();
    const result=await (await preview).json();
    await page.waitForFunction(()=>document.querySelector('#pl-live-status').textContent.includes('Fließendes Raster'));
    assert(result.gridTurns.roundedCorners>0);
    assert.equal(await page.locator('#pl-gridMotion').inputValue(),'smooth');
    assert.equal(await page.locator('#pl-limit-label').textContent(),'Max. Wegpunkte je Abschnitt');
    const expected=result.parts.reduce((n,part)=>n+part.length,0);
    const visible=await page.locator('#pl-map path[stroke="#fff"][fill-opacity="1"]').count();
    assert.equal(visible,expected,'every video support point is drawn');
    await page.locator('#pl-review').click();
    const profile=await page.locator('#pl-profile').evaluate(select=>select.options[1]?.value);
    assert(profile,'synthetic reference mission is available');
    await page.locator('#pl-profile').selectOption(profile);
    await page.getByRole('button',{name:'Mission im Projekt speichern',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#pl-status').textContent.includes('als Mission im gewählten Projekt gespeichert'));
    assert.equal(await page.getByRole('button',{name:'Planung speichern',exact:true}).count(),1);
    await page.locator('#planner-dialog').evaluate(dialog=>dialog.close());
   }
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
