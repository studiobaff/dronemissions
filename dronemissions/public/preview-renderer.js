'use strict';
function dmPreviewRenderer(canvas,mission){
 const ctx=canvas.getContext('2d');let seq=0;
 const loadImage=src=>new Promise((resolve,reject)=>{const i=new Image();i.crossOrigin='anonymous';i.referrerPolicy='strict-origin-when-cross-origin';i.onload=()=>resolve(i);i.onerror=()=>reject(Error('Kartenkachel nicht erreichbar.'));i.src=src;});
 function title(s){ctx.fillStyle='#102830';ctx.fillRect(0,465,960,135);ctx.fillStyle='#fff';ctx.font='bold 29px sans-serif';ctx.textBaseline='top';let lines=[''];for(const word of s.title.split(/\s+/)){let i=lines.length-1;const next=(lines[i]+' '+word).trim();if(ctx.measureText(next).width>860&&lines[i])lines.push(word);else lines[i]=next;}if(lines.length>2)lines=[lines[0],lines.slice(1).join(' ')];const top=465+Math.max(0,(135-lines.length*39))/2;lines.forEach((line,i)=>{while(ctx.measureText(line).width>860&&line.length>1)line=line.slice(0,-2)+'…';ctx.fillText(line,50,top+i*39);});}
 function segments(){const pts=mission.details.points||[];return mission.details.routes?.length?mission.details.routes:[{start:0,count:pts.length}];}
 function routes(draw){const pts=mission.details.points||[];for(const r of segments()){ctx.beginPath();for(let j=r.start;j<r.start+r.count&&j<pts.length;j++){const [x,y]=draw(pts[j]);if(j===r.start)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.stroke();}}
 /* Wegpunktmarker wie in Web-Karte und Bridge: Start „1“ hell, Ende mit letzter Nummer dunkel, dazwischen kleine Punkte (bei vielen Punkten ausgedünnt). */
 function markers(draw,dark=true){const pts=mission.details.points||[],n=pts.length;if(!n)return;const stride=n<=60?1:n<=150?2:Math.max(3,Math.floor(n/60)),numbered=new Map([[0,'1'],[n-1,String(n)]]);for(const r of segments())if(r.start>0&&r.start<n-1)numbered.set(r.start,String(r.start+1));
 ctx.lineWidth=1.2;for(let i=0;i<n;i++){if(numbered.has(i)||i%stride)continue;const [x,y]=draw(pts[i]);ctx.beginPath();ctx.arc(x,y,3.4,0,Math.PI*2);ctx.fillStyle=dark?'#d9ff63':'#fff';ctx.strokeStyle=dark?'#0b2422':'#20392d';ctx.fill();ctx.stroke();}
 ctx.font='bold 12px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';for(const [i,text] of [...numbered].sort((a,b)=>a[0]-b[0])){const [x,y]=draw(pts[i]),r=text.length<3?12:15;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fillStyle=i===0?'#d9ff63':'#254e3b';ctx.strokeStyle='#fff';ctx.lineWidth=2.5;ctx.fill();ctx.stroke();ctx.fillStyle=i===0?'#17372b':'#fff';ctx.fillText(text,x,y+0.5);}ctx.textAlign='start';ctx.textBaseline='alphabetic';}
 function coordinates(){const p=mission.details.points||[];if(!p.length)throw new Error('Keine Route ausgelesen. Bitte eine DJI-KMZ zuordnen oder ein eigenes Bild wählen.');const fit=p.concat(mission.details.pois||[]);const lat=(Math.min(...fit.map(v=>v.lat))+Math.max(...fit.map(v=>v.lat)))/2,lng=(Math.min(...fit.map(v=>v.lng))+Math.max(...fit.map(v=>v.lng)))/2;return {p,lat,lng};}

 function drawPois(draw){ctx.save();ctx.font='bold 21px sans-serif';ctx.textBaseline='middle';for(const p of mission.details.pois||[]){const [x,y]=draw(p);ctx.beginPath();ctx.moveTo(x,y-10);ctx.lineTo(x+10,y);ctx.lineTo(x,y+10);ctx.lineTo(x-10,y);ctx.closePath();ctx.fillStyle='#b45ee3';ctx.fill();ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.stroke();const w=ctx.measureText(p.label).width+14,l=Math.max(5,Math.min(950-w,x+14)),t=Math.max(4,Math.min(410,y-16));ctx.fillStyle='#44245e';ctx.fillRect(l,t,w,30);ctx.fillStyle='#fff';ctx.fillText(p.label,l+7,t+15);}ctx.restore();}
 function three(s){const {p,lat,lng}=coordinates(),h0=Math.min(...p.map(v=>Number(v.height)||0)),a=s.yaw*Math.PI/180,b=s.pitch*Math.PI/180;
 const project=p=>{const x=(p.lng-lng)*111320*Math.cos(lat*Math.PI/180),y=(p.lat-lat)*111320,z=(Number(p.height)||0)-h0;return [x*Math.cos(a)-y*Math.sin(a),(x*Math.sin(a)+y*Math.cos(a))*Math.sin(b)-z*Math.cos(b)];};
 const pp=p.concat((mission.details.pois||[]).map(q=>({...q,height:h0}))).map(project),xs=pp.map(v=>v[0]),ys=pp.map(v=>v[1]),cx=(Math.min(...xs)+Math.max(...xs))/2,cy=(Math.min(...ys)+Math.max(...ys))/2,scale=Math.min(780/Math.max(1,Math.max(...xs)-Math.min(...xs)),350/Math.max(1,Math.max(...ys)-Math.min(...ys)))*s.zoom;
 ctx.strokeStyle='#294c46';ctx.lineWidth=1;for(let x=0;x<960;x+=80){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,465);ctx.stroke();}for(let y=0;y<465;y+=80){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(960,y);ctx.stroke();}
 const draw=p=>{const [x,y]=project(p);return [480+(x-cx)*scale+s.x,230+(y-cy)*scale+s.y];},heights=p.map(v=>Number(v.height)||0),hmax=Math.max(...heights),span=Math.max(hmax-h0,1);
 ctx.lineCap='round';ctx.lineJoin='round';ctx.strokeStyle='#0b2422';ctx.lineWidth=7;routes(draw);
 const edges=[];for(const r of segments())for(let j=r.start+1;j<r.start+r.count&&j<p.length;j++)edges.push(j);
 for(const j of edges){const t=((heights[j-1]+heights[j])/2-h0)/span,[x1,y1]=draw(p[j-1]),[x2,y2]=draw(p[j]);ctx.strokeStyle=`rgb(${Math.round(70+145*t)},${Math.round(190+34*t)},${Math.round(196-93*t)})`;ctx.lineWidth=3.8;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();}
 markers(draw,true);drawPois(q=>draw({...q,height:h0}));ctx.fillStyle='#b1c6bc';ctx.font='14px sans-serif';ctx.textAlign='right';ctx.fillText(p.some(v=>v.height==null)?'Draufsicht · für einzelne Punkte fehlt die Höhe':`3D · Höhe ${h0.toFixed(0)}–${hmax.toFixed(0)} m · ${p.length} Wegpunkte`,930,452);ctx.textAlign='start';}
 const merc=(lat,lng,z)=>{const n=256*2**z,phi=Math.max(-85,Math.min(85,lat))*Math.PI/180;return [(lng+180)/360*n,(1-Math.log(Math.tan(phi)+1/Math.cos(phi))/Math.PI)/2*n];};
 /* Kartenquellen wie in der Bridge: Österreich basemap.at (Luftbild mit Beschriftungs-Overlay), sonst OpenStreetMap bzw. Esri World Imagery. */
 function provider(s,lat,lng){const austria=lat>=46.35&&lat<=49.05&&lng>=9.45&&lng<=17.2,bm=l=>(z,x,y)=>`https://mapsneu.wien.gv.at/basemap/${l}/normal/google3857/${z}/${y}/${x}.${l==='bmaporthofoto30cm'?'jpeg':'png'}`;
 if(austria)return s.provider==='aerial'?{layers:[bm('bmaporthofoto30cm'),bm('bmapoverlay')],credit:'Datenquelle: basemap.at · CC BY 4.0 · basemap.at/#lizenz',maxZoom:19}:{layers:[bm('geolandbasemap')],credit:'Datenquelle: basemap.at · CC BY 4.0 · basemap.at/#lizenz',maxZoom:19};
 return s.provider==='aerial'?{layers:[(z,x,y)=>`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`],credit:'Luftbild: Esri World Imagery · Esri, Maxar, Earthstar Geographics, GIS User Community',maxZoom:18}:{layers:[(z,x,y)=>`https://${'abc'[(x+y)%3]}.tile.openstreetmap.org/${z}/${x}/${y}.png`],credit:'Karte: © OpenStreetMap-Mitwirkende · ODbL',maxZoom:19};}
 async function map(s,token){const {lat,lng}=coordinates(),src=provider(s,lat,lng),z=Math.min(Math.round(s.mapZoom),src.maxZoom),[cx,cy]=merc(lat,lng,z),ox=cx-(480-s.x)/s.zoom,oy=cy-(232-s.y)/s.zoom,tiles=[];
 for(let x=Math.floor(ox/256);x<=Math.floor((ox+960/s.zoom)/256);x++)for(let y=Math.floor(oy/256);y<=Math.floor((oy+465/s.zoom)/256);y++)for(const layer of src.layers)tiles.push({x,y,url:layer(z,x,y)});
 if(tiles.length>80*src.layers.length)throw new Error('Bitte den Zoom erhöhen.');const loaded=await Promise.all(tiles.map(async t=>({...t,img:await loadImage(t.url)})));if(token!==seq)return;
 for(const t of loaded)ctx.drawImage(t.img,(t.x*256-ox)*s.zoom,(t.y*256-oy)*s.zoom,256*s.zoom+1,256*s.zoom+1);const draw=p=>{const [x,y]=merc(p.lat,p.lng,z);return [(x-ox)*s.zoom,(y-oy)*s.zoom];};
 ctx.lineCap='round';ctx.lineJoin='round';ctx.strokeStyle='#20392d';ctx.lineWidth=8;routes(draw);ctx.strokeStyle='#d9ff63';ctx.lineWidth=4;routes(draw);markers(draw,false);drawPois(draw);
 ctx.textBaseline='alphabetic';ctx.fillStyle='rgba(255,255,255,.88)';ctx.fillRect(0,437,960,28);ctx.fillStyle='#223e35';ctx.font='15px sans-serif';ctx.fillText(src.credit,18,457);}
 function fitZoom(){const p=(mission?.details?.points||[]).concat(mission?.details?.pois||[]);if(!p.length)return 16;for(let z=19;z>2;z--){const xy=p.map(v=>merc(v.lat,v.lng,z)),xs=xy.map(v=>v[0]),ys=xy.map(v=>v[1]);if(Math.max(...xs)-Math.min(...xs)<=860&&Math.max(...ys)-Math.min(...ys)<=400)return z;}return 3;}

 return {fitZoom,cancel:()=>{seq++;},async render(s,photo=null){const token=++seq;ctx.fillStyle='#12372e';ctx.fillRect(0,0,960,600);if(s.mode==='3d')three(s);else if(s.mode==='map')await map(s,token);else{if(!photo)throw Error('Bitte ein Foto auswählen.');const scale=Math.max(960/photo.width,465/photo.height)*s.zoom;ctx.drawImage(photo,480-photo.width*scale/2+s.x,232-photo.height*scale/2+s.y,photo.width*scale,photo.height*scale);}if(token!==seq)return false;title(s);ctx.getImageData(0,0,1,1);return true;}};
}
function dmPreviewDefaults(mission){
 let preset=folderById(mission.folder)?.preview_effective||'auto';
 if(preset==='auto'){
  const type=mission.details.plannerType,heights=(mission.details.points||[]).map(p=>p.height).filter(Number.isFinite);
  preset=['helix','doubleHelix','circleGrid'].includes(type)?'3d':type==='grid'?'aerial':/helix|spiral/i.test(mission.name)?'3d':/raster|grid|polygon|polyflight/i.test(mission.name)?'aerial':heights.length&&Math.max(...heights)-Math.min(...heights)>5?'3d':'aerial';
 }
 return {mode:preset==='3d'?'3d':'map',provider:preset==='aerial'?'aerial':'map',title:mission.name,yaw:-35,pitch:25,zoom:1,x:0,y:0};
}

