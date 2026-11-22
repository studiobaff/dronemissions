const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const [base,accessPath]=process.argv.slice(2);assert.equal(new URL(base).hostname,'127.0.0.1');
 const access=JSON.parse(fs.readFileSync(accessPath,'utf8'));const browser=await chromium.launch({headless:true});
 const context=await browser.newContext();let csrf;
 const api=async(action,body)=>{const r=await context.request.fetch(base+'api.php?action='+action,{method:body?'POST':'GET',headers:body?{'X-CSRF-Token':csrf}:{},data:body});assert(r.ok(),action+': '+await r.text());return r.json();};
 let original;
 try{
  csrf=(await api('session')).csrf;await api('login',{email:access.email});
  const mail=fs.readFileSync(access.mailbox,'utf8'),part=mail.match(/Content-Type: text\/plain;[\s\S]*?\r\n\r\n([\s\S]*?)\r\n--/)[1],code=Buffer.from(part,'base64').toString('utf8').match(/Anmeldecode für Drone Missions: (\d{6})/)[1];csrf=(await api('login-verify',{code})).csrf;
  original=await api('settings');await api('settings',{...original,googleMapsEnabled:true,googleMapsKey:'synthetic-google-browser-key-1234567890'});
  let requests=0;
  const sdk=`window.google={maps:{RenderingType:{RASTER:'RASTER'},event:{trigger(){},clearInstanceListeners(){}},Map:class{constructor(node,opts){this.opts=opts;window.lastGoogleMap=this;node.textContent='Synthetic Google renderer';}setCenter(c){this.center=c;}setZoom(z){this.zoom=z;}}}};window.dmGoogleReady();`;
  await context.route('https://maps.googleapis.com/maps/api/js?*',r=>{requests++;return r.fulfill({contentType:'application/javascript',body:sdk});});
  const page=await context.newPage();await page.goto(base);await page.waitForFunction(()=>window.dmGoogleLayers);
  assert.equal(requests,0,'SDK is not loaded for ordinary base maps');
  await page.evaluate(()=>{const d=document.createElement('div');d.style.cssText='position:fixed;inset:0;z-index:9999';document.body.append(d);window.testMap=L.map(d).setView([48,16],12);window.testLayers=dmGoogleLayers('synthetic-google-browser-key-1234567890');testLayers['Google · Satellit'].addTo(testMap);});
  await page.waitForFunction(()=>window.lastGoogleMap?.zoom===12);
  await page.evaluate(()=>testMap.setView([48.1,16.1],14,{animate:false}));
  await page.waitForFunction(()=>lastGoogleMap.zoom===14&&Math.abs(lastGoogleMap.center.lat-48.1)<1e-6);
  assert.equal(await page.evaluate(()=>lastGoogleMap.opts.mapTypeId),'satellite');
  await page.evaluate(()=>{testMap.removeLayer(testLayers['Google · Satellit']);testLayers['Google · Karte'].addTo(testMap);});
  await page.waitForFunction(()=>lastGoogleMap.opts.mapTypeId==='roadmap');assert.equal(requests,1,'SDK loaded only once');
  await page.evaluate(()=>testMap.remove());assert.equal(await page.locator('.dm-google-map').count(),0,'renderer removed');
  const bad=await context.newPage();await bad.route('https://maps.googleapis.com/maps/api/js?*',r=>r.fulfill({contentType:'application/javascript',body:'window.gm_authFailure();'}));await bad.goto(base);await bad.waitForFunction(()=>window.dmGoogleLayers);
  await bad.evaluate(()=>{const d=document.createElement('div');d.style.cssText='height:400px';document.body.append(d);window.badMap=L.map(d).setView([48,16],12);window.badLayers=dmGoogleLayers('synthetic-google-browser-key-1234567890');badMap.on('googlemaperror',()=>{window.authErrorReported=true;badMap.removeLayer(badLayers['Google · Karte']);});badLayers['Google · Karte'].addTo(badMap);});
  await bad.waitForFunction(()=>window.authErrorReported);assert.equal(await bad.evaluate(()=>badMap.dmGoogleActive),false);
  console.log('PASS: optional Google SDK, CSP nonce, satellite/road selection, pan/zoom sync, single loader, cleanup and authentication failure. No real Google request.');
 }finally{if(original)await api('settings',{...original,googleMapsEnabled:false,googleMapsRemoveKey:true});await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
