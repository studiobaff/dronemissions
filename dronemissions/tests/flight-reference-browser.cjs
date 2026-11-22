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
   const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;z-index:9999;background:white';host.innerHTML='<div id="ref-map" style="height:350px"></div><div id="ref-controls"></div>';document.body.append(host);
   window.refMap=L.map('ref-map').setView([48,16],12);window.refCalls=[];
   window.refMissions=[{id:'kmz',name:'Test Raster',folder:'project',details:{sourceFormat:'dji-kmz',points:[{lat:48,lng:16},{lat:48.01,lng:16},{lat:48.1,lng:16.1},{lat:48.11,lng:16.1}],routes:[{start:0,count:2},{start:2,count:2}]}}];window.refBefore=JSON.stringify(refMissions);
   window.refRequest=async action=>{refCalls.push(action);if(action.startsWith('flight-logs'))return {logs:[{id:'actual',folder:'project',summary:{model:'Mavic 3 Cine',startTime:'2026-10-16T10:00:00Z'}},{id:'slow',summary:{name:'Delayed'}}]};if(action.endsWith('slow'))return new Promise(resolve=>window.refResolve=resolve);return {track:[{lat:48,lng:16,time:0},{lat:48.01,lng:16,time:1},{lat:48.1,lng:16,time:50},{lat:48.11,lng:16,time:51}]};};
   dmFlightReference(refMap,document.querySelector('#ref-controls'),{missions:refMissions,scope:'editor-scope',project:'project',request:refRequest});
   window.refLayers=()=>Object.values(refMap._layers).filter(l=>l instanceof L.Path&&l.options?.pane==='flightReference');
  });
  await page.locator('.map-flight-reference summary').click();
  await page.waitForFunction(()=>document.querySelector('[data-ref-select]').options.length===4);
  assert.deepEqual(await page.evaluate(()=>refCalls),['flight-logs&folder=editor-scope']);
  await page.locator('[data-ref-select]').selectOption('mission:kmz');
  assert.equal(await page.evaluate(()=>refLayers().length),2,'separate planned routes are not joined');
  assert.equal(await page.evaluate(()=>refLayers().every(l=>l.options.pmIgnore&&l.options.snapIgnore&&!l.options.interactive)),true);
  await page.locator('[data-ref-visible]').uncheck();assert.equal(await page.evaluate(()=>refLayers().length),0);
  await page.locator('[data-ref-visible]').check();assert.equal(await page.evaluate(()=>refLayers().length),2);
  await page.locator('[data-ref-color]').evaluate(e=>{e.value='#00ff00';e.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(await page.evaluate(()=>refLayers()[0].options.color),'#00ff00');
  await page.locator('[data-ref-search]').fill('mavic3');assert.equal(await page.locator('[data-ref-select] option').count(),3,'search retains current selection');
  await page.locator('[data-ref-select]').selectOption('log:actual');await page.waitForFunction(()=>refLayers().length===2);
  assert.equal(await page.evaluate(()=>refLayers().every(l=>!l.options.dashArray)),true,'actual track is solid and split at gaps');
  await page.locator('[data-ref-search]').fill('');await page.locator('[data-ref-select]').selectOption('log:slow');
  await page.waitForFunction(()=>window.refResolve);await page.locator('[data-ref-select]').selectOption('mission:kmz');
  await page.evaluate(()=>refResolve({track:[{lat:1,lng:2}]}));
  assert.equal(await page.evaluate(()=>refLayers().length),2,'stale response cannot replace selected reference');
  assert.equal(await page.evaluate(()=>JSON.stringify(refMissions)===refBefore),true,'mission data unchanged');
  await page.evaluate(()=>{refMap.remove();refMap=L.map('ref-map').setView([48,16],12);dmFlightReference(refMap,document.querySelector('#ref-controls'),{missions:refMissions,project:'project',request:refRequest});});
  assert.equal(await page.locator('[data-ref-select]').inputValue(),'mission:kmz');assert.equal(await page.evaluate(()=>refLayers()[0].options.color),'#00ff00');
  await page.evaluate(()=>refMap.remove());assert.equal(await page.locator('.map-flight-reference').count(),0);
  console.log('PASS: scoped reference search, separate KMZ routes, actual track gaps, visibility/color, stale requests, persistence, cleanup and unchanged mission data.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
