'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=__dirname+'/../public/';
const context={URLSearchParams,location:{search:''},navigator:{language:'de'},localStorage:{getItem:()=>null},document:{addEventListener:()=>{}},console,esc:s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))};
vm.createContext(context);for(const name of ['i18n.js','nature.js','zones.js'])vm.runInContext(fs.readFileSync(root+name,'utf8'),context,{filename:name});
const fresh={checkedAt:Date.now()/1000,stale:false};
assert.equal(context.dmAirspaceAssessment([],fresh,true).key,'legal.noZone');
assert.equal(context.dmAirspaceAssessment([],null,false).key,'legal.notLoaded');
assert.equal(context.dmAirspaceAssessment([],{...fresh,stale:true},true).key,'legal.stale');
assert.equal(context.dmAirspaceAssessment([],{},true).key,'legal.stale');
assert.equal(context.dmAirspaceAssessment([],{checkedAt:1},true).key,'legal.stale');
for(const restriction of ['PROHIBITED','REQ_AUTHORISATION','CONDITIONAL'])assert.equal(context.dmAirspaceAssessment([{restriction,reason:['NATURE']}],fresh,true).key,'legal.restricted');
assert.equal(context.dmAirspaceAssessment([{restriction:'NO_RESTRICTION',reason:['NATURE']}],fresh,true).key,'legal.exception');
assert.equal(context.dmAirspaceAssessment([{restriction:'NEW'}],fresh,true).key,'legal.unknownZone');
assert.equal(context.dmAirspaceAssessment([{restriction:'PROHIBITED',applicability:[{endDateTime:'2020-01-01'}]}],fresh,true).key,'legal.noZone');
const outer=[[15.9,47.9],[16.1,47.9],[16.1,48.1],[15.9,48.1],[15.9,47.9]],hole=[[15.99,47.99],[16.01,47.99],[16.01,48.01],[15.99,48.01],[15.99,47.99]];
const feature=(name,designation,holes=[])=>({geometry:{type:'Polygon',coordinates:[outer,...holes]},properties:{name,designation,state:'Niederösterreich'}});
context.api=async(action,{category})=>({type:'FeatureCollection',features:category==='N2000'?[feature('<Wienerwald>','FFH'),feature('<Wienerwald>','Vogelschutz')]:category==='NSG'?[feature('Hole should not match','NSG',[hole])]:[],source:'Synthetic',dataYear:2025});
(async()=>{
 const result=await context.dmNatureAt({lat:48,lng:16});assert(result.complete);assert.equal(result.areas.length,2,'distinct FFH and SPA records retained; hole excluded');
 const html=context.dmNaturePointHTML(result);assert(html.includes('&lt;Wienerwald&gt;'));assert(html.includes('keine Verbotsbewertung'));assert(html.includes('nicht automatisch geprüft'));assert(!html.includes('Genehmigung erforderlich'));
 for(const lang of ['de','en','uk']){vm.runInContext('dmLang='+JSON.stringify(lang),context);assert(!context.dmNaturePointHTML(result).includes('legal.'));assert(!context.dmAirspaceAssessmentHTML([],fresh,true).includes('legal.'));}
 vm.runInContext("dmNatureRequests.clear();dmLang='de'",context);context.api=async()=>{throw Error('source down');};
 const failed=await context.dmNatureAt({lat:48,lng:16});assert(!failed.complete);const failureHTML=context.dmNaturePointHTML(failed);assert(failureHTML.includes('unvollständig'));assert(!failureHTML.includes('Kein Schutzgebiet im'));
 vm.runInContext('dmNatureRequests.clear()',context);context.api=async()=>({type:'FeatureCollection',features:[],stale:true});assert(!(await context.dmNatureAt({lat:48,lng:16})).complete);
 vm.runInContext('dmNatureRequests.clear()',context);context.api=async()=>({});assert(!(await context.dmNatureAt({lat:48,lng:16})).complete);
 console.log('PASS: aviation restrictions vs area intersections, exceptions, expired/unknown/stale/missing data, FFH/SPA identity, holes, escaped names, source failure and DE/EN/UK.');
})().catch(e=>{console.error(e);process.exitCode=1;});
