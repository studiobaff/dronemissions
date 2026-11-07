'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');const context={};vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../public/zones.js','utf8'),context);
const ring=[[0,0],[10,0],[10,10],[0,10],[0,0]],hole=[[4,4],[6,4],[6,6],[4,6],[4,4]],shape={type:'Polygon',coordinates:[ring,hole]};
assert(context.dmZoneContains(shape,2,2));assert(!context.dmZoneContains(shape,5,5));assert(!context.dmZoneContains(shape,12,5));assert(context.dmZoneContains({type:'MultiPolygon',coordinates:[[ring]]},2,2));
assert(context.dmZonePeriod({applicability:[{permanent:'NO',startDateTime:'2026-10-25T01:00:00Z',schedule:[{day:['MON','FRI'],startTime:'07:00:00Z',endTime:'12:00:00Z'}]}]}).includes('Mo, Fr: 07:00:00Z–12:00:00Z (Z = UTC)'));
console.log('PASS: zone hit detection including holes and multipolygons, source schedule retained in UTC.');

assert(!context.dmZoneInDate({applicability:[{startDateTime:'2026-10-26T05:00:00Z',endDateTime:'2026-10-26T18:00:00Z'}]},Date.parse('2026-11-07T12:00:00Z')));assert(context.dmZoneInDate({applicability:[{permanent:'YES'}]},Date.parse('2026-11-07T12:00:00Z')));console.log('PASS: expired Nationalfeiertag zone excluded by date, permanent zones retained.');
const weekly={applicability:[{startDateTime:'2026-10-25T00:00:00Z',endDateTime:'2027-03-28T00:59:59Z',schedule:[{day:['MON','TUE','WED','THU'],startTime:'07:00:00Z',endTime:'15:00:00Z'},{day:['FRI'],startTime:'07:00:00Z',endTime:'12:30:00Z'}]}]};
assert.equal(context.dmZoneScheduleState(weekly,Date.parse('2026-11-09T08:00:00Z')).kind,'scheduled');assert.equal(context.dmZoneScheduleState(weekly,Date.parse('2026-11-07T12:00:00Z')).kind,'outside');assert(context.dmZoneScheduleState(weekly,Date.parse('2026-11-07T12:00:00Z')).note.includes('08:00'));
assert.equal(context.dmZoneScheduleState({applicability:[{permanent:'YES'}]}).kind,'unknown');assert.equal(context.dmZoneScheduleState({applicability:[{startDateTime:'2022-01-01T00:00:00Z',endDateTime:'2100-12-31T23:59:59Z'}]}).kind,'unknown');
const overnight={applicability:[{schedule:[{day:['FRI'],startTime:'22:00:00Z',endTime:'02:00:00Z'}]}]};assert.equal(context.dmZoneScheduleState(overnight,Date.parse('2026-11-07T01:00:00Z')).kind,'scheduled');
console.log('PASS: scheduled hours, weekend/next opening in Vienna time, overnight range, missing MCTR hours remain unknown.');
