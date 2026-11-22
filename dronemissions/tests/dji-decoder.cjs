const assert=require('node:assert/strict');
const {fixture}=require('./dji-fixture.cjs');
const {DJILog}=require('../public/vendor/dji-log-parser.js');
const {normalize}=require('../public/dji-decoder.js');
const f=fixture(),log=new DJILog(new Uint8Array(f.raw));
assert.equal(log.version,13);assert.equal(log.details.totalTime,960);
const frames=log.frames(f.chains),out=normalize(log.details,frames);
assert.equal(out.flight.totalDistance,750);assert.equal(out.telemetry.time.at(-1),960);assert.equal(out.telemetry.battery[0],100);assert.equal(out.telemetry.battery.at(-1),60);
assert.equal(out.telemetry.batteryRemainedCapacity.at(-1),3000);
assert(Math.abs(out.telemetry.latitude[1]-48.001)<1e-6);
assert.equal(log.keychainsRequest().department,3);log.free();
console.log('PASS: synthetic AES-encrypted DJI v13 binary decoded, coordinates, duration and battery verified.');

const sample=t=>({osd:{flyTime:t,latitude:t,longitude:16},battery:{voltage:12,chargeLevel:90,currentCapacity:1000}});
const startup=normalize({},[sample(.1),sample(0),sample(.2)]);assert.deepEqual(startup.telemetry.time,[0,.1,.2]);assert.deepEqual(startup.telemetry.latitude,[0,.1,.2]);
assert.deepEqual(normalize({},[sample(1),sample(2),sample(0)]).telemetry.time,[1,2,0]);
assert.deepEqual(normalize({},[sample(10),sample(0),sample(11)]).telemetry.time,[10,0,11]);

assert.deepEqual(normalize({},[sample(0),sample(.2),sample(.1),sample(.3),sample(.4),sample(.5)]).telemetry.time,[0,.1,.2,.3,.4,.5]);
