<?php
declare(strict_types=1);
// Official ED-269 data is fetched on demand, never bundled with public source releases.
function dm_zone_fetch(string $url,int $limit): string {
 $context=stream_context_create(['http'=>['timeout'=>12,'follow_location'=>0,'header'=>"User-Agent: DroneMissions/1.0\r\n"],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);
 $stream=@fopen($url,'rb',false,$context);if(!$stream)throw new RuntimeException('Geozonen-Quelle nicht erreichbar.');
 try{$raw=stream_get_contents($stream,$limit+1);if($raw===false||strlen($raw)>$limit)throw new RuntimeException('Geozonen-Daten zu groß.');return $raw;}finally{fclose($stream);}
}
function dm_zone_release(string $html,?string $today=null): array {
 $today=$today??(new DateTimeImmutable('now',new DateTimeZone('Europe/Vienna')))->format('Y-m-d');$chosen=null;
 preg_match_all('~<tr\b[^>]*>(.*?)</tr>~is',$html,$rows);
 foreach($rows[1] as $row){
  if(!preg_match('~href=["\'](/jart/prj3/ac/releases/de/upload/Dronespace/[^"\'<>]+\.zip)["\']~i',$row,$link))continue;
  $text=html_entity_decode(strip_tags($row),ENT_QUOTES|ENT_HTML5,'UTF-8');
  if(!preg_match('~(\d{1,2})\.(\d{1,2})\.(\d{4})~',$text,$date))continue;
  $start=sprintf('%04d-%02d-%02d',(int)$date[3],(int)$date[2],(int)$date[1]);if($start>$today)continue;
  preg_match_all('~(\d{1,2})\.(\d{1,2})\.(\d{4})~',$text,$dates,PREG_SET_ORDER);$end=isset($dates[1])?sprintf('%04d-%02d-%02d',(int)$dates[1][3],(int)$dates[1][2],(int)$dates[1][1]):null;if($end!==null&&$end<$today)continue;
  if(!$chosen||$start>=$chosen['validFrom'])$chosen=['url'=>'https://www.austrocontrol.at'.$link[1],'validFrom'=>$start,'validTo'=>$end];
 }
 if(!$chosen)throw new RuntimeException('Kein gültiger Geozonen-Datensatz gefunden.');return $chosen;
}
function dm_zone_decode(string $zip): array {
 $tmp=tempnam(dm_private().'/tmp','zones-');
 try{file_put_contents($tmp,$zip);$z=new ZipArchive();if($z->open($tmp)!==true)throw new RuntimeException('Geozonen-Archiv ungültig.');$raw=null;
  try{if($z->numFiles>20)throw new RuntimeException('Geozonen-Archiv ungültig.');for($i=0;$i<$z->numFiles;$i++){$entry=$z->statIndex($i);if(str_ends_with(strtolower($entry['name']),'.json')){if($entry['size']>8388608)throw new RuntimeException('Geozonen-Daten zu groß.');$raw=$z->getFromIndex($i);break;}}}finally{$z->close();}
  if(!is_string($raw))throw new RuntimeException('Geozonen-Daten fehlen.');$zones=json_decode(str_starts_with($raw,"\xEF\xBB\xBF")?substr($raw,3):$raw,true,64,JSON_THROW_ON_ERROR);
  if(!is_array($zones)||!array_is_list($zones)||!count($zones)||count($zones)>5000)throw new RuntimeException('Geozonen-Daten ungültig.');
  foreach($zones as $zone){if(!is_string($zone['name']??null)||!is_array($zone['geometry']??null))throw new RuntimeException('Geozonen-Struktur ungültig.');foreach($zone['geometry'] as $g)if(!in_array($g['horizontalProjection']['type']??null,['Polygon','MultiPolygon'],true)||!is_array($g['horizontalProjection']['coordinates']??null))throw new RuntimeException('Unbekannte Geozonen-Geometrie.');}
  return $zones;
 }finally{if(is_file($tmp))unlink($tmp);}
}
function dm_zones(): array {
 $cache=dm_private().'/uas-zones-cache.json';$cached=is_file($cache)?json_decode(file_get_contents($cache),true):null;
 if(is_array($cached)&&time()-(int)($cached['checkedAt']??0)<3600)return $cached+['stale'=>false];
 $lock=fopen(dm_private().'/uas-zones.lock','c');if(!$lock)throw new RuntimeException('Geozonen-Cache nicht verfügbar.');
 try{
  if(!flock($lock,LOCK_EX|LOCK_NB)){if(is_array($cached))return $cached+['stale'=>true];throw new RuntimeException('Geozonen werden gerade geladen. Bitte erneut versuchen.');}
  $page='https://www.austrocontrol.at/luftfahrtbehoerde/lizenzen__bewilligungen/drohnen/geografische_zonen';
  $release=dm_zone_release(dm_zone_fetch($page,2097152));
  $zones=is_array($cached)&&($cached['downloadURL']??'')===$release['url']?$cached['zones']:dm_zone_decode(dm_zone_fetch($release['url'],8388608));
  $result=['source'=>'Austro Control · ED-269','sourceURL'=>$page,'downloadURL'=>$release['url'],'validFrom'=>$release['validFrom'],'validTo'=>$release['validTo'],'checkedAt'=>time(),'zones'=>$zones];
  $tmp=tempnam(dm_private(),'.zones-');try{file_put_contents($tmp,json_encode($result,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR),LOCK_EX);chmod($tmp,0600);if(!rename($tmp,$cache))throw new RuntimeException('Geozonen nicht gespeichert.');}finally{if(is_file($tmp))unlink($tmp);}
  return $result+['stale'=>false];
 }catch(Throwable $e){if(is_array($cached))return $cached+['stale'=>true];throw $e;}finally{flock($lock,LOCK_UN);fclose($lock);}
}
