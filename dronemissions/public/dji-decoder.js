'use strict';
// Server-side CLI. No credentials in arguments or diagnostics. No network access.
const fs=require('node:fs');
const {DJILog}=require('./vendor/dji-log-parser.js');
function normalize(details,frames){
 if(!Array.isArray(frames)||frames.length<2||frames.length>50000)throw Error('FRAME_LIMIT');
 // Some DJI streams emit the first two samples in reverse order (one tick).
 // Reorder the complete samples only at startup; later clock resets stay invalid.
 if(frames.length>=3){const a=frames[0]?.osd?.flyTime,b=frames[1]?.osd?.flyTime,c=frames[2]?.osd?.flyTime;if(Number.isFinite(a)&&Number.isFinite(b)&&Number.isFinite(c)&&a>b&&a-b<=.25&&c>=a)frames=[frames[1],frames[0],...frames.slice(2)];}
 const telemetry={time:[],latitude:[],longitude:[],battery:[],batteryRemainedCapacity:[]};
 for(const frame of frames){
  const o=frame.osd,b=frame.battery;
  if(!o||!Number.isFinite(o.flyTime))throw Error('TIME_INVALID');
  telemetry.time.push(o.flyTime);telemetry.latitude.push(o.latitude);telemetry.longitude.push(o.longitude);
  // Parser defaults are zero before any battery record. Do not invent a 0% measurement.
  const measured=b&&Number.isFinite(b.voltage)&&b.voltage>0;
  telemetry.battery.push(measured?b.chargeLevel:null);
  telemetry.batteryRemainedCapacity.push(measured&&b.currentCapacity>0?b.currentCapacity:null);
 }
 const recovered=frames.find(f=>f.recover?.aircraftSn)?.recover||{};
 return {_exportInfo:{format:'Open DroneLog JSON Export',units:{distance:'metric'},decoder:'dji-log-parser-js 0.5.7'},flight:{displayName:details.aircraftName||'DJI-Flug',startTime:details.startTime,durationSecs:details.totalTime,totalDistance:details.totalDistance,droneModel:typeof details.productType==='string'?details.productType:'DJI',droneSerial:recovered.aircraftSn||details.aircraftSn,batterySerial:recovered.batterySn||details.batterySn},telemetry};
}
async function main(){
 const [mode,path]=process.argv.slice(2);
 if(mode==='health'){process.stdout.write(JSON.stringify({ready:typeof DJILog==='function',version:'0.5.7'}));return;}
 if(!['request','decode'].includes(mode)||!path)throw Error('ARGUMENT');
 const stat=fs.statSync(path);if(!stat.isFile()||stat.size>16777216||stat.size<16)throw Error('FILE_SIZE');
 const log=new DJILog(new Uint8Array(fs.readFileSync(path)));
 try{
  if(mode==='request'){process.stdout.write(JSON.stringify({version:log.version,request:log.version>=13?log.keychainsRequest():null}));return;}
  const raw=fs.readFileSync(0,'utf8');if(raw.length>4194304)throw Error('KEYCHAIN_SIZE');
  const chains=raw?JSON.parse(raw):undefined;
  const frames=log.frames(chains||undefined);process.stdout.write(JSON.stringify(normalize(log.details,frames)));
 }finally{log.free();}
}
if(require.main===module)main().catch(()=>{process.stderr.write('DJI log could not be decoded.\n');process.exitCode=1;});
module.exports={normalize};
