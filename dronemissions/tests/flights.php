<?php
declare(strict_types=1);
require __DIR__.'/../public/lib.php';require __DIR__.'/../public/planner-core.php';
function ft(bool $ok,string $why): void {if(!$ok)throw new RuntimeException($why);}
$in=['name'=>'Synthetic shared raster','type'=>'grid','cameraId'=>'mavic3','geometry'=>['type'=>'Polygon','coordinates'=>[[[16,48],[16.003,48],[16.003,48.006],[16,48.006],[16,48]]]],'params'=>['captureMode'=>'video','height'=>70,'gridMotion'=>'smooth','gridTurnRadius'=>10,'speed'=>3,'photoLimit'=>200,'sectionOverlap'=>2,'terrainMode'=>'off','flightSplit'=>'count','flightCount'=>2,'flightMinutes'=>8,'reserveMinutes'=>2,'flightOverlap'=>15,'entryEnabled'=>true,'entryLat'=>48,'entryLng'=>16]];
$two=dm_plan_build($in);ft(count($two['parts'])===2,'two flights');
$in['params']['flightCount']=3;$three=dm_plan_build($in);ft(count($three['parts'])===3,'three flights');ft($two['points']===$three['points']&&$two['geometry']===$three['geometry'],'repartition retains master raster');
$replay=dm_plan_build(array_intersect_key($three,array_flip(['name','type','cameraId','camera','geometry','params'])));ft($replay['routeSha256']===$three['routeSha256']&&$replay['parts']===$three['parts'],'persist and replay');
ft($three['flights']['flights'][1]['overlapMeters']>0&&$three['flights']['flights'][1]['overlapMeters']<=15.001,'bounded distance overlap');
$in['params']['flightSplit']='time';$auto=dm_plan_build($in);ft(count($auto['parts'])>1,'budget partitions route');
foreach($auto['flights']['flights'] as $e){ft($e['budgetSeconds']<=480.01,'all flight budgets including transit and reserve');ft($e['outboundSeconds']>0&&$e['returnSeconds']>0&&$e['reserveSeconds']===120.0,'transit and reserve counted');}
ft($auto['parts'][0][0]['lat']===$auto['points'][0]['lat'],'route start preserved');$last=end($auto['parts']);ft(end($last)['lat']===end($auto['points'])['lat'],'route end preserved');
$in['params']['flightMinutes']=15;$longer=dm_plan_build($in);ft(count($longer['parts'])<=count($auto['parts']),'larger budget no more flights');
$short=$in;$short['params']['flightMinutes']=3;$short['params']['reserveMinutes']=2.9;try{dm_plan_build($short);throw new RuntimeException('impossible budget accepted');}catch(InvalidArgumentException $expected){}
$in['params']['flightSplit']='count';$in['params']['flightCount']=1;$in['params']['flightMinutes']=3;$in['params']['photoLimit']=200;
// Use straight grid to keep the entire route under the export limit.
$in['params']['gridMotion']='stop';$one=dm_plan_build($in);ft($one['flights']['overBudget']===1,'explicit count reports budget overrun');
$in['params']['flightSplit']='legacy';$old=dm_plan_build($in);ft($old['flights']===null,'legacy compatibility');
$hole=$in;$hole['params']['flightSplit']='count';$hole['geometry']['coordinates'][]=[[16.001,48.001],[16.001,48.004],[16.002,48.004],[16.002,48.001],[16.001,48.001]];
try{dm_plan_build($hole);throw new RuntimeException('holes connected to force count');}catch(InvalidArgumentException $expected){}
$bad=$in;$bad['params']['flightSplit']='count';$bad['params']['entryEnabled']=false;try{dm_plan_build($bad);throw new RuntimeException('missing H accepted');}catch(InvalidArgumentException $expected){}
// A single long straight leg must be cut inside the leg, not into independent geometry.
$line=$in;$line['type']='line';$line['geometry']=['type'=>'LineString','coordinates'=>[[16,48],[16,48.012]]];$line['params']['flightSplit']='count';$line['params']['flightCount']=2;
$lp=dm_plan_build($line);ft(count($lp['parts'])===2,'long leg split');ft($lp['parts'][0][count($lp['parts'][0])-1]['lat']>$lp['parts'][1][0]['lat'],'continuation overlaps on same line');
echo "PASS: shared raster repartition 2/3, time budgets, reserve/transit, replay, overlap, long legs, unreachable budget, holes and legacy.\n";
