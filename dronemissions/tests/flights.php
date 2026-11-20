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
$bad=$in;$bad['params']['flightSplit']='time';$bad['params']['entryEnabled']=false;try{dm_plan_build($bad);throw new RuntimeException('missing H accepted');}catch(InvalidArgumentException $expected){}
// A single long straight leg must be cut inside the leg, not into independent geometry.
$line=$in;$line['type']='line';$line['geometry']=['type'=>'LineString','coordinates'=>[[16,48],[16,48.012]]];$line['params']['flightSplit']='count';$line['params']['flightCount']=2;
$lp=dm_plan_build($line);ft(count($lp['parts'])===2,'long leg split');ft($lp['parts'][0][count($lp['parts'][0])-1]['lat']>$lp['parts'][1][0]['lat'],'continuation overlaps on same line');
$tmp=sys_get_temp_dir().'/dm-flights-'.bin2hex(random_bytes(5));mkdir($tmp,0700);mkdir($tmp.'/tmp',0700);$oldEnv=getenv('DRONEMISSIONS_PRIVATE');putenv('DRONEMISSIONS_PRIVATE='.$tmp);
try{foreach($auto['parts'] as $i=>$part){$raw=dm_plan_kmz($auto,$part,['droneEnumValue'=>68],$i+1);$file=$tmp.'/flight.kmz';file_put_contents($file,$raw);$zip=new ZipArchive();$zip->open($file);$xml=dm_xml($zip->getFromName('wpmz/waylines.wpml'));$marks=$xml->xpath('//*[local-name()="Placemark"]');ft(count($marks)===count($part),'export matches flight preview');ft(dm_value($xml,'finishAction')==='goHome','each flight returns home');ft((float)dm_value($xml,'globalTransitionalSpeed')===$auto['params']['transitSpeed'],'export transit speed');foreach([$marks[0],end($marks)] as $mark)ft(dm_value($mark,'waypointTurnMode')==='toPointAndStopWithDiscontinuityCurvature','flight boundaries stop');$actions=array_map('strval',$xml->xpath('//*[local-name()="actionActuatorFunc"]'));ft(count(array_filter($actions,fn($v)=>$v==='startRecord'))===1&&count(array_filter($actions,fn($v)=>$v==='stopRecord'))===1,'one recording per flight');$zip->close();unlink($file);}}finally{putenv('DRONEMISSIONS_PRIVATE'.($oldEnv===false?'':'='.$oldEnv));rmdir($tmp.'/tmp');rmdir($tmp);}
echo "PASS: shared raster repartition 2/3, time budgets, reserve/transit, replay, overlap, long legs, unreachable budget, holes and legacy.\n";

ft(dm_mission_capture_type(['map_capture_type'=>'photo','details'=>['plannerCaptureMode'=>'video']])==='video','legacy video overview fallback');
ft(dm_mission_capture_type(['map_capture_type'=>'photo','map_capture_override'=>1,'details'=>['plannerCaptureMode'=>'video']])==='photo','explicit capture override retained');

// Explicit manual count is independent of battery estimate and old photo cap.
$manual=['name'=>'Synthetic manual helix','type'=>'helix','cameraId'=>'mavic3','geometry'=>['type'=>'Point','coordinates'=>[16,48]],'params'=>['shape'=>'cylinder','radius'=>30,'bottom'=>20,'top'=>60,'standoff'=>20,'spacingMode'=>'distance','photoDistance'=>2,'trackDistance'=>10,'flightSplit'=>'count','flightCount'=>1,'flightMinutes'=>3,'entryEnabled'=>false,'photoLimit'=>20]];
$single=dm_plan_build($manual);ft(count($single['points'])>200&&count($single['parts'])===1,'manual helix stays one above old limit');ft(!$single['flights']['homeKnown'],'no invented home estimate');
foreach(['helix','doubleHelix'] as $kind){$manual['type']=$kind;foreach([1,2,3] as $n){$manual['params']['flightCount']=$n;$r=dm_plan_build($manual);ft(count($r['parts'])===$n,'explicit helix count '.$kind.' '.$n);ft(!array_filter($r['points'],fn($p)=>$p['breakBefore']),'manual double helix continuous');$rr=dm_plan_build(array_intersect_key($r,array_flip(['name','type','cameraId','camera','geometry','params'])));ft($r['parts']===$rr['parts'],'manual helix replay');}}
$manual['type']='doubleHelix';$manual['params']['flightCount']=1;$joined=dm_plan_build($manual);$transit=array_filter($joined['points'],fn($p)=>($p['capture']??true)===false);ft(count($transit)>20,'cylinder top arc connects spirals');foreach($transit as $pt){ft($pt['height']===60.0,'top arc altitude');ft(abs(dm_distance($pt,['lat'=>48,'lng'=>16])-30)<.1,'top arc remains on radius');}
$manual['params']['shape']='hemisphere';$dome=dm_plan_build($manual);ft(count($dome['parts'])===1,'dome joins at apex');
// Exact budget endpoint must not choose the first candidate in the last 15%.
$pts=[];for($i=0;$i<=100;$i++)$pts[]=['lat'=>48+$i*.0001,'lng'=>16,'height'=>20,'pitch'=>-90,'yaw'=>0,'breakBefore'=>false,'capture'=>false,'gridPass'=>true];
$fp=['flightSplit'=>'time','flightMinutes'=>3,'reserveMinutes'=>0,'entryEnabled'=>true,'entryLat'=>48,'entryLng'=>16,'speed'=>3,'captureMode'=>'video','photoPause'=>0,'photoLimit'=>200,'transitSpeed'=>5,'verticalSpeed'=>2,'flightOverlap'=>0];
$auto=dm_plan_flights($pts,$fp);$first=$auto['info']['flights'][0];ft($first['budgetSeconds']>170&&$first['budgetSeconds']<=180.01,'automatic budget is utilized near last fitting point');
echo "PASS: manual 1/2/3 helix and double helix, >200 explicit points, continuous top arc, apex, replay, missing-home disclosure and automatic endpoint utilization.\n";
