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
   await page.locator('#bridge').click();
   await page.locator('#bridge-device-name').fill('Browser test Mac');
   await page.locator('#bridge-device-create').click();
   await page.waitForFunction(()=>document.querySelector('#bridge-device-secret').value.startsWith('dmb_'));
   await page.locator('#bridge-device-list [data-device-revoke]').last().click();
   await page.waitForFunction(()=>document.querySelector('#bridge-device-secret').value==='');
   await page.locator('#bridge-dialog [data-close]').first().click();
   if(viewport.width>1000){
    await page.locator('#planner-open').click();await page.locator('#planner-dialog').waitFor({state:'visible'});
    await page.locator('#pl-type').selectOption('grid');
    assert.equal(await page.locator('#pl-pitchMode').inputValue(),'manual');assert.equal(await page.locator('#pl-cameraPitch').inputValue(),'-70');
    await page.locator('#pl-type').selectOption('helix');assert.equal(await page.locator('#pl-pitchMode').inputValue(),'auto');
    await page.locator('#pl-type').selectOption('corridor');assert.equal(await page.locator('#pl-cameraPitch').inputValue(),'-70');assert.equal(await page.locator('#pl-pitchMode').inputValue(),'manual');
    await page.locator('#pl-cameraPitch').fill('-75');await page.locator('#pl-type').selectOption('grid');assert.equal(await page.locator('#pl-cameraPitch').inputValue(),'-75','explicit pitch preserved');
    await page.locator('#pl-close').click();
    const saved=await page.evaluate(async()=>{
     const folder=(await api('folder',{name:'Synthetic smooth grid browser'})).id;
     const plan={name:'Synthetic video turns',type:'grid',cameraId:'mavic3',geometry:{type:'Polygon',coordinates:[[[16,48],[16.003,48],[16.003,48.003],[16,48.003],[16,48]]]},params:{captureMode:'video',height:70,gridMotion:'smooth',gridTurnRadius:10,speed:5,photoLimit:200,sectionOverlap:2,terrainMode:'off',flightSplit:'count',flightCount:2,flightMinutes:15,entryEnabled:true,entryLat:48,entryLng:16}};
     const saved=await api('planner-save',{folder,plan});await refresh();return saved;
    });
    const preview=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.locator(`#saved-plans [data-planner-id="${saved.id}"]`).click();
    const result=await (await preview).json();
    await page.waitForFunction(()=>document.querySelector('#pl-live-status').textContent.includes('Fließendes Raster'));
    assert(result.gridTurns.roundedCorners>0);
    assert.equal(await page.locator('#pl-gridMotion').inputValue(),'smooth');
    assert.equal(await page.locator('#pl-pitchMode').inputValue(),'auto','legacy saved plan keeps automatic pitch');
    assert.equal(await page.locator('#pl-drafts').inputValue(),saved.id,'loaded plan selected');
    assert.equal(await page.locator('.pl-head .badge-warn').count(),0);
    const cameraFits=await page.locator('#pl-cameraId').evaluate(e=>{const c=document.createElement('canvas').getContext('2d'),s=getComputedStyle(e);c.font=s.font;return e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)>=c.measureText(e.selectedOptions[0].text).width;});assert(cameraFits,'camera label fits with arrow space');
    assert(await page.locator('#pl-bearing').evaluate(e=>e.clientWidth>=80),'degree field has room for spinner and value');
    assert.equal(await page.locator('#pl-limit-label').textContent(),'Max. Wegpunkte je Abschnitt');
    const expected=result.parts.reduce((n,part)=>n+part.length,0);
    const visible=await page.locator('#pl-map path[stroke="#fff"][fill-opacity="1"]').count();
    assert.equal(visible,expected,'every video support point is drawn');
    assert.equal(result.parts.length,2);
    await page.locator('#pl-flightCount').scrollIntoViewIfNeeded();
    let recalc=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.locator('#pl-flightCount').fill('3');
    assert.equal((await (await recalc).json()).parts.length,3);
    assert.equal(await page.locator('#pl-flight-fields #pl-photoLimit').count(),1,'point limit grouped with time and sections');
    assert.equal(await page.locator('#pl-photoLimit').isVisible(),false,'manual count hides unused point cap');
    assert.equal(await page.locator('#pl-flightMinutes').isVisible(),true,'manual count keeps budget beside count');
    const stepLayout=await page.locator('#pl-flightCount').evaluate(input=>{const wrap=input.closest('.pl-stepper'),boxes=[...wrap.children].map(e=>e.getBoundingClientRect());return {display:getComputedStyle(wrap).display,gap:Math.max(Math.abs(boxes[0].right-boxes[1].left),Math.abs(boxes[1].right-boxes[2].left)),height:Math.max(...boxes.map(b=>b.height))-Math.min(...boxes.map(b=>b.height))};});
    assert.equal(stepLayout.display,'grid');assert(stepLayout.gap<1&&stepLayout.height<1,'stepper buttons flush and aligned');
    assert.equal(await page.locator('#pl-photoLimit').getAttribute('max'),'5000','point limit can exceed 200');
    assert.equal(await page.locator('#pl-slider-photoLimit').getAttribute('max'),'5000','slider shares raised limit');
    const minutes=page.locator('#pl-flightMinutes');
    await minutes.scrollIntoViewIfNeeded();
    const before=Number(await minutes.inputValue());
    const minutePreview=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await minutes.locator('..').getByRole('button',{name:'Flugzeit pro Akku · min erhöhen',exact:true}).click();
    assert.equal(Number(await minutes.inputValue()),before+1);
    await (await minutePreview).finished();
    await page.waitForFunction(()=>document.querySelector('#pl-status').textContent.includes('Vorschau aktuell'));
    const marker=page.locator('#pl-map .pl-home-marker');
    assert.equal(await marker.locator('img').getAttribute('src'),'vendor/icons/helipad-romzicon-164972.png');
    await marker.locator('img').evaluate(img=>img.decode());
    assert(await marker.evaluate(e=>{const a=e.getBoundingClientRect(),b=e.querySelector('img').getBoundingClientRect();return Math.abs(a.x+a.width/2-b.x-b.width/2)<.1&&Math.abs(a.y+a.height/2-b.y-b.height/2)<.1;}),'helipad graphic centered on marker anchor');
    await marker.hover(); // wait for the redraw/map animation to settle before dragging
    const oldLat=await page.locator('#pl-entry-lat').inputValue();
    const box=await marker.boundingBox();assert(box);
    recalc=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+30,box.y+box.height/2-30,{steps:12});await page.mouse.up();
    await page.waitForFunction(old=>document.querySelector('#pl-entry-lat').value!==old,oldLat);
    await recalc;assert.notEqual(await page.locator('#pl-entry-lat').inputValue(),oldLat,'H drag updates coordinates');
    await page.locator('#pl-review').click();
    const profile=await page.locator('#pl-profile').inputValue();assert(profile,'saved drone profile is selected automatically');
    assert(await page.locator('#pl-device-settings').isHidden(),'known drone needs no extra KMZ selection');
    await page.getByRole('button',{name:'Mission im Projekt speichern',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#pl-status').textContent.includes('Flüge zur gemeinsamen Planung im Projekt gespeichert'));
    assert.equal(await page.getByRole('button',{name:'Planung speichern',exact:true}).count(),1);
    await page.locator('#planner-dialog').evaluate(dialog=>dialog.close());
    assert.equal(await page.locator('#saved-plans .saved-plan').filter({has:page.locator(`[data-planner-id="${saved.id}"]`)}).locator('[data-flight-open]').count(),3,'flights grouped within saved raster');
    assert.equal(await page.locator(`#saved-plans [data-planner-id="${saved.id}"]`).count(),1,'one master plan');
    const again=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.locator(`#saved-plans [data-planner-id="${saved.id}"]`).click();
    assert.equal((await (await again).json()).parts.length,3);
    assert.equal(await page.locator('#pl-flightCount').inputValue(),'3');
    assert.equal(await page.locator('#pl-profile').inputValue(),profile,'device reference retained');assert.equal(await page.locator('#pl-device-settings').evaluate(e=>e.open),false,'known device requires no additional selection');
    await page.locator('#planner-dialog').evaluate(dialog=>dialog.close());
   }
   if(viewport.width>1000){
    const old=await page.evaluate(async()=>{const row=data.plans.find(p=>p.name==='Synthetic video turns');const loaded=await api('planner-load&id='+row.id);const plan={...loaded.body,name:'Synthetic video turns updated'};await api('planner-save',{id:row.id,revision:row.revision,folder:row.folder,profileMission:plan.profileMission,plan});await refresh();return {id:row.id,revision:row.revision};});
    const remove=page.locator(`[data-delete-plan-export="${old.id}"][data-export-revision="${old.revision}"]`);
    await remove.click();assert((await page.locator('#confirm-text').textContent()).includes(`Revision ${old.revision}`));
    await page.locator('#confirm-dialog').getByRole('button',{name:'Abbrechen',exact:true}).click();assert(await remove.isVisible());
    await remove.click();const deleted=page.waitForResponse(r=>r.url().includes('action=planner-export-delete')&&r.status()===200);await page.locator('#confirm-ok').click();assert.equal((await (await deleted).json()).deleted,3);
    await page.waitForFunction(id=>!document.querySelector(`[data-delete-plan-export="${id}"]`),old.id);assert.equal(await page.locator(`[data-planner-id="${old.id}"]`).count(),1,'master plan survives export deletion');
   }
   if(viewport.width>1000){
    const h=await page.evaluate(async()=>{const p={name:'Manual helix browser',type:'doubleHelix',cameraId:'mavic3',geometry:{type:'Point',coordinates:[16,48]},params:{shape:'hemisphere',radius:30,bottom:20,top:50,standoff:20,spacingMode:'distance',photoDistance:5,trackDistance:10,flightSplit:'count',flightCount:1,flightMinutes:15,entryEnabled:false,photoLimit:200}};const h=await api('planner-save',{plan:p});await refresh();return h;});
    let response=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.locator(`#saved-plans [data-planner-id="${h.id}"]`).click();
    assert.equal((await (await response).json()).parts.length,1);
    assert(await page.locator('#pl-flight-fields').isVisible());
    assert.equal(await page.locator('#pl-flightCount').inputValue(),'1');
    response=page.waitForResponse(r=>r.url().includes('action=planner-preview')&&r.status()===200);
    await page.locator('#pl-flightCount').fill('2');await page.locator('#pl-flightCount').press('Tab');
    assert.equal((await (await response).json()).parts.length,2);
    await page.locator('#planner-dialog').evaluate(dialog=>dialog.close());
   }
   if(viewport.width>1000){
    await page.evaluate(async()=>{
     const f=data.folders.find(f=>f.name==='Synthetic smooth grid browser');
     navigate('folder',f.id);
     document.querySelector('#page-title').textContent='3GS';
     document.querySelector('#page-subtitle').textContent='Flugmissionen und wiederverwendbare Panorama-Standorte an einem Ort. Vier archivierte Missionen sind im selben Projektordner zu finden.';
    });
    for(const width of [1600,1280]){
     await page.setViewportSize({width,height:900});
     assert(await page.locator('.page-head-text').evaluate(e=>e.getBoundingClientRect().width>=300),'project heading retains readable width');
     assert(await page.locator('#page-title').evaluate(e=>e.getBoundingClientRect().height<70),'short project title stays on one line');
     assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'header buttons stay within page');
    }
    await page.evaluate(()=>{
     document.querySelector('#overview-map').classList.remove('hidden');renderOverview();
    });
    await page.waitForTimeout(150);
    await page.evaluate(()=>{
     overview.setView([47.91,16.23],14,{animate:false});
     const input=[...document.querySelectorAll('#overview-map [data-map-base]')].find(e=>e.value==='Weltweit · OpenStreetMap');input.click();
     const original=L.map;L.map=function(...args){const map=original.apply(this,args);if(args[0]==='pl-map')window.testPlannerMap=map;return map;};
    });
    await page.locator('#planner-open').click();
    await page.locator('#pl-map .map-panel>summary').click();
    assert(await page.locator('#pl-map .map-address-form input').isVisible());
    assert(await page.locator('#pl-map [data-map-base][value="Weltweit · OpenStreetMap"]').isChecked(),'project background retained');
    const start=await page.evaluate(()=>({lat:window.testPlannerMap.getCenter().lat,lng:window.testPlannerMap.getCenter().lng,zoom:window.testPlannerMap.getZoom()}));
    assert(Math.abs(start.lat-47.91)<.0001&&Math.abs(start.lng-16.23)<.0001&&start.zoom===14,'new mission retains project map view');
    await page.route('**/api.php?action=address',route=>route.fulfill({json:{results:[{label:'Synthetic address',lat:48.123,lng:16.456}],source:'fixture'}}));
    await page.locator('#pl-map .map-address-form input').fill('Synthetic address');
    await page.locator('#pl-map .map-address-form button[type="submit"]').click();
    await page.locator('#pl-map [data-address-result]').click();
    await page.waitForFunction(()=>Math.abs(window.testPlannerMap.getCenter().lat-48.123)<.0001);
    assert.equal(await page.locator('#pl-live-status').textContent(),'Umriss zeichnen oder importieren','search does not draw or change mission');
    await page.locator('#planner-dialog').evaluate(d=>d.close());
    // The fallback uses project routes even if its overview was never opened.
    assert(await page.evaluate(()=>{dmProjectViews.clear();const map=window.testPlannerMap,original=data.missions;try{data.missions=[{folder,details:{points:[{lat:48,lng:16},{lat:48.003,lng:16.003}]}}];dmApplyProjectView(map,folder);return map.getBounds().contains([48.001,16.001])&&map.getZoom()>12;}finally{data.missions=original;}}),'project route extent fallback');
   }
   if(viewport.width>1000){
    const tile=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=','base64');
    await page.route('https://mapsneu.wien.gv.at/**',route=>route.fulfill({body:tile,contentType:'image/png',headers:{'access-control-allow-origin':'*'}}));
    await page.evaluate(()=>{const f=data.folders.find(f=>f.name==='Synthetic smooth grid browser');navigate('folder',f.id);});
    await page.locator('#folder-options').click();await page.locator('#folder-form [name="previewDefault"]').selectOption('3d');
    const savedFolder=page.waitForResponse(r=>r.url().includes('action=folder')&&r.request().method()==='POST');await page.locator('#folder-form button[type="submit"]').click();await savedFolder;
    await page.waitForFunction(()=>folderById(folder)?.preview_effective==='3d');
    await page.evaluate(()=>{
     const host=document.createElement('div');host.id='test-preview-host';host.style='position:fixed;top:10px;left:10px;z-index:99999;background:white;display:flex';document.body.append(host);
     const points=[{lat:48,lng:16,height:60},{lat:48.001,lng:16.001,height:60},{lat:48.002,lng:16,height:60}];
     const grid={id:'preview-grid-test',folder,versionId:'fixture',revision:1,name:'Synthetic raster',hasCustomPreview:false,details:{plannerType:'grid',points,routes:[{start:0,count:3}],pois:[]}};
     const helix={...grid,id:'preview-helix-test',name:'Synthetic helix',folder:null,details:{...grid.details,plannerType:'doubleHelix',points:points.map((p,i)=>({...p,height:20+i*20}))}};
     for(const m of [grid,helix,{...grid,id:'preview-custom-test',hasCustomPreview:true}]){data.missions.push(m);const img=document.createElement('img');img.dataset.missionPreview=m.id;img.width=240;img.height=150;img.src='data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';host.append(img);}
    });
    await page.locator('[data-mission-preview="preview-grid-test"][data-preview-rendered="3d"]').waitFor();
    await page.locator('[data-mission-preview="preview-helix-test"][data-preview-rendered="3d"]').waitFor();
    assert.equal(await page.locator('[data-mission-preview="preview-custom-test"]').getAttribute('data-preview-rendered'),null,'custom title remains untouched');
    await page.evaluate(()=>{const m=data.missions.find(m=>m.id==='preview-grid-test');m.folder=null;document.querySelector('#test-preview-host').append(document.createElement('span'));});
    await page.locator('[data-mission-preview="preview-grid-test"][data-preview-rendered="aerial"]').waitFor();
    assert((await page.locator('[data-mission-preview="preview-grid-test"]').getAttribute('src')).startsWith('data:image/jpeg'));
    await page.evaluate(()=>{document.querySelector('#test-preview-host').remove();data.missions=data.missions.filter(m=>!m.id.startsWith('preview-'));});
   }
   if(viewport.width>1000){
    await page.locator('#flight-logs-open').click();
    await page.locator('#dji-log-setup-open').click();
    await page.waitForFunction(()=>document.querySelector('#dji-log-key-status').textContent.includes('Noch kein App Key'));
    await page.locator('#dji-log-api-key').fill('synthetic-browser-test-key-123456');
    await page.locator('#dji-log-settings-form button[type="submit"]').click();
    await page.waitForFunction(()=>document.querySelector('#dji-log-key-status').textContent.includes('Schlüssel hinterlegt'));
    assert.equal(await page.locator('#dji-log-api-key').inputValue(),'');
    await page.locator('#dji-log-close').click();
    // Clear synthetic server key without interacting with the separate confirmation dialog.
    await page.evaluate(async()=>{const s=await api('dji-log-settings');await api('dji-log-settings',{revision:s.revision,apiKey:null});});
    let cloudConnected=false;
    await page.route('**/api.php?action=dji-cloud-*',async route=>{
     const action=new URL(route.request().url()).searchParams.get('action');let result;
     if(action==='dji-cloud-status')result={connected:cloudConnected,email:cloudConnected?'pilot@example.test':null,decoderReady:true};
     else if(action==='dji-cloud-captcha')result={challengeId:'test-challenge',image:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ioAAAAASUVORK5CYII='};
     else if(action==='dji-cloud-login'){assert.equal(route.request().postDataJSON().answer,'AB12');cloudConnected=true;result={connected:true};}
     else if(action==='dji-cloud-list')result={records:[{id:'synthetic-ui',filename:'Synthetic.txt',status:'pending',selected:true},{id:'archived-ui',filename:'Archived.txt',status:'archived',selected:false}],done:true};
     else if(action==='dji-cloud-sync'){assert.equal(route.request().postDataJSON().id,'synthetic-ui');result={id:'synthetic-log',assigned:true,duplicate:false};}
     else if(action==='dji-cloud-disconnect'){cloudConnected=false;result={ok:true};}
     else throw Error('Unexpected mocked cloud action');
     await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)});
    });
    await page.locator('#dji-cloud-open').click();await page.locator('#dc-refresh').click();
    await page.locator('#dc-captcha').waitFor({state:'visible'});
    await page.locator('#dc-email').fill('pilot@example.test');await page.locator('#dc-password').fill('synthetic-password');await page.locator('#dc-answer').fill('AB12');
    await page.locator('#dc-login button[type="submit"]').click();await page.locator('#dc-connected').waitFor({state:'visible'});
    assert.equal(await page.locator('#dc-password').inputValue(),'');
    await page.locator('#dc-list').click();await page.waitForFunction(()=>document.querySelector('#dc-status').textContent.includes('1 relevante Flüge'));
    assert.equal(await page.locator('#dc-records').getByText('Archived.txt',{exact:true}).count(),0);await page.locator('#dc-archive').check();assert.equal(await page.locator('#dc-records').getByText('Archived.txt',{exact:true}).count(),1);
    await page.locator('#dc-sync').click();await page.waitForFunction(()=>document.querySelector('#dc-status').textContent.includes('1 automatisch zugeordnet'));
    await page.locator('#dc-disconnect').click();await page.locator('#dc-login').waitFor({state:'visible'});await page.locator('#dc-close').click();
    await page.unroute('**/api.php?action=dji-cloud-*');
    const project=await page.evaluate(()=>data.folders.find(f=>f.name==='Synthetic flight logs').id);
    await page.locator('#fl-folder').selectOption(project);
    const fixture={_exportInfo:{format:'Open DroneLog JSON Export'},flight:{displayName:'Browser log import',startTime:'2026-10-17T13:00:00Z',durationSecs:600,totalDistance:1200,droneModel:'Synthetic Mavic 4'},telemetry:{time:[0,300,600],latitude:[48,48.001,48],longitude:[16,16.002,16.004],battery:[95,80,65]}};
    await page.locator('#fl-files').setInputFiles({name:'browser-flight.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(fixture))});
    await page.waitForFunction(()=>document.querySelector('#fl-status').textContent.includes('Prüfung fertig'));
    assert((await page.locator('#fl-imports').textContent()).includes('30 Prozentpunkte'));
    const option=await page.locator('[data-import-choice="0"]').evaluate(e=>e.options[1].value);
    await page.locator('[data-import-choice="0"]').selectOption(option);
    await page.locator('#fl-import').click();await page.waitForFunction(()=>document.querySelector('#fl-status').textContent.includes('1 Fluglogs importiert'));
    assert((await page.locator('#fl-list').textContent()).includes('Browser log import'));
    const flightCard=page.locator('#fl-list [data-ref-card]').filter({has:page.locator('.flight-card-title', {hasText:'Browser log import'})});
    await flightCard.locator('[data-ref-pick]').check();
    await page.waitForFunction(()=>document.querySelectorAll('#fl-map .leaflet-flightReference-pane path').length>0);
    await flightCard.locator('[data-ref-details]').click();assert((await page.locator('#fl-detail').textContent()).includes('30 Prozentpunkte'));
    await flightCard.locator('.flight-edit summary').click();await flightCard.locator('[data-ref-name]').fill('Browser renamed flight');await flightCard.locator('[data-ref-capture]').selectOption('panorama');await flightCard.locator('[data-ref-save]').click();
    await page.waitForFunction(()=>document.querySelector('#fl-list').textContent.includes('Browser renamed flight'));
    await page.locator('[data-log-close]').click();
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
