'use strict';
const assert=require('node:assert/strict');const {DmMissionSelection}=require('../public/mission-selection.js');
const s=new DmMissionSelection(),rows=[{id:'A',captureType:'photo'},{id:'B',captureType:'video'},{id:'E',captureType:'photo'},{id:'F',captureType:'video'},{id:'G',captureType:'photo'}];
assert.deepEqual(s.rows('project',rows),rows);s.only('project',['A','B','E','G']);assert.deepEqual(s.rows('project',rows).map(m=>m.id),['A','B','E','G']);
s.toggle('project','F',true,rows);assert.equal(s.rows('project',rows).length,5);s.toggle('project','A',false,rows);assert(!s.rows('project',rows).some(m=>m.id==='A'));
assert.equal(s.rows('another',rows).length,5);assert.equal(s.rows('project',rows.filter(m=>m.id==='B')).length,1);assert.equal(s.rows('project',rows).length,4);
s.only('project',[]);assert.equal(s.rows('project',rows).length,0);s.all('project');assert.equal(s.rows('project',rows).length,5);assert.equal(s.explicit('project'),false);
s.only('project',['unauthorized','A']);assert.deepEqual(s.rows('project',rows).map(m=>m.id),['A']);
console.log('PASS: arbitrary photo/video mission subsets, all/none, project isolation, search preservation and authorized-row intersection.');
