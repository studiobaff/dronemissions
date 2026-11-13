<?php
/* Fixed provider, immutable private snapshots, bounded requests and shared public-API quota. */
function dm_planner_elevations(array $coords,string $dataset): array {
 $locations=array_map(fn($p)=>sprintf('%.7f,%.7f',$p['lat'],$p['lng']),$coords);$key=hash('sha256',$dataset.':bilinear:'.implode('|',$locations));
 $dir=dm_private().'/terrain';if(!is_dir($dir))mkdir($dir,0700);$file=$dir.'/'.$key.'.json';
 if(is_file($file))return json_decode(file_get_contents($file),true,64,JSON_THROW_ON_ERROR);
 @set_time_limit(150);$lock=fopen($dir.'/rate','c+');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))throw new InvalidArgumentException('Geländeabfrage läuft bereits. Bitte gleich erneut versuchen.');
 try{
  if(is_file($file))return json_decode(file_get_contents($file),true,64,JSON_THROW_ON_ERROR);
  $rate=json_decode(stream_get_contents($lock)?:'{}',true)?:[];if(($rate['day']??'')!==gmdate('Y-m-d'))$rate=['day'=>gmdate('Y-m-d'),'count'=>0,'last'=>0];
  $chunks=array_chunk($locations,100);if(count($chunks)>65||($rate['count']??0)+count($chunks)>950)throw new InvalidArgumentException('DEM-Abfragelimit erreicht. Kleiner planen oder später erneut versuchen.');$elevations=[];
  foreach($chunks as $chunk){$wait=1.1-(microtime(true)-($rate['last']??0));if($wait>0)usleep((int)($wait*1000000));$rate['last']=microtime(true);$rate['count']++;rewind($lock);ftruncate($lock,0);fwrite($lock,json_encode($rate,JSON_THROW_ON_ERROR));fflush($lock);
   $ctx=stream_context_create(['http'=>['method'=>'POST','timeout'=>20,'follow_location'=>0,'header'=>"Content-Type: application/json\r\nUser-Agent: ".dm_user_agent('dronemissions/0.2')."\r\n",'content'=>json_encode(['locations'=>implode('|',$chunk),'interpolation'=>'bilinear'],JSON_THROW_ON_ERROR)],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);
   $stream=@fopen('https://api.opentopodata.org/v1/'.$dataset,'rb',false,$ctx);if(!$stream)throw new InvalidArgumentException('DEM-Dienst nicht erreichbar. Geländeexport bleibt gesperrt; keine stillen Ersatzhöhen.');try{$raw=stream_get_contents($stream,262145);}finally{fclose($stream);}if($raw===false||strlen($raw)>262144)throw new InvalidArgumentException('DEM-Antwort zu groß.');
   $response=json_decode($raw,true,64,JSON_THROW_ON_ERROR);if(($response['status']??'')!=='OK'||count($response['results']??[])!==count($chunk))throw new InvalidArgumentException('DEM-Abfrage fehlgeschlagen.');
   foreach($response['results'] as $i=>$row){[$lat,$lng]=array_map('floatval',explode(',',$chunk[$i]));if(!isset($row['elevation'],$row['location']['lat'],$row['location']['lng'])||abs($lat-(float)$row['location']['lat'])>1e-6||abs($lng-(float)$row['location']['lng'])>1e-6||!is_numeric($row['elevation'])||!is_finite((float)$row['elevation']))throw new InvalidArgumentException('Keine verlässlichen DEM-Daten an allen Punkten. Datensatz/Region prüfen.');$elevations[]=(float)$row['elevation'];}
  }
  $data=['snapshot'=>$key,'dataset'=>$dataset,'created'=>gmdate('c'),'elevations'=>$elevations];$json=json_encode($data,JSON_THROW_ON_ERROR);$tmp=tempnam($dir,'snapshot-');try{file_put_contents($tmp,$json,LOCK_EX);chmod($tmp,0600);rename($tmp,$file);}finally{if(is_file($tmp))unlink($tmp);}return $data;
 }finally{flock($lock,LOCK_UN);fclose($lock);}
}
