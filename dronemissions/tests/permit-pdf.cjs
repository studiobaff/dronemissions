'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'../public');
const context=vm.createContext({URLSearchParams,location:{search:''},navigator:{language:'de'},localStorage:{getItem:()=>null},document:{addEventListener:()=>{}},Blob,Response,DecompressionStream,CompressionStream,TextEncoder,Uint8Array,DataView,Map,Set,console});
for(const name of ['i18n.js','permit-font.js','permit-pdf.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),context,{filename:name});
vm.runInContext(`
 const equal=(a,b,message)=>{if(a!==b)throw Error(message+': '+a+' !== '+b);};
 const mission={details:{heightMode:'mehrere Flugrouten',points:[{height:60},{height:200},{height:null},{height:15}],routes:[{start:0,count:1,heightMode:'relativeToStartPoint'},{start:1,count:2,heightMode:'EGM96'},{start:3,count:1,heightMode:'unbekannt'}]}};
 equal(dmPdfHeight(mission,0),'60.0 m\\nrelativ zum Startpunkt','relative datum');
 equal(dmPdfHeight(mission,1),'200.0 m\\nüber EGM96','per-route datum');
 equal(dmPdfHeight(mission,2),'—','missing height');
 equal(dmPdfHeight(mission,3),'15.0 m\\nBezug unbekannt','unknown datum');
 dmLang='en';equal(dmPdfHeight(mission,0),'60.0 m\\nrelative to take-off','English datum');
 dmLang='uk';equal(dmPdfHeight(mission,0),'60.0 m\\nвідносно точки зльоту','Ukrainian datum');
 const identifier='МісіяБезПробілів'.repeat(12);const lines=dmPdfWrap(identifier,20,1,s=>[...s].length);
 equal(lines.join(''),identifier,'unbroken identifier retained');
 if(lines.some(s=>[...s].length>20))throw Error('identifier overflows');
 equal(dmPdfWrap('alpha beta gamma',10,1,s=>s.length).join('|'),'alpha beta|gamma','word wrapping');
`,context);
(async()=>{
 const bytes=fs.readFileSync(path.join(root,'vendor/fonts/DejaVuSans.woff'));
 const font=await context.dmParseWoff(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)).then(context.dmParseFont);
 const text='ÄÖÜß Українська Ґґ Єє Іі Її';assert(context.dmGlyphs(font,text).every(id=>id!==0),'DE/UK glyphs must exist');
 const subset=context.dmBuildTrueType(font,new Set(context.dmGlyphs(font,text)));assert(subset.length>0);
 console.log('PASS: PDF route-specific height datums, missing/unknown references, DE/EN/UK, intact long Unicode names and embedded font glyphs.');
})().catch(e=>{console.error(e);process.exitCode=1;});
