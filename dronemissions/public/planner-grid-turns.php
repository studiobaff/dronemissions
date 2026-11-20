<?php
declare(strict_types=1);

/* Nominal circular fillets for a level video grid. DJI's actual flown trajectory
 * is device-dependent; these checks apply to the planned polygon and polyline. */
function dm_grid_segment_inside(array $a,array $b,array $rings): bool {
 foreach($rings as $ring)for($i=1;$i<count($ring);$i++)if(dm_plan_crosses($a,$b,$ring[$i-1],$ring[$i]))return false;
 $n=max(1,(int)ceil(hypot($b[0]-$a[0],$b[1]-$a[1])/.5));
 for($i=0;$i<=$n;$i++)if(!dm_plan_inside([$a[0]+($b[0]-$a[0])*$i/$n,$a[1]+($b[1]-$a[1])*$i/$n],$rings))return false;
 return true;
}

function dm_grid_turns(array $points,array $geo,float $radius,float $speed): array {
 $to=$geo['project'];$from=$geo['unproject'];
 $rings=array_map(fn($ring)=>array_map($to,$ring),$geo['geometry']['coordinates']);
 $out=[];$rounded=0;$stops=0;$minRadius=$radius;
 foreach($points as $i=>$point){
  $point['gridPass']=false;
  if($i===0||$i===count($points)-1||$point['breakBefore']||$points[$i+1]['breakBefore']){$out[]=$point;continue;}
  $a=$to([$points[$i-1]['lng'],$points[$i-1]['lat']]);$b=$to([$point['lng'],$point['lat']]);$c=$to([$points[$i+1]['lng'],$points[$i+1]['lat']]);
  $la=hypot($b[0]-$a[0],$b[1]-$a[1]);$lb=hypot($c[0]-$b[0],$c[1]-$b[1]);
  if(min($la,$lb)<.1){$out[]=$point;$stops++;continue;}
  $u=[($b[0]-$a[0])/$la,($b[1]-$a[1])/$la];$v=[($c[0]-$b[0])/$lb,($c[1]-$b[1])/$lb];
  $angle=acos(max(-1,min(1,$u[0]*$v[0]+$u[1]*$v[1])));
  if($angle<deg2rad(1)){$point['gridPass']=true;$out[]=$point;continue;}
  if($angle>=deg2rad(170)){$out[]=$point;$stops++;continue;}
  $cut=min($radius*tan($angle/2),.4*$la,.4*$lb);$actual=$cut/tan($angle/2);
  if($actual<1){$out[]=$point;$stops++;continue;}
  $sign=$u[0]*$v[1]-$u[1]*$v[0]>0?1:-1;
  $start=[$b[0]-$u[0]*$cut,$b[1]-$u[1]*$cut];$end=[$b[0]+$v[0]*$cut,$b[1]+$v[1]*$cut];
  $center=[$start[0]-$sign*$u[1]*$actual,$start[1]+$sign*$u[0]*$actual];
  $theta=atan2($start[1]-$center[1],$start[0]-$center[0]);$steps=max(2,(int)ceil($angle/deg2rad(30)));
  $arc=[];for($j=0;$j<=$steps;$j++){$t=$theta+$sign*$angle*$j/$steps;$arc[]=$j===0?$start:($j===$steps?$end:[$center[0]+cos($t)*$actual,$center[1]+sin($t)*$actual]);}
  // Check nominal arc at <= 0.5 m spacing, as well as exported chords.
  $safe=true;$fine=max($steps,(int)ceil($actual*$angle/.5));$prev=$start;
  for($j=1;$j<=$fine;$j++){$t=$theta+$sign*$angle*$j/$fine;$q=[$center[0]+cos($t)*$actual,$center[1]+sin($t)*$actual];if(!dm_grid_segment_inside($prev,$q,$rings)){$safe=false;break;}$prev=$q;}
  for($j=1;$safe&&$j<count($arc);$j++)$safe=dm_grid_segment_inside($arc[$j-1],$arc[$j],$rings);
  if(!$safe){$out[]=$point;$stops++;continue;}
  foreach($arc as $q){[$lng,$lat]=$from($q);$out[]=array_replace($point,['lng'=>$lng,'lat'=>$lat,'gridPass'=>true,'gridTurn'=>true,'capture'=>false]);}
  $minRadius=min($minRadius,$actual);$rounded++;
 }
 if(count($out)>5000)throw new InvalidArgumentException('Mehr als 5000 Kurvenstützpunkte; Raster verkleinern.');
 // Planning cap using 1 m/s² lateral acceleration. Not a vehicle performance claim.
 $effective=$rounded?min($speed,sqrt($minRadius)):$speed;
 foreach($out as &$point)$point['speed']=$effective;unset($point);
 return ['points'=>$out,'info'=>['roundedCorners'=>$rounded,'stopCorners'=>$stops,'requestedRadius'=>$radius,'minRadius'=>$rounded?$minRadius:null,'effectiveSpeed'=>$effective,'lateralAcceleration'=>1]];
}
