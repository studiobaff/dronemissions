'use strict';
/* Drone Missions · Freigabekarte als Bild und PDF
   dmPermitCanvas: Kartenkacheln, Vektorebenen (Schutzgebiete, Geozonen, Routen) und die Marker in der Formsprache der Oberfläche.
   dmBuildPermitPDF: A4 quer. Seite 1 Kopf (Titel, Untertitel, Betreiber, Logo) · Karte · Legende · Quellen; ab Seite 2 Tabellen
   (Projekt: Kennung | Mission | Aufnahmeart | Startplatz | Aufnahmepunkt | Höhe; Einzelmission: Wegpunkte) mit wiederholter Kopfzeile.
   Schrift: DejaVu Sans als eingebettetes Unicode-Subset (permit-font.js), daher auch Ukrainisch. Keine Bedien- oder Statustexte im PDF. */
const DM_PDF={start:'#1f5fbf',capture:'#c4551c',link:'#243a4d',ink:'#19342f',muted:'#687a70',line:'#cbd4c3',soft:'#f1f4ec',route:'#7f9c2a',nature:'#2a985b',zone:'#b96a16'};
function dmRoundedRect(ctx,x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();}
function dmCanvasCaptureIcon(ctx,type){ctx.beginPath();if(type==='sphere'){ctx.arc(0,0,7,0,Math.PI*2);ctx.moveTo(-7,0);ctx.lineTo(7,0);ctx.moveTo(3,0);ctx.ellipse(0,0,3,7,0,0,Math.PI*2);}else if(type==='video'){ctx.rect(-8,-5,11,10);ctx.moveTo(3,-2);ctx.lineTo(8,-5);ctx.lineTo(8,5);ctx.lineTo(3,2);}else if(type==='panorama'){ctx.moveTo(-8,-6);ctx.quadraticCurveTo(0,-3,8,-6);ctx.lineTo(8,6);ctx.quadraticCurveTo(0,3,-8,6);ctx.closePath();ctx.moveTo(-6,3);ctx.lineTo(-2,-1);ctx.lineTo(1,2);ctx.lineTo(3,0);ctx.lineTo(6,3);}else{ctx.rect(-8,-5,16,11);ctx.moveTo(-4,-5);ctx.lineTo(-2,-8);ctx.lineTo(2,-8);ctx.lineTo(4,-5);ctx.moveTo(3,1);ctx.arc(0,1,3,0,Math.PI*2);}ctx.stroke();}
function dmCanvasLabel(ctx,text,x,y,color){ctx.font='bold 8px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';const width=Math.max(18,ctx.measureText(text).width+8);ctx.fillStyle='#fff';ctx.strokeStyle=color;ctx.lineWidth=1;dmRoundedRect(ctx,x-width/2,y,width,12,6);ctx.fill();ctx.stroke();ctx.fillStyle=color;ctx.fillText(text,x,y+6.5);}
async function dmPermitCanvas(map,missions){
 const element=map.getContainer(),bounds=element.getBoundingClientRect(),scale=2,canvas=document.createElement('canvas');canvas.width=Math.round(bounds.width*scale);canvas.height=Math.round(bounds.height*scale);const ctx=canvas.getContext('2d');ctx.scale(scale,scale);ctx.fillStyle='#f5f7f0';ctx.fillRect(0,0,bounds.width,bounds.height);
 const load=url=>new Promise((resolve,reject)=>{const img=new Image();img.crossOrigin='anonymous';img.onload=()=>resolve(img);img.onerror=()=>reject(Error(t('pdf.tileFailed')));img.src=url;});
 const tiles=[...element.querySelectorAll('img.leaflet-tile')].filter(img=>{const r=img.getBoundingClientRect();return img.src&&r.right>bounds.left&&r.left<bounds.right&&r.bottom>bounds.top&&r.top<bounds.bottom;});if(!tiles.length)throw Error(t('pdf.mapNotReady'));
 const loaded=await Promise.all(tiles.map(async tile=>({image:await load(tile.src),rect:tile.getBoundingClientRect(),opacity:Number(getComputedStyle(tile).opacity)||1})));for(const {image,rect,opacity}of loaded){ctx.globalAlpha=opacity;ctx.drawImage(image,rect.left-bounds.left,rect.top-bounds.top,rect.width,rect.height);}ctx.globalAlpha=1;
 const vectors=[...element.querySelectorAll('.leaflet-pane>svg')].sort((a,b)=>(parseInt(getComputedStyle(a.parentElement).zIndex)||0)-(parseInt(getComputedStyle(b.parentElement).zIndex)||0));
 for(const svg of vectors){const rect=svg.getBoundingClientRect();if(!rect.width||!rect.height)continue;const copy=svg.cloneNode(true);copy.removeAttribute('style');copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.setAttribute('width',String(rect.width));copy.setAttribute('height',String(rect.height));const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml'}));try{const image=await load(url);ctx.drawImage(image,rect.left-bounds.left,rect.top-bounds.top,rect.width,rect.height);}finally{URL.revokeObjectURL(url);}}
 /* Wegpunkte: kleine weiße Kreise mit Nummer (wie .waypoint-marker) */
 missions.filter(m=>m.includeWaypoints).forEach(m=>(m.details?.points||[]).forEach((point,i)=>{const p=map.latLngToContainerPoint([point.lat,point.lng]);ctx.fillStyle='#fff';ctx.strokeStyle=DM_PDF.ink;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(p.x,p.y,10,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle=DM_PDF.ink;ctx.font='bold 9.5px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(i+1),p.x,p.y+.5);}));
 /* Startplatz H (runder Kreis, blau) und Aufnahmepunkt (orangefarbenes Quadrat mit Symbol); Kennung als eigenes Schild darunter */
 missions.forEach(m=>{const id=dmPermitLabel(m);
  if(m.panoPoint){const p=map.latLngToContainerPoint([m.panoPoint.lat,m.panoPoint.lng]);ctx.fillStyle=DM_PDF.capture;ctx.strokeStyle='#fff';ctx.lineWidth=2;dmRoundedRect(ctx,p.x-15,p.y-15,30,30,8);ctx.fill();ctx.stroke();ctx.save();ctx.translate(p.x,p.y);ctx.strokeStyle='#fff';ctx.lineWidth=1.8;ctx.lineCap='round';ctx.lineJoin='round';dmCanvasCaptureIcon(ctx,m.captureType);ctx.restore();dmCanvasLabel(ctx,id,p.x,p.y+18,DM_PDF.capture);}
  if(m.takeoffPoint){const p=map.latLngToContainerPoint([m.takeoffPoint.lat,m.takeoffPoint.lng]);ctx.fillStyle='#fff';ctx.strokeStyle=DM_PDF.start;ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(p.x,p.y,16,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle=DM_PDF.start;ctx.font='bold 15px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('H',p.x,p.y+.5);dmCanvasLabel(ctx,id,p.x,p.y+20,DM_PDF.ink);}
 });
 return canvas;
}
async function dmPdfLogo(){try{const img=await new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=reject;i.src='favicon.png?v=1';});const c=document.createElement('canvas');c.width=c.height=128;const ctx=c.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,128,128);ctx.drawImage(img,0,0,128,128);return c;}catch{return null;}}
function dmPdfColor(hex){const n=parseInt(hex.slice(1),16);return [(n>>16)&255,(n>>8)&255,n&255].map(v=>(v/255).toFixed(3)).join(' ');}
/* Baut das PDF. options: {title, kind:'project'|'mission', subtitle, credits, author, logo, natureShown, zonesShown} */
async function dmBuildPermitPDF(canvas,options,missions){
 const font=await dmPdfFont().catch(()=>{throw Error(t('pdf.fontFailed'));}),used=new Set([0]);
 const binary=s=>Uint8Array.from(s,c=>c.charCodeAt(0)&255),objects=[null],add=body=>(objects.push(body),objects.length-1),pages=add(''),kids=[];
 const PAGE_W=842,PAGE_H=595,MARGIN=36,INNER=PAGE_W-2*MARGIN;
 const hex=text=>dmGlyphs(font,text).map(g=>{used.add(g);return g.toString(16).padStart(4,'0');}).join('');
 const width=(text,size)=>dmTextWidth(font,text,size);
 const fill=color=>`${dmPdfColor(color)} rg\n`,stroke=color=>`${dmPdfColor(color)} RG\n`;
 const text=(s,x,y,size=9,color=DM_PDF.ink,bold=false,align='left')=>{s=String(s??'');if(!s)return '';const w=width(s,size),dx=align==='right'?-w:align==='center'?-w/2:0;return `BT ${fill(color)}${bold?`${stroke(color)}2 Tr ${(size*.03).toFixed(2)} w `:''}/F1 ${size} Tf ${(x+dx).toFixed(2)} ${y.toFixed(2)} Td <${hex(s)}> Tj${bold?' 0 Tr':''} ET\n`;};
 const fit=(s,maxWidth,size)=>{s=String(s??'');if(width(s,size)<=maxWidth)return s;let cut=s;while(cut.length&&width(cut+'…',size)>maxWidth)cut=cut.slice(0,-1);return cut+'…';};
 const wrap=(s,maxWidth,size)=>{const lines=[];for(const paragraph of String(s??'').split('\n')){let line='';for(const word of paragraph.split(/\s+/).filter(Boolean)){const candidate=line?line+' '+word:word;if(width(candidate,size)<=maxWidth)line=candidate;else{if(line)lines.push(line);line=width(word,size)<=maxWidth?word:fit(word,maxWidth,size);}}lines.push(line);}return lines.length?lines:[''];};
 const rule=(x1,y1,x2,y2,color=DM_PDF.line,w=.6,dash='')=>`q ${stroke(color)}${w} w ${dash?`[${dash}] 0 d `:''}${x1.toFixed(2)} ${y1.toFixed(2)} m ${x2.toFixed(2)} ${y2.toFixed(2)} l S Q\n`;
 const box=(x,y,w,h,color)=>`q ${fill(color)}${x.toFixed(2)} ${y.toFixed(2)} ${w.toFixed(2)} ${h.toFixed(2)} re f Q\n`;
 const circle=(cx,cy,r,fillColor,strokeColor,w=1.2)=>{const k=.5523*r;return `q ${fillColor?fill(fillColor):''}${stroke(strokeColor)}${w} w ${(cx+r).toFixed(2)} ${cy.toFixed(2)} m ${(cx+r).toFixed(2)} ${(cy+k).toFixed(2)} ${(cx+k).toFixed(2)} ${(cy+r).toFixed(2)} ${cx.toFixed(2)} ${(cy+r).toFixed(2)} c ${(cx-k).toFixed(2)} ${(cy+r).toFixed(2)} ${(cx-r).toFixed(2)} ${(cy+k).toFixed(2)} ${(cx-r).toFixed(2)} ${cy.toFixed(2)} c ${(cx-r).toFixed(2)} ${(cy-k).toFixed(2)} ${(cx-k).toFixed(2)} ${(cy-r).toFixed(2)} ${cx.toFixed(2)} ${(cy-r).toFixed(2)} c ${(cx+k).toFixed(2)} ${(cy-r).toFixed(2)} ${(cx+r).toFixed(2)} ${(cy-k).toFixed(2)} ${(cx+r).toFixed(2)} ${cy.toFixed(2)} c ${fillColor?'B':'S'} Q\n`;};
 const images={};const jpeg=(c,quality)=>Uint8Array.from(atob(c.toDataURL('image/jpeg',quality).split(',')[1]),ch=>ch.charCodeAt(0));
 const mapJpeg=jpeg(canvas,.92);images.Map=add([binary(`<< /Type /XObject /Subtype /Image /Width ${canvas.width} /Height ${canvas.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${mapJpeg.length} >>\nstream\n`),mapJpeg,binary('\nendstream')]);
 if(options.logo){const logoJpeg=jpeg(options.logo,.9);images.Logo=add([binary(`<< /Type /XObject /Subtype /Image /Width ${options.logo.width} /Height ${options.logo.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${logoJpeg.length} >>\nstream\n`),logoJpeg,binary('\nendstream')]);}
 const streams=[];const page=stream=>streams.push(stream);
 const created=new Date().toLocaleString(t.locale(),{dateStyle:'medium',timeStyle:'short'});
 /* Kopf: Logo + Wortmarke links, Titel/Untertitel darunter; Betreiber rechts. */
 const head=(stream,continued=false)=>{let y=PAGE_H-MARGIN;if(images.Logo)stream+=`q 22 0 0 22 ${MARGIN} ${y-22} cm /Logo Do Q\n`;const brandX=MARGIN+(images.Logo?28:0);stream+=text('drone',brandX,y-16,13,DM_PDF.ink,true)+text('missions',brandX+width('drone',13)+.5,y-16,13,DM_PDF.ink);if(options.author){stream+=text(t('pdf.author'),PAGE_W-MARGIN,y-8,6.5,DM_PDF.muted,false,'right')+text(fit(options.author,300,9.5),PAGE_W-MARGIN,y-20,9.5,DM_PDF.ink,true,'right');}y-=46;stream+=text(fit(options.title+(continued?' · '+(options.kind==='mission'?t('pdf.tableWaypoints'):t('pdf.tableMissions')):''),INNER,17),MARGIN,y,17,DM_PDF.ink,true);y-=15;stream+=text(fit(continued?t('pdf.coordinates'):options.subtitle,INNER,9),MARGIN,y,9,DM_PDF.muted);y-=10;stream+=rule(MARGIN,y,PAGE_W-MARGIN,y,DM_PDF.line,.7);return {stream,y};};
 const foot=(stream,n,total)=>stream+rule(MARGIN,MARGIN+10,PAGE_W-MARGIN,MARGIN+10,DM_PDF.line,.5)+text(`${options.kind==='mission'?t('pdf.mission'):t('pdf.project')} · ${t('pdf.created',{date:created})}`,MARGIN,MARGIN,6.5,DM_PDF.muted)+text(t('pdf.page',{n,total}),PAGE_W-MARGIN,MARGIN,6.5,DM_PDF.muted,false,'right');
 /* Seite 1: Karte, Legende, Quellen */
 {let {stream,y}=head('');const legendH=64,sourcesH=44,mapTop=y-10,mapBottom=MARGIN+18+sourcesH+legendH;let w=INNER,h=w*canvas.height/canvas.width;const maxH=mapTop-mapBottom;if(h>maxH){h=maxH;w=h*canvas.width/canvas.height;}const x=MARGIN+(INNER-w)/2,mapY=mapTop-h;
  stream+=`q ${w.toFixed(2)} 0 0 ${h.toFixed(2)} ${x.toFixed(2)} ${mapY.toFixed(2)} cm /Map Do Q\n`+`q ${stroke(DM_PDF.line)}.6 w ${x.toFixed(2)} ${mapY.toFixed(2)} ${w.toFixed(2)} ${h.toFixed(2)} re S Q\n`;
  let ly=mapY-14;stream+=text(t('pdf.legend'),MARGIN,ly,7,DM_PDF.muted,true);ly-=13;
  const items=[];if(missions.some(m=>m.takeoffPoint))items.push(['start',t('pdf.legendStart')]);if(missions.some(m=>m.panoPoint))items.push(['capture',t('pdf.legendCapture')]);if(missions.some(m=>m.takeoffPoint&&m.panoPoint))items.push(['link',t('pdf.legendLink')]);if(missions.some(m=>m.includeWaypoints))items.push(['route',t('pdf.legendRoute')]);if(options.natureShown)items.push(['nature',t('pdf.legendNature')]);if(options.zonesShown)items.push(['zone',t('pdf.legendZones')]);
  const colW=INNER/2;items.forEach((item,i)=>{const col=i%2,row=Math.floor(i/2),ix=MARGIN+col*colW,iy=ly-row*12.5;const [kind,label]=item;
   if(kind==='start')stream+=circle(ix+8,iy+3,6,'#ffffff',DM_PDF.start,1.4)+text('H',ix+8,iy+.6,6.5,DM_PDF.start,true,'center');
   else if(kind==='capture')stream+=`q ${fill(DM_PDF.capture)}${(ix+2).toFixed(2)} ${(iy-3).toFixed(2)} 12 12 re f Q\n`+circle(ix+8,iy+3,2.2,null,'#ffffff',1.1);
   else if(kind==='link')stream+=rule(ix,iy+3,ix+16,iy+3,DM_PDF.link,1.4,'3 2.5');
   else if(kind==='route')stream+=rule(ix,iy+3,ix+16,iy+3,DM_PDF.route,1.8)+circle(ix+8,iy+3,3,'#ffffff',DM_PDF.ink,.9);
   else if(kind==='nature')stream+=`q ${fill(DM_PDF.nature)}/GSa gs ${ix.toFixed(2)} ${(iy-3).toFixed(2)} 16 12 re f Q\n`+`q ${stroke(DM_PDF.nature)}.8 w ${ix.toFixed(2)} ${(iy-3).toFixed(2)} 16 12 re S Q\n`;
   else stream+=`q ${fill(DM_PDF.zone)}/GSa gs ${ix.toFixed(2)} ${(iy-3).toFixed(2)} 16 12 re f Q\n`+`q ${stroke(DM_PDF.zone)}.8 w ${ix.toFixed(2)} ${(iy-3).toFixed(2)} 16 12 re S Q\n`;
   stream+=text(fit(label,colW-30,7.5),ix+22,iy,7.5,DM_PDF.ink);});
  let sy=MARGIN+18+sourcesH-4;stream+=text(t('pdf.sources'),MARGIN,sy,7,DM_PDF.muted,true);sy-=10;
  const sources=[t('pdf.sourceMap',{credits:options.credits})];if(options.natureShown)sources.push(t('pdf.sourceNature'));if(options.zonesShown)sources.push(t('pdf.sourceZones'));sources.push(t('pdf.sourceNote'));
  for(const line of sources){stream+=text(fit(line,INNER,6.8),MARGIN,sy,6.8,DM_PDF.ink);sy-=9;}
  page(stream);}
 /* Tabellen mit wiederholter Kopfzeile. columns: [{key,label,width,align}] rows: [{cells:[...],muted?}] */
 const table=(columns,rows,title)=>{const size=8,lineH=10.5,padX=5,padY=4;let {stream,y}=head('',true);const scaleW=INNER/columns.reduce((s,c)=>s+c.width,0),widths=columns.map(c=>c.width*scaleW);
  const headerRow=()=>{y-=14;const hh=lineH+padY*2;stream+=box(MARGIN,y-hh,INNER,hh,DM_PDF.soft);let cx=MARGIN;columns.forEach((c,i)=>{stream+=text(fit(c.label,widths[i]-padX*2,size),cx+(c.align==='right'?widths[i]-padX:padX),y-padY-lineH+3,size,DM_PDF.ink,true,c.align||'left');cx+=widths[i];});y-=hh;stream+=rule(MARGIN,y,PAGE_W-MARGIN,y,DM_PDF.line,.8);};
  headerRow();
  if(!rows.length){y-=18;stream+=text(t('pdf.noMissions'),MARGIN+padX,y,size,DM_PDF.muted);}
  for(const row of rows){const cells=row.cells.map((cell,i)=>wrap(cell,widths[i]-padX*2,size));const lines=Math.max(...cells.map(c=>c.length)),rh=lines*lineH+padY*2;if(y-rh<MARGIN+24){page(stream);({stream,y}=head('',true));headerRow();}let cx=MARGIN;cells.forEach((lines,i)=>{lines.forEach((line,li)=>{stream+=text(line,cx+(columns[i].align==='right'?widths[i]-padX:padX),y-padY-lineH*(li+1)+3,size,row.muted?DM_PDF.muted:DM_PDF.ink,false,columns[i].align||'left');});cx+=widths[i];});y-=rh;stream+=rule(MARGIN,y,PAGE_W-MARGIN,y,DM_PDF.line,.4);}
  page(stream);};
 const coords=p=>p?`${Number(p.lat).toFixed(6)}, ${Number(p.lng).toFixed(6)}`:'—';
 const heightOf=p=>p&&p.height!=null?`${Number(p.height).toFixed(1)} m · ${t('pdf.heightMission')}`:'—';
 if(options.kind==='mission'&&missions.length===1){const m=missions[0],points=m.details?.points||[],rows=[];
  if(m.takeoffPoint)rows.push({cells:['H',t('pdf.fnStartGround')+' '+dmPermitLabel(m),Number(m.takeoffPoint.lat).toFixed(6),Number(m.takeoffPoint.lng).toFixed(6),'—']});
  points.forEach((p,i)=>rows.push({cells:[String(i+1),m.panoPoint&&i===0?t('pdf.fnStart'):m.panoPoint&&i===1?t('pdf.fnCapture')+' · '+dmCaptureName(m.captureType):t('pdf.fnWaypoint'),Number(p.lat).toFixed(6),Number(p.lng).toFixed(6),heightOf(p)]}));
  table([{label:t('pdf.colNo'),width:40,align:'right'},{label:t('pdf.colFunction'),width:190},{label:t('pdf.colLat'),width:120},{label:t('pdf.colLng'),width:120},{label:t('pdf.colHeightRef'),width:200}],rows,`${m.name} · ${t('pdf.tableWaypoints')}`);}
 else{const rows=missions.map(m=>({cells:[dmPermitLabel(m),m.name,dmCaptureName(m.captureType),coords(m.takeoffPoint),coords(m.panoPoint),heightOf(m.details?.points?.[1])],muted:!m.takeoffPoint&&!m.panoPoint}));
  table([{label:t('pdf.colId'),width:60},{label:t('pdf.colMission'),width:210},{label:t('pdf.colCapture'),width:95},{label:t('pdf.colStart'),width:140},{label:t('pdf.colCapturePoint'),width:140},{label:t('pdf.colHeight'),width:125}],rows,t('pdf.tableMissions'));}
 /* Schrift erst jetzt einbetten: alle benutzten Glyphen sind bekannt. Fußzeilen danach, da sie keine neuen Zeichen außer Ziffern brauchen. */
 for(const s of [t('pdf.page',{n:0,total:0}),'0123456789',t('pdf.mission'),t('pdf.project'),t('pdf.created',{date:created})])hex(s);
 const fontId=await dmPdfFontObjects(font,used,add,binary),alpha=add('<< /Type /ExtGState /ca 0.18 /CA 1 >>');
 streams.forEach((stream,i)=>{const bytes=new TextEncoder().encode(foot(stream,i+1,streams.length));const content=add([binary(`<< /Length ${bytes.length} >>\nstream\n`),bytes,binary('\nendstream')]);kids.push(add(`<< /Type /Page /Parent ${pages} 0 R /MediaBox [0 0 ${PAGE_W} ${PAGE_H}] /Resources << /Font << /F1 ${fontId} 0 R >> /ExtGState << /GSa ${alpha} 0 R >> /XObject << ${Object.entries(images).map(([name,id])=>`/${name} ${id} 0 R`).join(' ')} >> >> /Contents ${content} 0 R >>`));});
 objects[pages]=`<< /Type /Pages /Count ${kids.length} /Kids [${kids.map(id=>id+' 0 R').join(' ')}] >>`;
 const info=add(`<< /Producer (dronemissions) /Title <FEFF${Array.from(options.title,ch=>ch.charCodeAt(0).toString(16).padStart(4,'0')).join('')}> >>`),catalog=add(`<< /Type /Catalog /Pages ${pages} 0 R >>`),chunks=[binary('%PDF-1.5\n%\xE2\xE3\xCF\xD3\n')],offsets=[0];let length=chunks[0].length;
 for(let id=1;id<objects.length;id++){offsets[id]=length;const parts=[binary(`${id} 0 obj\n`),...(Array.isArray(objects[id])?objects[id]:[new TextEncoder().encode(objects[id])]),binary('\nendobj\n')];for(const part of parts){chunks.push(part);length+=part.length;}}
 const xref=length;chunks.push(binary(`xref\n0 ${objects.length}\n0000000000 65535 f \n${offsets.slice(1).map(offset=>String(offset).padStart(10,'0')+' 00000 n \n').join('')}trailer\n<< /Size ${objects.length} /Root ${catalog} 0 R /Info ${info} 0 R >>\nstartxref\n${xref}\n%%EOF\n`));return new Blob(chunks,{type:'application/pdf'});
}
/* options: {title, kind, subtitle, file} – Quellen, Betreiber, Logo und Ebenenstatus werden hier ergänzt. */
async function dmDownloadPermitPDF(map,options,missions){
 const container=map.getContainer(),credits=(container.querySelector('.leaflet-control-attribution')?.textContent||'basemap.at · CC BY 4.0').replace(/^\s*Leaflet\s*\|?\s*/,'').split('Schutzgebiete')[0].replace(/[\s,·|]+$/,'').trim();
 const author=(document.querySelector('.sidebar-head .brand-name small')?.textContent||'').trim();
 const canvas=await dmPermitCanvas(map,missions),logo=await dmPdfLogo();
 const pdf=await dmBuildPermitPDF(canvas,{...options,credits,author,logo,natureShown:Boolean(map.dmNature?.enabled()),zonesShown:Boolean(container.closest('body')&&container.querySelector('[data-zones]')?.checked)},missions);
 const url=URL.createObjectURL(pdf),link=document.createElement('a');link.href=url;link.download=options.file||'Freigabekarte.pdf';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