// Generate only visible, uncustomized thumbnails. Never overwrite saved title images.
(()=>{
 const cache=new Map(),queue=[];let running=0,scheduled=false;
 const visible=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){visible.unobserve(e.target);queue.push(e.target);}pump();},{rootMargin:'150px'});
 async function pump(){while(running<2&&queue.length){const image=queue.shift();if(!image.isConnected)continue;const job=image.dmPreviewJob;if(!job)continue;running++;
  (async()=>{try{let url=cache.get(job.key);if(!url){const canvas=document.createElement('canvas');canvas.width=960;canvas.height=600;const renderer=dmPreviewRenderer(canvas,job.mission);await renderer.render({...job.settings,mapZoom:renderer.fitZoom()});url=canvas.toDataURL('image/jpeg',.86);cache.set(job.key,url);if(cache.size>60)cache.delete(cache.keys().next().value);}
   if(image.isConnected&&image.dmPreviewJob===job){image.src=url;image.alt=job.settings.mode==='3d'?'3D-Flugroute':job.settings.provider==='aerial'?'Luftbild mit Flugroute':'Karte mit Flugroute';image.title=image.alt;image.dataset.previewRendered=job.settings.mode==='3d'?'3d':job.settings.provider;}
  }catch(error){if(image.isConnected&&image.dmPreviewJob===job){image.alt='Flugroute · Kartenvorschau nicht erreichbar';image.title='Kartenvorschau nicht erreichbar. Die einfache Routenvorschau bleibt sichtbar.';}}
  finally{running--;pump();}})();
 }}
 function scan(){scheduled=false;if(typeof data==='undefined'||!data||!canEdit())return;for(const image of document.querySelectorAll('img[data-mission-preview]')){
  const mission=data.missions.find(m=>m.id===image.dataset.missionPreview);if(!mission||mission.hasCustomPreview||!mission.details.points?.length)continue;
  const settings=dmPreviewDefaults(mission),key=JSON.stringify([mission.id,mission.versionId,mission.revision,settings]);if(image.dmPreviewJob?.key===key)continue;
  image.dmPreviewJob={mission,settings,key};visible.observe(image);
 }}
 new MutationObserver(()=>{if(!scheduled){scheduled=true;requestAnimationFrame(scan);}}).observe(document.body,{childList:true,subtree:true});scan();
})();
