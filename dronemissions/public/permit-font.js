'use strict';
/* Drone Missions · Unicode-Schrift für die PDF-Erzeugung
   Lädt DejaVu Sans aus vendor/fonts/DejaVuSans.woff (WOFF 1.0 = TrueType-Tabellen, je Tabelle zlib-komprimiert),
   entpackt sie im Browser und bettet ein TrueType-Subset (nur benutzte Glyphen) als CIDFontType2 mit Identity-H ein.
   Damit sind Deutsch, Englisch und Ukrainisch (Kyrillisch) im PDF korrekt; die Zeichenbreiten kommen aus hmtx.
   Lizenz: Bitstream Vera / DejaVu (vendor/fonts/DejaVu-LICENSE). Keine externe Abhängigkeit, kein CDN. */
const DM_PDF_FONT_URL='vendor/fonts/DejaVuSans.woff';
let dmPdfFontPromise=null;
async function dmInflate(bytes){
 if(typeof DecompressionStream==='undefined')throw Error('DecompressionStream fehlt');
 return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer());
}
async function dmParseWoff(buffer){
 const view=new DataView(buffer),tag=String.fromCharCode(view.getUint8(0),view.getUint8(1),view.getUint8(2),view.getUint8(3));
 if(tag!=='wOFF')throw Error('Keine WOFF-Datei');
 const count=view.getUint16(12),tables={};
 for(let i=0;i<count;i++){const base=44+i*20,name=String.fromCharCode(view.getUint8(base),view.getUint8(base+1),view.getUint8(base+2),view.getUint8(base+3)),offset=view.getUint32(base+4),compressed=view.getUint32(base+8),original=view.getUint32(base+12);const raw=new Uint8Array(buffer,offset,compressed);tables[name]=compressed<original?await dmInflate(raw):raw.slice();}
 return tables;
}
function dmParseFont(tables){
 const need=['head','hhea','maxp','hmtx','loca','glyf','cmap'];for(const name of need)if(!tables[name])throw Error('Schrifttabelle fehlt: '+name);
 const dv=table=>new DataView(table.buffer,table.byteOffset,table.byteLength);
 const head=dv(tables.head),unitsPerEm=head.getUint16(18),longLoca=head.getInt16(50)===1,bbox=[head.getInt16(36),head.getInt16(38),head.getInt16(40),head.getInt16(42)];
 const hhea=dv(tables.hhea),ascent=hhea.getInt16(4),descent=hhea.getInt16(6),metricCount=hhea.getUint16(34);
 const numGlyphs=dv(tables.maxp).getUint16(4);
 const hmtx=dv(tables.hmtx),advance=gid=>hmtx.getUint16(Math.min(gid,metricCount-1)*4);
 const loca=dv(tables.loca),offsets=new Array(numGlyphs+1);for(let i=0;i<=numGlyphs;i++)offsets[i]=longLoca?loca.getUint32(i*4):loca.getUint16(i*2)*2;
 /* cmap: Format 4 (BMP) der Plattform 3/1 oder 0/x; Format 12 ergänzt Zeichen außerhalb der BMP, falls vorhanden. */
 const cmap=dv(tables.cmap),map=new Map();let best=null,best12=null;
 for(let i=0,n=cmap.getUint16(2);i<n;i++){const platform=cmap.getUint16(4+i*8),encoding=cmap.getUint16(6+i*8),offset=cmap.getUint32(8+i*8),format=cmap.getUint16(offset);if(format===4&&(platform===3&&encoding===1||platform===0)&&best===null)best=offset;if(format===12&&(platform===3&&encoding===10||platform===0))best12=offset;}
 if(best!==null){const segX2=cmap.getUint16(best+6),ends=best+14,starts=ends+segX2+2,deltas=starts+segX2,ranges=deltas+segX2;for(let s=0;s<segX2/2;s++){const end=cmap.getUint16(ends+s*2),start=cmap.getUint16(starts+s*2),delta=cmap.getInt16(deltas+s*2),rangeOffset=cmap.getUint16(ranges+s*2);if(start===0xFFFF)continue;for(let c=start;c<=end;c++){let gid;if(rangeOffset===0)gid=(c+delta)&0xFFFF;else{const address=ranges+s*2+rangeOffset+(c-start)*2;if(address+1>=cmap.byteLength)continue;gid=cmap.getUint16(address);if(gid)gid=(gid+delta)&0xFFFF;}if(gid&&gid<numGlyphs)map.set(c,gid);}}}
 if(best12!==null){const groups=cmap.getUint32(best12+12);for(let g=0;g<groups;g++){const base=best12+16+g*12,start=cmap.getUint32(base),end=cmap.getUint32(base+4),gid=cmap.getUint32(base+8);for(let c=start;c<=end&&c-start<65536;c++){const id=gid+(c-start);if(id<numGlyphs&&!map.has(c))map.set(c,id);}}}
 return {tables,unitsPerEm,bbox,ascent,descent,numGlyphs,offsets,advance,map,glyf:tables.glyf,head:tables.head};
}
async function dmPdfFont(){
 if(!dmPdfFontPromise)dmPdfFontPromise=(async()=>{const response=await fetch(DM_PDF_FONT_URL,{cache:'force-cache'});if(!response.ok)throw Error('HTTP '+response.status);return dmParseFont(await dmParseWoff(await response.arrayBuffer()));})().catch(e=>{dmPdfFontPromise=null;throw e;});
 return dmPdfFontPromise;
}
/* Zeichenfolge → Glyphen-IDs. Unbekannte Zeichen fallen auf das .notdef-Rechteck zurück; Steuerzeichen werden übersprungen. */
function dmGlyphs(font,text){const ids=[];for(const ch of String(text)){const code=ch.codePointAt(0);if(code<32)continue;ids.push(font.map.get(code)??0);}return ids;}
function dmTextWidth(font,text,size){let width=0;for(const gid of dmGlyphs(font,text))width+=font.advance(gid);return width*size/font.unitsPerEm;}
/* Subset: Glyphen samt Komponenten zusammengesetzter Glyphen behalten, Nummern bleiben erhalten (loca zeigt für unbenutzte Glyphen auf leere Einträge). */
function dmSubsetGlyphs(font,used){
 const glyf=new DataView(font.glyf.buffer,font.glyf.byteOffset,font.glyf.byteLength),queue=[...used],keep=new Set([0]);
 while(queue.length){const gid=queue.pop();if(keep.has(gid)||gid>=font.numGlyphs)continue;keep.add(gid);const start=font.offsets[gid],end=font.offsets[gid+1];if(end-start<10)continue;if(glyf.getInt16(start)>=0)continue;let p=start+10;for(;;){const flags=glyf.getUint16(p),component=glyf.getUint16(p+2);queue.push(component);p+=4;p+=flags&1?4:2;if(flags&8)p+=2;else if(flags&0x40)p+=4;else if(flags&0x80)p+=8;if(!(flags&0x20))break;}}
 return keep;
}
function dmBuildTrueType(font,used){
 const keep=dmSubsetGlyphs(font,used),loca=new Uint8Array((font.numGlyphs+1)*4),locaView=new DataView(loca.buffer);let glyfSize=0;
 for(let gid=0;gid<font.numGlyphs;gid++)if(keep.has(gid))glyfSize+=(font.offsets[gid+1]-font.offsets[gid]+3)&~3;
 const glyf=new Uint8Array(glyfSize);let cursor=0;
 for(let gid=0;gid<font.numGlyphs;gid++){locaView.setUint32(gid*4,cursor);if(!keep.has(gid))continue;const start=font.offsets[gid],length=font.offsets[gid+1]-start;glyf.set(font.glyf.subarray(start,start+length),cursor);cursor+=(length+3)&~3;}
 locaView.setUint32(font.numGlyphs*4,cursor);
 const head=font.head.slice();new DataView(head.buffer).setInt16(50,1);new DataView(head.buffer).setUint32(8,0);
 const tables=[['head',head],['hhea',font.tables.hhea],['maxp',font.tables.maxp],['hmtx',font.tables.hmtx],['loca',loca],['glyf',glyf]].sort((a,b)=>a[0]<b[0]?-1:1);
 const directory=12+16*tables.length;let total=directory;for(const [,data]of tables)total+=(data.byteLength+3)&~3;
 const out=new Uint8Array(total),view=new DataView(out.buffer);view.setUint32(0,0x00010000);view.setUint16(4,tables.length);const power=Math.floor(Math.log2(tables.length));view.setUint16(6,(2**power)*16);view.setUint16(8,power);view.setUint16(10,tables.length*16-(2**power)*16);
 let offset=directory;tables.forEach(([name,data],i)=>{const base=12+i*16;for(let c=0;c<4;c++)out[base+c]=name.charCodeAt(c);let sum=0;for(let p=0;p<data.byteLength;p+=4)sum=(sum+(((data[p]||0)<<24)|((data[p+1]||0)<<16)|((data[p+2]||0)<<8)|(data[p+3]||0)))>>>0;view.setUint32(base+4,sum);view.setUint32(base+8,offset);view.setUint32(base+12,data.byteLength);out.set(data,offset);offset+=(data.byteLength+3)&~3;});
 return out;
}
/* PDF-Objekte der Schrift: Type0 → CIDFontType2 → FontDescriptor → FontFile2 (optional Flate) + ToUnicode. add(body) liefert die Objektnummer. */
async function dmPdfFontObjects(font,used,add,binary){
 const program=dmBuildTrueType(font,used);let stream=program,filter='';
 if(typeof CompressionStream!=='undefined'){try{stream=new Uint8Array(await new Response(new Blob([program]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());filter=' /Filter /FlateDecode';}catch{stream=program;filter='';}}
 const scale=1000/font.unitsPerEm,ids=[...used].filter(g=>g<font.numGlyphs).sort((a,b)=>a-b);
 const widths=ids.map(gid=>`${gid} [${Math.round(font.advance(gid)*scale)}]`).join(' ');
 const file=add([binary(`<< /Length ${stream.length}${filter} /Length1 ${program.length} >>\nstream\n`),stream,binary('\nendstream')]);
 const descriptor=add(`<< /Type /FontDescriptor /FontName /DejaVuSans /Flags 32 /FontBBox [${font.bbox.map(v=>Math.round(v*scale)).join(' ')}] /ItalicAngle 0 /Ascent ${Math.round(font.ascent*scale)} /Descent ${Math.round(font.descent*scale)} /CapHeight 729 /StemV 80 /FontFile2 ${file} 0 R >>`);
 const reverse=new Map();for(const [code,gid]of font.map)if(used.has(gid)&&!reverse.has(gid))reverse.set(gid,code);
 const utf16=code=>code>0xFFFF?((0xD800+((code-0x10000)>>10)).toString(16).padStart(4,'0')+(0xDC00+((code-0x10000)&0x3FF)).toString(16).padStart(4,'0')):code.toString(16).padStart(4,'0');
 const chars=ids.filter(gid=>reverse.has(gid)).map(gid=>`<${gid.toString(16).padStart(4,'0')}> <${utf16(reverse.get(gid))}>`);
 const cmapText=`/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n${chars.length} beginbfchar\n${chars.join('\n')}\nendbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n`;
 const cmapBytes=binary(cmapText),toUnicode=add([binary(`<< /Length ${cmapBytes.length} >>\nstream\n`),cmapBytes,binary('\nendstream')]);
 const cid=add(`<< /Type /Font /Subtype /CIDFontType2 /BaseFont /DejaVuSans /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor ${descriptor} 0 R /DW 600 /W [${widths}] /CIDToGIDMap /Identity >>`);
 return add(`<< /Type /Font /Subtype /Type0 /BaseFont /DejaVuSans /Encoding /Identity-H /DescendantFonts [${cid} 0 R] /ToUnicode ${toUnicode} 0 R >>`);
}
