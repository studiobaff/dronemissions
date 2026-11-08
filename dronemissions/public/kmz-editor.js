'use strict';
// Separate from the parametric planner: edit a copy of the latest archived DJI route.
(() => {
 const dlg=document.createElement('dialog');dlg.id='ke-dialog';dlg.className='dialog ke-dialog';dlg.setAttribute('aria-label','KMZ bearbeiten');
 dlg.innerHTML=`<header class="ke-head"><div><strong>KMZ bearbeiten</strong><div id="ke-title" class="hint"></div></div><button type="button" class="btn btn-icon" id="ke-close" aria-label="KMZ-Editor schließen">×</button></header>
 <div class="ke-tools"><button class="btn btn-outline" id="ke-undo" title="Letzte Änderung zurücknehmen">↶ Rückgängig</button><button class="btn btn-outline" id="ke-redo">↷ Wiederholen</button><button class="btn btn-outline" id="ke-fit">Route zentrieren</button><span id="ke-count" role="status"></span></div>
 <div class="ke-body"><aside><label class="field">Wegpunkt<select id="ke-point"></select></label><div class="ke-navigation"><button class="btn btn-outline" id="ke-prev" aria-label="Vorheriger Wegpunkt">←</button><button class="btn btn-outline" id="ke-next" aria-label="Nächster Wegpunkt">→</button></div>
 <label class="field">Breitengrad<input id="ke-lat" type="number" min="-85" max="85" step="any"></label><label class="field">Längengrad<input id="ke-lng" type="number" min="-180" max="180" step="any"></label><label class="field">Höhe · m<input id="ke-height" type="number" min="-1000" max="10000" step="any"></label><p id="ke-datum" class="hint"></p>

 <button class="btn btn-outline" id="ke-insert">Zwischenpunkt danach einfügen</button><button class="btn btn-outline" id="ke-delete">Wegpunkt löschen</button><p id="ke-structure-note" class="hint"></p>
 <div class="ke-nudge" aria-label="Wegpunkt um einen Meter verschieben"><button class="btn btn-outline" data-ke-move="north" title="1 m nach Norden">↑</button><button class="btn btn-outline" data-ke-move="west" title="1 m nach Westen">←</button><span>1 m</span><button class="btn btn-outline" data-ke-move="east" title="1 m nach Osten">→</button><button class="btn btn-outline" data-ke-move="south" title="1 m nach Süden">↓</button></div>
 <p id="ke-point-info" class="hint"></p><details><summary>Hinweise zur Bearbeitung</summary><p class="hint">Marker ziehen oder Werte ändern. Kameraaktionen und POIs bleiben erhalten; Ausrichtung, Gimbal und Hindernisabstände werden nicht neu berechnet. Neue Zwischenpunkte erhalten keine Kameraaktionen. Beim Löschen entfallen die Aktionen dieses Punktes. Nach Einfügen/Löschen den Punkt für die Projektkarte neu wählen.</p><p class="hint">Die Route ist eine Verbindung der Wegpunkte, keine Simulation der geflogenen Kurven. Neue Version vor dem Flug in DJI Fly prüfen.</p></details></aside>
 <div id="ke-map" aria-label="KMZ-Wegpunktkarte"></div></div>
 <footer class="ke-footer"><span id="ke-status" role="status">Original bleibt erhalten.</span><button class="btn btn-primary" id="ke-save">Als neue Version speichern</button></footer>`;
 document.body.append(dlg);
 const el=id=>document.getElementById('ke-'+id);let source=null,points=[],cursor=0,map=null,route=null,markers=[],past=[],future=[],busy=false;
 const status=(text,error=false)=>{el('status').textContent=text;el('status').classList.toggle('error',error);};
 const payload=()=>({changes:points.filter(p=>p.index!==null&&['lat','lng','height'].some(k=>p[k]!==source.points[p.index][k])).map(p=>({index:p.index,lat:p.lat,lng:p.lng,height:p.height})),deletions:source.points.filter(p=>!points.some(q=>q.index===p.index)).map(p=>p.index),insertions:points.filter(p=>p.index===null).map(p=>({after:p.after,lat:p.lat,lng:p.lng,height:p.height}))});
 const dirty=()=>source&&Object.values(payload()).some(a=>a.length);
 const snapshot=()=>({points:structuredClone(points),cursor});
 function remember(){past.push(snapshot());if(past.length>50)past.shift();future=[];}
 function fields(){const p=points[cursor];if(!p)return;for(const k of ['lat','lng','height'])el(k).value=String(p[k]);el('point').value=String(cursor);const info=p.index===null?null:source.pointInfo?.[p.index];el('point-info').textContent=info?['Aktionen: '+(info.actions.join(', ')||'keine'),info.headingMode?'Ausrichtung: '+info.headingMode+(info.heading!==null?' · '+info.heading+'°':''):'',info.gimbalPitch!==null?'Gimbal: '+info.gimbalPitch+'°':''].filter(Boolean).join(' · '):'Neuer Zwischenpunkt ohne Kameraaktionen.';el('prev').disabled=busy||cursor===0;el('next').disabled=busy||cursor===points.length-1;el('delete').disabled=busy||points.length<=2||!source.structureEditable;el('insert').disabled=busy||!source.structureEditable||cursor===points.length-1||p.index===null||points[cursor+1]?.index===null;}
 function render(){
  el('point').replaceChildren(...points.map((p,i)=>new Option(`${i+1} · ${p.height.toLocaleString('de-AT')} m${p.index===null?' · neu':''}`,String(i))));fields();
  el('undo').disabled=busy||!past.length;el('redo').disabled=busy||!future.length;el('save').disabled=busy||!dirty();el('count').textContent=points.length+' Wegpunkte'+(dirty()?' · ungespeicherte Änderungen':'');
  markers.forEach(m=>m.remove());markers=[];if(route)route.remove();route=L.polyline(points.map(p=>[p.lat,p.lng]),{color:'#b3bc28',weight:3}).addTo(map);
  points.forEach((p,i)=>{const marker=L.marker([p.lat,p.lng],{draggable:!busy,zIndexOffset:i===cursor?1000:0,icon:L.divIcon({className:'ke-marker'+(i===cursor?' ke-selected':''),html:String(i+1),iconSize:[26,26],iconAnchor:[13,13]})}).addTo(map).bindTooltip(`${i+1} · ${p.height.toLocaleString('de-AT')} m · ${source.heightMode==='WGS84'?'WGS84-Ellipsoid':'relativ Start'}`);
   marker.on('click',()=>{cursor=i;render();});marker.on('dragstart',()=>{cursor=i;remember();});marker.on('dragend',()=>{const pos=marker.getLatLng();if(Math.abs(pos.lat)>85||Math.abs(pos.lng)>180){const old=past.pop();points=old.points;cursor=old.cursor;status('Position außerhalb des unterstützten Bereichs.',true);}else{p.lat=Number(pos.lat.toFixed(9));p.lng=Number(pos.lng.toFixed(9));status('Position geändert. Noch nicht gespeichert.');}render();});markers.push(marker);
  });
 }
 function apply(){if(busy)return false;const next={};for(const k of ['lat','lng','height']){if(!el(k).value||!el(k).checkValidity()){el(k).reportValidity();status('Position und Höhe prüfen.',true);return false;}next[k]=Number(el(k).value);}
  if(Object.keys(next).some(k=>next[k]!==points[cursor][k])){remember();Object.assign(points[cursor],next);render();status('Wegpunkt geändert. Noch nicht gespeichert.');}return true;
 }
 for(const k of ['lat','lng','height']){el(k).addEventListener('change',apply);el(k).addEventListener('blur',apply);el(k).addEventListener('input',()=>{const valid=['lat','lng','height'].every(n=>el(n).value!==''&&el(n).checkValidity());el('save').disabled=busy||!valid||(!dirty()&&!['lat','lng','height'].some(n=>Number(el(n).value)!==points[cursor][n]));});}
 el('point').onchange=()=>{cursor=Number(el('point').value);render();};el('prev').onclick=()=>{cursor=Math.max(0,cursor-1);render();};el('next').onclick=()=>{cursor=Math.min(points.length-1,cursor+1);render();};
 el('undo').onclick=()=>{if(!past.length||busy)return;future.push(snapshot());const s=past.pop();points=s.points;cursor=s.cursor;render();status('Änderung zurückgenommen.');};el('redo').onclick=()=>{if(!future.length||busy)return;past.push(snapshot());const s=future.pop();points=s.points;cursor=s.cursor;render();status('Änderung wiederhergestellt.');};
 dlg.querySelectorAll('[data-ke-move]').forEach(button=>button.onclick=()=>{if(busy)return;const p=points[cursor],direction=button.dataset.keMove;remember();if(direction==='north'||direction==='south')p.lat+=(direction==='north'?1:-1)/111319.490793;else p.lng+=(direction==='east'?1:-1)/(111319.490793*Math.cos(p.lat*Math.PI/180));if(Math.abs(p.lat)>85||Math.abs(p.lng)>180){points=past.pop().points;status('Position außerhalb des unterstützten Bereichs.',true);}render();});
 el('insert').onclick=()=>{if(el('insert').disabled)return;remember();const a=points[cursor],b=points[cursor+1];points.splice(cursor+1,0,{index:null,after:a.index,lat:(a.lat+b.lat)/2,lng:(a.lng+b.lng)/2,height:(a.height+b.height)/2});cursor++;render();status('Zwischenpunkt ohne Kameraaktionen eingefügt. Noch nicht gespeichert.');};
 el('delete').onclick=()=>{if(el('delete').disabled)return;const p=points[cursor];if(p.index!==null&&points.some(q=>q.after===p.index)){status('Zuerst den danach eingefügten Zwischenpunkt entfernen.',true);return;}remember();points.splice(cursor,1);cursor=Math.min(cursor,points.length-1);render();status('Wegpunkt und seine Aktionen entfernt. Noch nicht gespeichert.');};
 el('fit').onclick=()=>map.fitBounds(route.getBounds(),{padding:[45,45],maxZoom:19});
 window.addEventListener('beforeunload',e=>{if(dlg.open&&dirty()){e.preventDefault();e.returnValue='';}});
 function close(){if(busy)return;if(dirty()&&!confirm('Ungespeicherte Wegpunktänderungen verwerfen?'))return;dlg.close();}
 el('close').onclick=close;dlg.addEventListener('cancel',e=>{e.preventDefault();close();});dlg.addEventListener('close',()=>{map?.remove();map=null;source=null;});
 // Prevent the shared backdrop handler from discarding an editor with unsaved changes.
 dlg.addEventListener('click',e=>{if(e.target===dlg)e.stopPropagation();});
 el('save').onclick=async()=>{if(busy||!apply()||!dirty())return;busy=true;render();dlg.querySelectorAll('input,select,[data-ke-move]').forEach(n=>n.disabled=true);status('Neue Archivversion wird geprüft und gespeichert …');
  try{const response=await api('kmz-edit-save',{id:source.id,revision:source.revision,version:source.version,sha256:source.sha256,...payload()});const id=source.id;busy=false;dlg.close();if($('#detail-dialog').open)$('#detail-dialog').close();await refresh();await openMission(id);toast(`Version ${response.version} gespeichert. Original und ältere Versionen bleiben erhalten.`);}
  catch(e){busy=false;status(e.message,true);dlg.querySelectorAll('input,select,[data-ke-move]').forEach(n=>n.disabled=false);render();}
 };
 window.dmKmzEditor={open:async id=>{
  if(!canEdit())return;const loaded=await api('kmz-edit-load&id='+encodeURIComponent(id));source=loaded;points=structuredClone(loaded.points);cursor=0;past=[];future=[];busy=false;
  el('title').textContent=loaded.name+' · Ausgangsversion '+loaded.ordinal;el('datum').textContent=loaded.heightMode==='WGS84'?'Höhen über dem WGS84-Ellipsoid; kein AGL.':'Höhen relativ zum ursprünglichen Startpunkt; kein AGL.';el('structure-note').textContent=loaded.structureEditable?'Einfügen und Löschen mit Rückgängig.':'Einfügen/Löschen bei verknüpften oder unbekannten Aktionen gesperrt.';
  dlg.querySelectorAll('input,select,[data-ke-move]').forEach(n=>n.disabled=false);dlg.showModal();dlg.querySelector('aside').scrollTop=0;map=L.map('ke-map');tiles(map,loaded.folder);route=null;markers=[];
  for(const poi of loaded.pois||[])L.circleMarker([poi.lat,poi.lng],{radius:7,color:'#b45ee3',fillOpacity:.8}).addTo(map).bindTooltip(document.createTextNode(poi.label||'POI'));
  render();map.fitBounds(route.getBounds(),{padding:[45,45],maxZoom:19});status('Original bleibt erhalten. Änderungen werden als neue Version gespeichert.');
 }};
})();
