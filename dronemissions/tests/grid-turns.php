<?php
declare(strict_types=1);
require __DIR__.'/../public/lib.php';require __DIR__.'/../public/planner-core.php';
function gt(bool $ok,string $why): void {if(!$ok)throw new RuntimeException($why);}
$in=['name'=>'Synthetic video turns','type'=>'grid','cameraId'=>'mavic3','geometry'=>['type'=>'Polygon','coordinates'=>[[[16,48],[16.003,48],[16.003,48.003],[16,48.003],[16,48]]]],'params'=>['captureMode'=>'video','height'=>70,'gridMotion'=>'smooth','gridTurnRadius'=>10,'speed'=>5,'photoLimit'=>200,'sectionOverlap'=>2,'terrainMode'=>'off']];
$plan=dm_plan_build($in);$info=$plan['gridTurns'];
gt($info['roundedCorners']>0&&$info['stopCorners']===0,'rectangle corners rounded');
gt($plan['summary']['photos']===0,'no photos');gt($info['effectiveSpeed']<=sqrt(10)+1e-7,'radius speed cap');
gt(count($plan['points'])>2*$plan['summary']['rows'],'explicit turn support points');
$replay=dm_plan_build(array_intersect_key($plan,array_flip(['name','type','cameraId','camera','geometry','params'])));
gt($replay['routeSha256']===$plan['routeSha256'],'deterministic replay');
function inside_plan(array $input,array $plan):void {
 $geo=dm_plan_geometry($input['geometry']);$to=$geo['project'];$rings=array_map(fn($r)=>array_map($to,$r),$geo['geometry']['coordinates']);
 foreach($plan['parts'] as $part)for($i=1;$i<count($part);$i++)gt(dm_grid_segment_inside($to([$part[$i-1]['lng'],$part[$i-1]['lat']]),$to([$part[$i]['lng'],$part[$i]['lat']]),$rings),'exported segment leaves polygon/hole');
}
inside_plan($in,$plan);
$hole=$in;$hole['geometry']['coordinates'][]=[[16.001,48.001],[16.001,48.002],[16.002,48.002],[16.002,48.001],[16.001,48.001]];
$holePlan=dm_plan_build($hole);inside_plan($hole,$holePlan);gt(count($holePlan['parts'])>1,'hole separates flights');
$cross=$in;$cross['params']['crossGrid']=true;$crossPlan=dm_plan_build($cross);inside_plan($cross,$crossPlan);gt(count(array_filter($crossPlan['points'],fn($p)=>$p['breakBefore']))>0,'cross pass stays separate');
$reverse=$in;$reverse['params']+=['entryEnabled'=>true,'entryLat'=>48.003,'entryLng'=>16.003];inside_plan($reverse,dm_plan_build($reverse));
$stop=$in;$stop['params']['gridMotion']='stop';$stopPlan=dm_plan_build($stop);gt($stopPlan['gridTurns']===null&&count($stopPlan['points'])===2*$stopPlan['summary']['rows'],'legacy grid endpoints');
$photo=$in;$photo['params']['captureMode']='photo';$a=dm_plan_build($photo);$photo['params']['gridMotion']='stop';$b=dm_plan_build($photo);gt($a['points']===$b['points']&&$a['parts']===$b['parts'],'photo geometry preserved');
foreach([['gridMotion'=>'invalid'],['gridTurnRadius'=>0],['terrainMode'=>'follow']] as $bad){$q=$in;$q['params']=array_replace($q['params'],$bad);try{dm_plan_build($q);throw new RuntimeException('invalid motion accepted');}catch(InvalidArgumentException $e){}}
$geo=dm_plan_geometry($in['geometry']);$from=$geo['unproject'];$pose=function($x,$y)use($from){[$lng,$lat]=$from([$x,$y]);return ['lng'=>$lng,'lat'=>$lat,'height'=>70,'yaw'=>0,'pitch'=>-90,'breakBefore'=>false,'poi'=>null];};
$back=dm_grid_turns([$pose(20,20),$pose(40,20),$pose(20,20)],$geo,10,5);gt($back['info']['stopCorners']===1&&!$back['points'][1]['gridPass'],'reversal has explicit stop');
$short=dm_grid_turns([$pose(20,20),$pose(20.5,20),$pose(20.5,20.5)],$geo,10,5);gt($short['info']['stopCorners']===1,'too little room stops');
$split=$in;$split['params']['photoLimit']=20;$splitPlan=dm_plan_build($split);foreach($splitPlan['parts'] as $part)gt(count($part)<=20,'section limit');
$tmp=sys_get_temp_dir().'/dm-turns-'.bin2hex(random_bytes(5));mkdir($tmp,0700);mkdir($tmp.'/tmp',0700);$old=getenv('DRONEMISSIONS_PRIVATE');putenv('DRONEMISSIONS_PRIVATE='.$tmp);
try{
 foreach([$plan,$splitPlan,$stopPlan] as $case)foreach($case['parts'] as $part){
  $bytes=dm_plan_kmz($case,$part,['droneEnumValue'=>68]);$path=$tmp.'/test.kmz';file_put_contents($path,$bytes);$zip=new ZipArchive();$zip->open($path);
  foreach(['wpmz/template.kml','wpmz/waylines.wpml'] as $file){
   $xml=dm_xml($zip->getFromName($file));$marks=$xml->xpath('//*[local-name()="Placemark"]');gt(count($marks)===count($part),'preview/export waypoint count');$lastDamping=0;
   foreach($marks as $i=>$mark){$pass=$case['params']['gridMotion']==='smooth'&&($part[$i]['gridPass']??false)&&$i>0&&$i<count($part)-1;
    gt(dm_value($mark,'waypointTurnMode')===($pass?'toPointAndPassWithContinuityCurvature':'toPointAndStopWithDiscontinuityCurvature'),'waypoint mode');
    $d=(float)dm_value($mark,'waypointTurnDampingDist');if($i)gt($lastDamping+$d<dm_distance($part[$i-1],$part[$i]),'adjacent damping sum');$lastDamping=$d;
    gt(abs((float)dm_value($mark,'waypointSpeed')-($part[$i]['speed']??5))<.001,'export speed');
   }
   $actions=array_map('strval',$xml->xpath('//*[local-name()="actionActuatorFunc"]'));
   gt(count(array_filter($actions,fn($v)=>$v==='startRecord'))===1&&count(array_filter($actions,fn($v)=>$v==='stopRecord'))===1,'one recording per section');gt(!in_array('takePhoto',$actions)&&!in_array('hover',$actions),'no photo/hover');
  }$zip->close();unlink($path);
 }
}finally{putenv('DRONEMISSIONS_PRIVATE'.($old===false?'':'='.$old));rmdir($tmp.'/tmp');rmdir($tmp);}
echo "PASS: grid fillets, polygon/holes, speed cap, replay, entry/cross-grid, explicit fallback stops, photo compatibility, section limits and both WPML files.\n";
