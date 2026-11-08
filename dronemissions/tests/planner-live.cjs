const assert=require('node:assert/strict');
const Live=require('../public/planner-live.js');
(async()=>{
 let resolve,reject,shown=[],errors=[],calls=0,open=true;
 const p=new Live({delay:100000,ready:()=>open,request:()=>{calls++;return new Promise((a,b)=>{resolve=a;reject=b;});},apply:x=>shown.push(x),error:e=>errors.push(e.message),start:()=>{},finish:()=>{}});
 p.change();let first=p.flush();p.change();p.change();p.flush();assert.equal(calls,1);resolve('old');await first;assert.deepEqual(shown,[]);
 let last=p.flush();resolve('latest');await last;assert.deepEqual(shown,['latest']);assert.equal(calls,2);
 p.change();let failure=p.flush();reject(new Error('invalid geometry'));await failure;assert.deepEqual(errors,['invalid geometry']);
 p.change();let closing=p.flush();p.cancel();open=false;resolve('closed');await closing;assert.deepEqual(shown,['latest']);p.cancel();
 console.log('PASS: serialized previews, coalesced edits, stale results discarded, validation error and close cancellation');
})().catch(e=>{console.error(e);process.exit(1);});
