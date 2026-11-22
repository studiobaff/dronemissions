const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const [base,accessPath]=process.argv.slice(2);assert.equal(new URL(base).hostname,'127.0.0.1');
 const access=JSON.parse(fs.readFileSync(accessPath,'utf8')),browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext();let csrf;
  const api=async(action,body)=>{const r=await context.request.fetch(base+'api.php?action='+action,{method:body?'POST':'GET',headers:body?{'X-CSRF-Token':csrf}:{},data:body});assert(r.ok(),action+': '+await r.text());return r.json();};
  csrf=(await api('session')).csrf;await api('login',{email:access.email});
  const mail=fs.readFileSync(access.mailbox,'utf8'),part=mail.match(/Content-Type: text\/plain;[\s\S]*?\r\n\r\n([\s\S]*?)\r\n--/)[1],code=Buffer.from(part,'base64').toString('utf8').match(/Anmeldecode für Drone Missions: (\d{6})/)[1];await api('login-verify',{code});
  const page=await context.newPage();await page.goto(base);await page.waitForFunction(()=>window.dmFlightReference);
  await page.evaluate(()=>{
   const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;z-index:9999;background:white;overflow:auto';host.innerHTML='<div id="ref-map" style="height:350px"></div><div id="ref-controls"></div>';document.body.append(host);
   window.refMap=L.map('ref-map');window.refCalls=[];
   window.refMissions=[{id:'kmz',name:'Test Raster',folder:'project',details:{sourceFormat:'dji-kmz',plannerCaptureMode:'photo',points:[{lat:48,lng:16},{lat:48.01,lng:16},{lat:48.1,lng:16.1},{lat:48.11,lng:16.1}],routes:[{start:0,count:2},{start:2,count:2}]}}];window.refBefore=JSON.stringify(refMissions);
   window.refRequest=async(action,body)=>{refCalls.push(action);if(action==='flight-log-label'){window.refSaved=body;return {revision:2};}if(action.startsWith('flight-logs'))return {logs:[{id:'actual',revision:1,folder:'project',previewSegments:[[[48,16],[48.01,16]]],summary:{name:'Actual route',model:'Mavic 3 Cine',startTime:'2026-10-16T10:00:00Z'}},{id:'slow',revision:1,previewSegments:[[[50,18],[50.01,18]]],summary:{name:'Delayed',model:'Mavic 4'}}]};if(action.endsWith('slow'))return new Promise(resolve=>window.refResolve=resolve);return {track:[{lat:48,lng:16,time:0},{lat:48.01,lng:16,time:1},{lat:48.1,lng:16,time:50},{lat:48.11,lng:16,time:51}]};};
   dmFlightReference(refMap,document.querySelector('#ref-controls'),{missions:refMissions,scope:'editor-scope',project:'project',request:refRequest});refMap.setView([48,16],12);
   window.refLayers=()=>Object.values(refMap._layers).filter(l=>l instanceof L.Path&&l.options?.pane==='flightReference');
  });
  await page.locator('#ref-controls > details > summary').click();
  await page.waitForFunction(()=>document.querySelectorAll('[data-ref-card]').length===3);
  assert.deepEqual(await page.evaluate(()=>refCalls),['flight-logs&geometry=1&folder=editor-scope']);
  const card=id=>page.locator(`[data-ref-card="${id}"]`);
  await card('mission:kmz').locator('[data-ref-pick]').check();assert.equal(await page.evaluate(()=>refLayers().length),2);
  await card('log:actual').locator('[data-ref-pick]').check();await page.waitForFunction(()=>refLayers().length===4);
  assert(await page.evaluate(()=>refLayers().every(l=>l.options.pmIgnore&&l.options.snapIgnore)),'references cannot edit/snap planner geometry');
  await card('mission:kmz').locator('[data-ref-visible]').uncheck();assert.equal(await page.evaluate(()=>refLayers().length),2);
  await card('mission:kmz').locator('[data-ref-visible]').check();
  await card('mission:kmz').locator('[data-ref-color]').evaluate(e=>{e.value='#00ff00';e.dispatchEvent(new Event('input',{bubbles:true}));});
  assert(await page.evaluate(()=>refLayers().some(l=>l.options.color==='#00ff00')));
  await page.locator('[data-ref-distance]').selectOption('1000');assert.equal(await page.locator('[data-ref-card]').count(),2,'nearby route rather than takeoff filter');
  await page.locator('[data-ref-distance]').selectOption('');await page.locator('[data-ref-search]').fill('mavic3');assert.equal(await page.locator('[data-ref-card]').count(),1);
  await page.locator('[data-ref-search]').fill('');await page.locator('[data-ref-mode]').selectOption('photo');assert.equal(await page.locator('[data-ref-card]').count(),1,'unknown logs never inherit photo from plan');
  await page.locator('[data-ref-mode]').selectOption('');
  await card('log:actual').locator('.flight-edit summary').click();await card('log:actual').locator('[data-ref-name]').fill('Ebenfurth Nord');await card('log:actual').locator('[data-ref-capture]').selectOption('video');await card('log:actual').locator('[data-ref-save]').click();
  await page.waitForFunction(()=>window.refSaved);assert.equal((await page.evaluate(()=>refSaved)).captureType,'video');assert.match(await card('log:actual').textContent(),/Ebenfurth Nord/);
  await card('log:slow').locator('[data-ref-pick]').check();await page.waitForFunction(()=>window.refResolve);await card('log:slow').locator('[data-ref-pick]').uncheck();await page.evaluate(()=>refResolve({track:[{lat:1,lng:2}]}));assert.equal(await page.evaluate(()=>refLayers().length),4,'deselected stale request ignored');
  assert.equal(await page.evaluate(()=>JSON.stringify(refMissions)===refBefore),true);
  await page.setViewportSize({width:390,height:844});
  assert(await page.locator('#ref-controls').evaluate(e=>e.scrollWidth<=e.clientWidth+1),'cards and filters fit a narrow screen');
  await page.setViewportSize({width:1280,height:900});
  assert(await page.evaluate(()=>dmFlightReferenceGeometry.distance([[[48,15],[48,17]]],{lat:48,lng:16})<1),'distance uses segment interior');
  assert(await page.evaluate(()=>dmFlightReferenceGeometry.inView([[[48,15],[48,17]]],L.latLngBounds([47.9,15.9],[48.1,16.1]))),'viewport crossing detected without vertices inside');
  await page.evaluate(()=>{refMap.remove();refMap=L.map('ref-map').setView([48,16],12);dmFlightReference(refMap,document.querySelector('#ref-controls'),{missions:refMissions,project:'project',request:refRequest});});
  await page.waitForFunction(()=>refLayers().length===4);assert(await page.evaluate(()=>refLayers().some(l=>l.options.color==='#00ff00')));
  await page.evaluate(()=>refMap.remove());assert.equal(await page.locator('#ref-controls > details').count(),0);
  console.log('PASS: multiple map references, cards, scoped search, distance/viewport, capture filter, rename, color, stale requests, persistence and unchanged mission data.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
