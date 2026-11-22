<?php
declare(strict_types=1);
// Independent OpenDroneLog CSV/JSON format adapter. No upstream application code.
function dm_log_number(mixed $v,?float $min=null,?float $max=null): ?float {
 if($v===null||$v===''||!is_numeric($v)||!is_finite((float)$v))return null;$v=(float)$v;
 return ($min!==null&&$v<$min)||($max!==null&&$v>$max)?null:$v;
}
function dm_log_distance(array $a,array $b): float {
 $lat=deg2rad(($a['lat']+$b['lat'])/2);return hypot(($a['lat']-$b['lat'])*111319.49,($a['lng']-$b['lng'])*111319.49*cos($lat));
}
function dm_log_parse(string $raw,string $filename): array {
 if(strlen($raw)>16777216)throw new InvalidArgumentException('Maximal 16 MB pro Fluglog.');
 $raw=preg_replace('/^\xEF\xBB\xBF/','',$raw);$rows=[];$meta=[];$format='';
 if(str_starts_with(ltrim($raw),'{')){
  $d=json_decode($raw,true,64,JSON_THROW_ON_ERROR);
  if(($d['_exportInfo']['format']??'')!=='Open DroneLog JSON Export'||!is_array($d['flight']??null)||!is_array($d['telemetry']??null))throw new InvalidArgumentException('Bitte einen vollständigen OpenDroneLog-JSON-Export wählen.');
  $f=$d['flight'];$t=$d['telemetry'];$u=$d['_exportInfo']['units']??[];$format='json';
  foreach(['time','latitude','longitude','battery','batteryRemainedCapacity','isPhoto'] as $key)if(isset($t[$key])&&(!is_array($t[$key])||!array_is_list($t[$key])))throw new InvalidArgumentException('Telemetriespalten müssen Listen sein.');
  if(isset($d['track'])&&(!is_array($d['track'])||!array_is_list($d['track'])))throw new InvalidArgumentException('GPS-Spur muss eine Liste sein.');
  if(!is_array($u))throw new InvalidArgumentException('Ungültige Einheiten.');
  if(isset($f['totalDistance'])&&dm_log_number($f['totalDistance'],0)===null)throw new InvalidArgumentException('Ungültige Flugstrecke.');
  $meta=['display_name'=>$f['displayName']??$f['fileName']??$filename,'drone_model'=>$f['droneModel']??null,'drone_serial'=>$f['droneSerial']??null,'battery_serial'=>$f['batterySerial']??null,'start_time'=>$f['startTime']??null,'duration_secs'=>$f['durationSecs']??null,'total_distance_m'=>isset($f['totalDistance'])?$f['totalDistance']/(($u['distance']??'metric')==='imperial'?3.28084:1):null];
  $times=$t['time']??[];if(!is_array($times)||count($times)>50000)throw new InvalidArgumentException('Zu viele Telemetriepunkte.');
  $track=$d['track']??[];$aligned=count($track)===count($times);
  foreach($times as $i=>$time)$rows[]=['time'=>$time,'lat'=>$t['latitude'][$i]??($aligned?($track[$i][1]??null):null),'lng'=>$t['longitude'][$i]??($aligned?($track[$i][0]??null):null),'battery'=>$t['battery'][$i]??null,'capacity'=>$t['batteryRemainedCapacity'][$i]??null,'photo'=>$t['isPhoto'][$i]??null];
 }else{
  $stream=fopen('php://temp','w+');fwrite($stream,$raw);rewind($stream);$header=fgetcsv($stream,0,',','"','');
  if(!$header||count($header)!==count(array_unique($header))||!in_array('time_s',$header,true)||!in_array('metadata',$header,true))throw new InvalidArgumentException('Bitte den vollständigen OpenDroneLog-CSV-Export wählen, keine Zusammenfassung.');
  while(($r=fgetcsv($stream,0,',','"',''))!==false){if($r===[null])continue;if(count($r)!==count($header))throw new InvalidArgumentException('CSV-Zeile hat eine falsche Spaltenanzahl.');$r=array_combine($header,$r);if($r['metadata']!==''){$m=json_decode($r['metadata'],true,32,JSON_THROW_ON_ERROR);if($meta&&$m!==$meta)throw new InvalidArgumentException('Mehrere Flüge bitte als getrennte Dateien importieren.');$meta=$m;}
   $rows[]=['time'=>$r['time_s'],'lat'=>$r['lat']??null,'lng'=>$r['lng']??null,'battery'=>$r['battery_percent']??null,'capacity'=>$r['battery_remained_capacity_mah']??null,'photo'=>$r['is_photo']??null];if(count($rows)>50000)throw new InvalidArgumentException('Zu viele Telemetriepunkte.');
  }fclose($stream);if(($meta['format']??'')!=='Open DroneLog CSV Export')throw new InvalidArgumentException('OpenDroneLog-Metadaten fehlen.');$format='csv';
 }
 $samples=[];$warnings=[];$previous=null;$photoWas=false;$photoCount=0;$photoKnown=false;$battery=[];$capacity=[];$batteryJump=false;$capacityJump=false;$gaps=0;
 foreach($rows as $r){$time=dm_log_number($r['time'],0,172800);if($time===null)throw new InvalidArgumentException('Ungültiger Zeitwert im Fluglog.');if($previous!==null&&$time<$previous)throw new InvalidArgumentException('Zeitwerte laufen rückwärts. Bitte Flüge getrennt exportieren.');if($previous!==null&&$time-$previous>5)$gaps++;$previous=$time;
  $lat=dm_log_number($r['lat'],-90,90);$lng=dm_log_number($r['lng'],-180,180);$b=dm_log_number($r['battery'],0,100);$c=dm_log_number($r['capacity'],0,100000);
  if($b!==null){if($battery&&$b-end($battery)['value']>5)$batteryJump=true;$battery[]=['time'=>$time,'value'=>$b];}if($c!==null){if($capacity&&$c-end($capacity)['value']>200)$capacityJump=true;$capacity[]=['time'=>$time,'value'=>$c];}
  if($r['photo']!==null&&$r['photo']!==''){$photoKnown=true;$on=in_array($r['photo'],[true,1,'1'],true);if($on&&!$photoWas)$photoCount++;$photoWas=$on;}
  $samples[]=['time'=>$time,'lat'=>$lat,'lng'=>$lng,'battery'=>$b];
 }
 $span=count($samples)>1?end($samples)['time']-$samples[0]['time']:null;$reported=dm_log_number($meta['duration_secs']??null,0,172800);$duration=$reported??$span;
 if($duration===null||$duration<=0)throw new InvalidArgumentException('Keine auswertbare Flugdauer vorhanden.');
 if($span===null||$span===0)$warnings[]='Keine durchgehende Telemetrie; Dauer nur aus Export-Metadaten.';
 if($span!==null&&abs($span-$duration)>max(5,$duration*.05))$warnings[]='Telemetrie-Zeitraum weicht von der gemeldeten Flugdauer ab.';
 if($gaps)$warnings[]=$gaps.' Telemetrielücken über 5 Sekunden.';
 $first=$battery[0]??null;$last=$battery?end($battery):null;$coverage=$first&&$last?($last['time']-$first['time'])/$duration:0;
 $used=$first&&$last&&$coverage>=.8&&!$batteryJump&&$first['value']>=$last['value']?$first['value']-$last['value']:null;
 if($used===null)$warnings[]='Akkuverbrauch nicht zuverlässig bestimmbar (fehlende Werte, unvollständiger Zeitraum oder Akkuwechsel).';
 $cf=$capacity[0]??null;$cl=$capacity?end($capacity):null;$mah=$cf&&$cl&&($cl['time']-$cf['time'])/$duration>=.8&&!$capacityJump&&$cf['value']>=$cl['value']?$cf['value']-$cl['value']:null;
 $track=[];$valid=array_values(array_filter($samples,fn($s)=>$s['lat']!==null&&$s['lng']!==null&&!(abs($s['lat'])<.000001&&abs($s['lng'])<.000001)));$stride=max(1,(int)ceil(count($valid)/1200));foreach($valid as $i=>$s)if($i%$stride===0||$i===count($valid)-1)$track[]=$s;
 $text=function($key,$fallback='')use($meta){$value=is_scalar($meta[$key]??null)?(string)$meta[$key]:$fallback;return preg_match('/^.{0,200}/us',$value,$m)?$m[0]:'';};
 $summary=['name'=>$text('display_name',$filename),'model'=>$text('drone_model'),'droneSerial'=>$text('drone_serial'),'batterySerial'=>$text('battery_serial'),'startTime'=>$text('start_time'),'durationSeconds'=>$duration,'telemetrySeconds'=>$span,'distanceMeters'=>dm_log_number($meta['total_distance_m']??null,0,10000000),'batteryStart'=>$first['value']??null,'batteryEnd'=>$last['value']??null,'batteryUsedPercent'=>$used,'batteryUsedMah'=>$mah,'batteryPerMinute'=>$used!==null?$used/($duration/60):null,'photoEvents'=>$photoKnown?$photoCount:null,'sampleCount'=>count($samples),'warnings'=>$warnings,'format'=>$format];
 $fingerprint=$summary['startTime']!==''?hash('sha256',json_encode([$summary['startTime'],$summary['droneSerial'],$summary['batterySerial'],round($duration,1),array_map(fn($p)=>[round($p['time'],1),round($p['lat'],6),round($p['lng'],6)],$track)])):hash('sha256',$raw);
 return ['summary'=>$summary,'track'=>$track,'fingerprint'=>$fingerprint];
}
function dm_log_candidates(array $log,array $missions): array {
 if(count($log['track'])<3)return [];$out=[];$track=$log['track'];
 foreach($missions as $m){$points=$m['details']['points']??[];if(count($points)<2)continue;$route=[];$stride=max(1,(int)ceil(count($points)/100));foreach($points as $i=>$p)if($i%$stride===0||$i===count($points)-1)$route[]=$p;
  // Compare only route samples: takeoff and return legs may extend beyond the mission.
  $near=0;$sum=0;foreach($route as $p){$best=INF;foreach($track as $q)$best=min($best,dm_log_distance($p,$q));if($best<=35)$near++;$sum+=min($best,10000);}
  $coverage=$near/count($route);if($coverage<.5)continue;
  $nameMatch=strtolower(trim($m['name']))===strtolower(trim($log['summary']['name']));
  $out[]=['id'=>$m['id'],'versionId'=>$m['versionId'],'name'=>$m['name'],'coverage'=>round($coverage,3),'meanDistance'=>round($sum/count($route),1),'nameMatch'=>$nameMatch];
 }
 usort($out,fn($a,$b)=>($b['coverage']<=>$a['coverage'])?:($a['meanDistance']<=>$b['meanDistance']));return array_slice($out,0,10);
}
