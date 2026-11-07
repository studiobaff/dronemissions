<?php
declare(strict_types=1);
require_once __DIR__.'/zones.php';
function dm_location_coords(mixed $lat,mixed $lng): array {
 if(!is_numeric($lat)||!is_numeric($lng)||!is_finite((float)$lat)||!is_finite((float)$lng)||(float)$lat<46.3||(float)$lat>49.1||(float)$lng<9.4||(float)$lng>17.3)throw new InvalidArgumentException('Standortinformationen sind derzeit für Österreich verfügbar.');return [round((float)$lat,4),round((float)$lng,4)];
}
function dm_location_cache(string $kind,string $key,int $ttl,callable $fetch): array {
 $dir=dm_private().'/location-cache';if(!is_dir($dir)&&!mkdir($dir,0700))throw new RuntimeException('Standortdaten nicht verfügbar.');$path=$dir.'/'.$kind.'-'.hash('sha256',$key).'.json';$cached=is_file($path)?json_decode(file_get_contents($path),true):null;
 if(is_array($cached)&&time()-($cached['checkedAt']??0)<$ttl)return $cached+['stale'=>false];
 $lock=fopen($path.'.lock','c');if(!$lock)throw new RuntimeException('Standortdaten nicht verfügbar.');
 try{if(!flock($lock,LOCK_EX|LOCK_NB)){if(is_array($cached))return $cached+['stale'=>true];throw new RuntimeException('Standortdaten werden geladen. Bitte erneut versuchen.');}
  $result=$fetch()+['checkedAt'=>time()];$tmp=tempnam($dir,'.location-');try{file_put_contents($tmp,json_encode($result,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR));chmod($tmp,0600);rename($tmp,$path);}finally{if(is_file($tmp))unlink($tmp);}return $result+['stale'=>false];
 }catch(Throwable $e){if(is_array($cached))return $cached+['stale'=>true];throw $e;}finally{flock($lock,LOCK_UN);fclose($lock);}
}
function dm_weather_normalize(array $raw): array {
 $p=$raw['features'][0]['properties']['parameters']??[];$times=$raw['timestamps']??[];if(!$times||!is_array($p)||!isset($raw['reference_time']))throw new RuntimeException('Wetterdaten unvollständig.');$hours=[];
 $number=fn($name,$i)=>isset($p[$name]['data'][$i])&&is_numeric($p[$name]['data'][$i])?(float)$p[$name]['data'][$i]:null;
 foreach($times as $i=>$time){if(!is_string($time)||strtotime($time)===false)continue;$u=$number('10u',$i);$v=$number('10v',$i);$gust=$number('10fg',$i);$hours[]=['time'=>$time,'temperature'=>$number('2t',$i),'wind'=>$u!==null&&$v!==null?round(hypot($u,$v)*3.6,1):null,'gust'=>$gust!==null?round($gust*3.6,1):null,'rain'=>$number('tp',$i),'cloud'=>$number('tcc',$i)];}
 if(!$hours)throw new RuntimeException('Wetterdaten fehlen.');return ['source'=>'GeoSphere Austria · C-LAEF 1 km','referenceTime'=>$raw['reference_time'],'hours'=>$hours];
}
function dm_location_weather(float $lat,float $lng): array {
 $lat=round($lat,3);$lng=round($lng,3);return dm_location_cache('weather',$lat.','.$lng,3600,function()use($lat,$lng){$url='https://dataset.api.hub.geosphere.at/v1/timeseries/forecast/nwp-v2-1h-1km?'.http_build_query(['parameters'=>'2t,10u,10v,10fg,tp,tcc','lat_lon'=>$lat.','.$lng,'output_format'=>'geojson']);return dm_weather_normalize(json_decode(dm_zone_fetch($url,2097152),true,64,JSON_THROW_ON_ERROR));});
}
function dm_location_elevation(float $lat,float $lng): array {
 return dm_location_cache('elevation',$lat.','.$lng,2592000,function()use($lat,$lng){
  $file=dm_private().'/location-cache/elevation-rate.json';$lock=fopen($file.'.lock','c');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))throw new RuntimeException('Höhendaten werden abgefragt. Bitte erneut versuchen.');
  try{$rate=is_file($file)?json_decode(file_get_contents($file),true):[];$now=microtime(true);$day=gmdate('Y-m-d');if(($rate['day']??'')!==$day)$rate=['day'=>$day,'count'=>0,'last'=>0];if($now-($rate['last']??0)<1||($rate['count']??0)>=1000)throw new RuntimeException('Höhendienst-Abfragelimit erreicht.');$rate['last']=$now;$rate['count']++;file_put_contents($file,json_encode($rate),LOCK_EX);chmod($file,0600);
   $raw=json_decode(dm_zone_fetch('https://api.opentopodata.org/v1/eudem25m?'.http_build_query(['locations'=>$lat.','.$lng]),1048576),true,32,JSON_THROW_ON_ERROR);$height=$raw['results'][0]['elevation']??null;if(($raw['status']??'')!=='OK'||!is_numeric($height))throw new RuntimeException('Keine Geländehöhe verfügbar.');return ['elevation'=>round((float)$height),'source'=>'EU-DEM · Open Topo Data','resolution'=>25];
  }finally{flock($lock,LOCK_UN);fclose($lock);}
 });
}
