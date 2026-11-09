'use strict';
let mapPointPick=null,dmPermitKeepView=false;
const dmCaptureNames={photo:'Foto',video:'Video',panorama:'Panorama',sphere:'Kugelpanorama'};
function dmCaptureIcon(type){const paths={photo:'<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M7 6l2-3h6l2 3"/><circle cx="12" cy="13" r="4"/>',video:'<rect x="2" y="6" width="13" height="12" rx="2"/><path d="M15 10l7-4v12l-7-4z"/>',panorama:'<path d="M2 5q10 4 20 0v14q-10-4-20 0z"/><path d="M4 15l5-5 5 4 3-2 3 3"/>',sphere:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6q7 5 14 0M5 18q7-5 14 0"/>'};return '<svg viewBox="0 0 24 24" aria-hidden="true">'+(paths[type]||paths.photo)+'</svg>';}
const dmIsMapOnly=()=>data.presentation==='map'||new URLSearchParams(location.search).get('map')==='1';
function dmDrawPermitMission(map,m,group,coords){
 const start=m.takeoffPoint,pano=m.panoPoint;if(!start&&!pano)return false;
 const index=visibleMissions().findIndex(x=>x.id===m.id)+1;
 const add=(p,kind,text)=>{coords.push([p.lat,p.lng]);L.marker([p.lat,p.lng],{icon:L.divIcon({className:'permit-marker '+kind,html:`<span>${kind==='start'?'H':dmCaptureIcon(m.captureType)}<small>${index}</small></span>`,iconSize:[34,30],iconAnchor:[17,15]}),keyboard:true,title:`${m.name} · ${kind==='start'?'Startplatz':'Aufnahme / Wegpunkt 2 · '+(dmCaptureNames[m.captureType]||'Foto')}`}).addTo(group).bindTooltip(esc(m.name)+' · '+(kind==='start'?'Startplatz':'Aufnahmepunkt / Wegpunkt 2')).bindPopup(`<strong>${esc(m.name)}</strong><p>${kind==='start'?'Startplatz am Boden':'Aufnahmepunkt · Wegpunkt 2'}<br>${Number(p.lat).toFixed(6)}, ${Number(p.lng).toFixed(6)}</p>`);};
 if(start)add(start,'start','H');if(pano)add(pano,'pano','P2');
 if(start&&pano)L.polyline([[start.lat,start.lng],[pano.lat,pano.lng]],{color:'#365c49',weight:2.5,dashArray:'7 7',opacity:.9,interactive:false}).addTo(group);
 return true;
}
function dmRenderPermitTools(){
 document.body.classList.toggle('permit-map-active',showMap);const rows=visibleMissions(),select=$('#permit-mission'),old=select.value;select.innerHTML='<option value="">Mission auswählen …</option>'+rows.map(m=>`<option value="${m.id}">${esc(m.name)}${m.panoPoint?'':' · Wegpunkt 2 nicht verfügbar'}</option>`).join('');if(rows.some(m=>m.id===old))select.value=old;$('#permit-type').value=rows.find(m=>m.id===select.value)?.captureType||'photo';
 $('#permit-tools').classList.toggle('hidden',!showMap);
 for(const id of ['permit-mission-label','permit-type-label','permit-set-start','permit-clear-start'])$('#'+id).classList.toggle('hidden',!canEdit()||dmIsMapOnly());
 $('#permit-auth').classList.toggle('hidden',!dmIsMapOnly());$('#permit-share').classList.toggle('hidden',!isOwner()||dmIsMapOnly());
 const coordinate=p=>p?`${Number(p.lat).toFixed(6)}, ${Number(p.lng).toFixed(6)}`:'Nicht festgelegt';
 $('#permit-print-list').innerHTML=`<h2>${esc(folder?pathFor(folder):'Freigabekarte')}</h2><p>Startplatz am Boden (H) und Aufnahmepunkt / Wegpunkt 2 (P2). Gestrichelte Linie = Zuordnung, keine vermessene Flugroute.</p><table><thead><tr><th>Nr.</th><th>Mission / Aufnahmeart</th><th>Startplatz · Breite, Länge</th><th>Aufnahme / Wegpunkt 2 · Breite, Länge</th></tr></thead><tbody>${rows.map((m,i)=>`<tr><td>${i+1}</td><td>${esc(m.name)} · ${esc(dmCaptureNames[m.captureType]||'Foto')}</td><td>${coordinate(m.takeoffPoint)}</td><td>${coordinate(m.panoPoint)}</td></tr>`).join('')}</tbody></table><p>Koordinaten WGS84. Naturschutz: Umweltbundesamt / INSPIRE-Dienste der Bundesländer, Stand 2025, CC BY 4.0. Darstellung und bekannte Datenlücken ersetzen keine Prüfung bei der zuständigen Behörde. Keine Flugfreigabe. Erstellt ${new Date().toLocaleString('de-AT')}.</p>`;
}
async function dmPickStart(latlng){
 const id=mapPointPick;if(!id)return;mapPointPick=null;$('#overview-map').classList.remove('picking');const m=data.missions.find(x=>x.id===id);if(!m)return;
 await run(async()=>{await api('mission-start',{id:m.id,revision:m.revision,lat:latlng.lat,lng:latlng.lng});dmPermitKeepView=true;await refresh();$('#permit-mission').value=id;$('#permit-hint').textContent=m.panoPoint?'Startplatz gespeichert. Die gestrichelte Linie führt zu Wegpunkt 2.':'Startplatz gespeichert. Für den Aufnahmepunkt fehlt eine auslesbare Mission mit Wegpunkt 2; bitte den passenden KMZ-Export ergänzen.';});
}
function dmApplyPermitView(){
 const only=dmIsMapOnly();document.body.classList.toggle('map-only',only);if(!only)return;
 if(data.scope){folder=data.scope;view='folder';}filter='all';$('#search').value='';showMap=true;render();
 const center=new URLSearchParams(location.search).get('center')?.split(',').map(Number);if(center?.length===3&&center.every(Number.isFinite)&&Math.abs(center[0])<=90&&Math.abs(center[1])<=180&&center[2]>=3&&center[2]<=19)setTimeout(()=>overview.setView([center[0],center[1]],center[2]),150);
 setTimeout(()=>overview?.dmNature?.enable(),200);
}
function dmBeginStartPick(id){if(!id){toast('Bitte zuerst eine Mission auswählen.',true);return;}if(picking)stopPicking();mapPointPick=mapPointPick===id?null:id;$('#permit-mission').value=id;$('#overview-map').classList.toggle('picking',Boolean(mapPointPick));$('#permit-hint').textContent=mapPointPick?'Klicke auf den Startplatz am Boden (Kreis mit H). Die Flugwegpunkte bleiben unverändert.':'Startplatz-Auswahl beendet.';}
function dmInitPermitMap(){
 $('#permit-mission').onchange=()=>{$('#permit-type').value=data.missions.find(m=>m.id===$('#permit-mission').value)?.captureType||'photo';};
 $('#permit-type').onchange=()=>run(async()=>{const m=data.missions.find(m=>m.id===$('#permit-mission').value);if(!m)throw Error('Bitte zuerst eine Mission auswählen.');const id=m.id;await api('mission-map-type',{id,revision:m.revision,captureType:$('#permit-type').value});dmPermitKeepView=true;await refresh();$('#permit-mission').value=id;toast('Aufnahmeart für die Karte gespeichert.');});

 $('#permit-auth').onclick=()=>run(async()=>{await api('logout',{});location.href='./';});
 $('#permit-set-start').onclick=()=>dmBeginStartPick($('#permit-mission').value);
 $('#permit-clear-start').onclick=()=>run(async()=>{const id=$('#permit-mission').value,m=data.missions.find(x=>x.id===id);if(!m)throw Error('Bitte zuerst eine Mission auswählen.');await api('mission-start',{id,revision:m.revision,lat:null,lng:null});dmPermitKeepView=true;await refresh();$('#permit-hint').textContent='Startplatz entfernt; die Missionsdatei bleibt unverändert.';});
 $('#permit-fit').onclick=()=>{dmPermitKeepView=false;renderOverview();};
 $('#permit-print').onclick=()=>run(async()=>{if(overview?.dmNature&&!overview.dmNature.enabled()){overview.dmNature.enable();throw Error('Naturschutz wird geladen. Danach erneut „PDF herunterladen“ wählen.');}if(overview?.dmNature&&!overview.dmNature.ready())throw Error('Naturschutz ist noch nicht vollständig geladen. Bitte Status im Kartenpanel prüfen.');dmRenderPermitTools();const button=$('#permit-print');button.disabled=true;try{await dmDownloadPermitPDF(overview,folder?pathFor(folder):'Freigabekarte',visibleMissions());toast('PDF mit Karte und Koordinatenliste erstellt.');}finally{button.disabled=false;}});
 $('#permit-share').onclick=e=>run(async()=>{if(!folder)throw Error('Bitte zuerst das Projekt öffnen, dessen Karte geteilt werden soll.');const d=await api('share',{folder,role:'view',presentation:'map'}),u=new URL('./',location.href),c=overview.getCenter();u.searchParams.set('map','1');u.searchParams.set('nature','1');u.searchParams.set('center',`${c.lat.toFixed(6)},${c.lng.toFixed(6)},${overview.getZoom()}`);u.hash=`share=${d.token}`;await openShares();$('#share-link').value=u.href;$('#share-link-wrap').classList.remove('hidden');$('#share-link').focus();$('#share-link').select();toast('Reiner Kartenlink erstellt: Startplätze, Wegpunkt 2 und Naturschutz. Keine Missionsdateien.');},e.currentTarget);
 let printView=null;window.addEventListener('beforeprint',()=>{if(overview){printView={center:overview.getCenter(),zoom:overview.getZoom()};overview.invalidateSize({pan:false});overview.setView(printView.center,printView.zoom,{animate:false});}});window.addEventListener('afterprint',()=>{if(overview){overview.invalidateSize({pan:false});if(printView)overview.setView(printView.center,printView.zoom,{animate:false});}});
}
