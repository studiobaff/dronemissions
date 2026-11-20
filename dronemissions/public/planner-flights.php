<?php
declare(strict_types=1);

/* Flights are derived ranges of one saved raster, never separate source plans.
 * Transit estimates are straight-line assumptions, not navigation instructions. */
function dm_flight_point(array $a,array $b,float $t): array {
 if($t<=1e-9)return $a;if($t>=1-1e-9)return $b;
 $p=$a;foreach(['lat','lng','height','pitch'] as $k)$p[$k]=$a[$k]+($b[$k]-$a[$k])*$t;
 $p['yaw']=$a['yaw']+fmod($b['yaw']-$a['yaw']+540,360)*$t-180*$t;
 $p['capture']=false;$p['breakBefore']=false;
 if(isset($a['speed'])||isset($b['speed']))$p['speed']=min($a['speed']??15,$b['speed']??15);
 $p['gridPass']=($a['gridPass']??false)&&($b['gridPass']??false);
 return $p;
}
function dm_flight_path(array $points): array {
 $dist=[0.0];for($i=1;$i<count($points);$i++)$dist[]=end($dist)+hypot(dm_distance($points[$i-1],$points[$i]),$points[$i]['height']-$points[$i-1]['height']);
 return ['points'=>$points,'dist'=>$dist,'length'=>end($dist)];
}
function dm_flight_slice(array $path,float $start,float $end): array {
 $p=$path['points'];$d=$path['dist'];$at=function($s)use($p,$d){for($i=1;$i<count($p);$i++)if($s<=$d[$i]+1e-8)return dm_flight_point($p[$i-1],$p[$i],($s-$d[$i-1])/max(1e-9,$d[$i]-$d[$i-1]));return end($p);};
 $out=[$at($start)];for($i=1;$i<count($p)-1;$i++)if($d[$i]>$start+1e-6&&$d[$i]<$end-1e-6)$out[]=$p[$i];
 $out[]=$at($end);$out[0]['breakBefore']=false;return $out;
}
function dm_flight_estimate(array $part,array $home,array $p): array {
 $speed=$p['speed'];$route=0.0;$photo=$p['captureMode']!=='video';
 foreach($part as $i=>$pt){if($i)$route+=hypot(dm_distance($part[$i-1],$pt),$pt['height']-$part[$i-1]['height'])/min($part[$i-1]['speed']??$speed,$pt['speed']??$speed);if($photo&&($pt['capture']??true))$route+=$p['photoPause']+2;elseif($i===0||$i===count($part)-1||!($pt['gridPass']??false))$route+=2;}
 $first=$part[0];$last=$part[count($part)-1];
 $out=dm_distance($home,$first)/$p['transitSpeed']+abs($first['height'])/$p['verticalSpeed'];
 $back=dm_distance($last,$home)/$p['transitSpeed']+abs($last['height'])/$p['verticalSpeed'];
 $reserve=$p['reserveMinutes']*60;
 return ['routeSeconds'=>$route,'outboundSeconds'=>$out,'returnSeconds'=>$back,'reserveSeconds'=>$reserve,'budgetSeconds'=>$route+$out+$back+$reserve];
}
function dm_plan_flights(array $points,array $p): array {
 $mode=$p['flightSplit']??'legacy';if(!in_array($mode,['legacy','time','count'],true))throw new InvalidArgumentException('Flugaufteilung prüfen.');
 if($mode==='legacy')return ['parts'=>null,'params'=>['flightSplit'=>'legacy'],'info'=>null];
 $minutes=dm_pnum($p,'flightMinutes',3,60,15);$count=(int)dm_pnum($p,'flightCount',1,100,2);
 if($count!== (int)($p['flightCount']??2)||$count!=dm_pnum($p,'flightCount',1,100,2))throw new InvalidArgumentException('Anzahl Flüge muss ganzzahlig sein.');
 $reserve=dm_pnum($p,'reserveMinutes',0,15,2);if($reserve>=$minutes)throw new InvalidArgumentException('Reserve muss kleiner als die Flugzeit pro Akku sein.');
 $overlap=dm_pnum($p,'flightOverlap',0,100,15);
 if(($p['entryEnabled']??false)!==true)throw new InvalidArgumentException('Abflugpunkt H auf der Karte setzen und aktivieren.');
 $home=['lat'=>dm_pnum($p,'entryLat',-80,80),'lng'=>dm_pnum($p,'entryLng',-180,180)];
 $opts=['flightSplit'=>$mode,'flightMinutes'=>$minutes,'flightCount'=>$count,'reserveMinutes'=>$reserve,'flightOverlap'=>$overlap,'transitSpeed'=>dm_pnum($p,'transitSpeed',.2,15,5),'verticalSpeed'=>dm_pnum($p,'verticalSpeed',.2,5,2)];
 $costParams=$opts+$p;$chains=[];$chain=[];foreach($points as $pt){if($chain&&$pt['breakBefore']){$chains[]=dm_flight_path($chain);$chain=[];}$chain[]=$pt;}if($chain)$chains[]=dm_flight_path($chain);
 if($mode==='count'&&$count<count($chains))throw new InvalidArgumentException('Der Umriss erfordert mindestens '.count($chains).' getrennte Flüge (Löcher/Kreuzraster).');
 $allocation=array_fill(0,count($chains),1);
 for($i=count($chains);$mode==='count'&&$i<$count;$i++){$scores=[];foreach($chains as $k=>$path)$scores[$k]=$path['length']/$allocation[$k];$allocation[array_search(max($scores),$scores)]++;}
 $parts=[];$estimates=[];$limit=(int)($p['photoLimit']??200);$budget=$minutes*60;
 foreach($chains as $k=>$path){
  if(count($path['points'])<2||$path['length']<.1)throw new InvalidArgumentException('Flugbereich ist zu kurz.');
  $cursor=0.0;$flight=0;$lastStart=0.0;
  while($cursor<$path['length']-.001){
   if(count($parts)>=100)throw new InvalidArgumentException('Mehr als 100 Flüge; Zeitbudget oder Gebiet prüfen.');
   $start=$flight?max($lastStart+($cursor-$lastStart)*.75,$cursor-$overlap):0.0;
   $fits=function($end)use($path,$start,$home,$costParams,$limit,$budget){$part=dm_flight_slice($path,$start,$end);return count($part)<=$limit&&count($part)<=200&&dm_flight_estimate($part,$home,$costParams)['budgetSeconds']<=$budget;};
   if($mode==='count')$end=$path['length']*($flight+1)/$allocation[$k];
   else{
    if(!$fits(min($path['length'],$cursor+.1)))throw new InvalidArgumentException('Zeitbudget reicht für Anflug, Rückflug, Reserve und Fortsetzung nicht aus. Startpunkt näher setzen oder Budget erhöhen.');
    $lo=$cursor+.1;$hi=$path['length'];for($n=0;$n<40;$n++){$mid=($lo+$hi)/2;if($fits($mid))$lo=$mid;else $hi=$mid;}$end=$lo;
    if($path['length']-$end<.001)$end=$path['length'];
    // Prefer an existing lane/turn boundary when it costs at most 15% of progress.
    if($end<$path['length']-.001)foreach($path['dist'] as $j=>$d)if($d>$cursor+($end-$cursor)*.85&&$d<=$end&&!($path['points'][$j]['gridTurn']??false)){$end=$d;}
   }
   if($end-$cursor<.05)throw new InvalidArgumentException('Zu viele Flüge für diese Route.');
   $part=dm_flight_slice($path,$start,$end);
   if(count($part)>min(200,$limit))throw new InvalidArgumentException('Die gewählte Anzahl Flüge überschreitet das Wegpunktlimit. Mehr Flüge wählen oder automatisch nach Minuten aufteilen.');
   $estimate=dm_flight_estimate($part,$home,$costParams);$estimate['overBudget']=$estimate['budgetSeconds']>$budget+.01;$estimate['overlapMeters']=$cursor-$start;
   $parts[]=$part;$estimates[]=$estimate;$lastStart=$start;$cursor=$end;$flight++;
  }
 }
 return ['parts'=>$parts,'params'=>$opts,'info'=>['home'=>$home,'minutes'=>$minutes,'mode'=>$mode,'flights'=>$estimates,'overBudget'=>count(array_filter($estimates,fn($e)=>$e['overBudget']))]];
}
