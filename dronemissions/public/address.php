<?php
declare(strict_types=1);
function dm_address_results(array $payload): array {
 $out=[];if(!is_array($payload['features']??null))throw new RuntimeException('Adresssuche nicht verfügbar.');
 foreach(array_slice($payload['features'],0,5) as $feature){$p=$feature['properties']??[];$c=$feature['geometry']['coordinates']??[];if(($feature['geometry']['type']??'')!=='Point'||strtoupper($p['countrycode']??'')!=='AT'||count($c)!==2||!is_numeric($c[0])||!is_numeric($c[1])||abs((float)$c[0])>180||abs((float)$c[1])>90)continue;
  $street=trim(($p['street']??'').' '.($p['housenumber']??''));$city=trim(($p['postcode']??'').' '.($p['city']??$p['town']??$p['village']??''));$parts=array_filter([$p['name']??'',$street,$city,$p['state']??'']);$label=implode(', ',array_unique($parts));if(!$label)continue;$out[]=['label'=>$label,'lat'=>(float)$c[1],'lng'=>(float)$c[0]];
 }
 return $out;
}
function dm_address(mixed $query,string $endpoint): array {
 $query=dm_text($query,200);if(strlen($query)<3)throw new InvalidArgumentException('Bitte mindestens drei Zeichen eingeben.');
 if(!filter_var($endpoint,FILTER_VALIDATE_URL)||parse_url($endpoint,PHP_URL_SCHEME)!=='https')throw new RuntimeException('Adressdienst nicht eingerichtet.');
 $dir=dm_private().'/address-cache';if(!is_dir($dir)&&!mkdir($dir,0700))throw new RuntimeException('Adresssuche nicht verfügbar.');$file=$dir.'/'.hash('sha256',$endpoint.'|'.strtolower($query)).'.json';
 if(is_file($file)&&time()-filemtime($file)<86400)return ['results'=>json_decode(file_get_contents($file),true,32,JSON_THROW_ON_ERROR),'source'=>'Photon / OpenStreetMap'];
 $lock=fopen($dir.'/request.lock','c+');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))throw new InvalidArgumentException('Eine Adresssuche läuft bereits. Bitte kurz warten.');
 try{
  $last=(float)stream_get_contents($lock);if(microtime(true)-$last<1)throw new InvalidArgumentException('Bitte eine Sekunde bis zur nächsten Suche warten.');ftruncate($lock,0);rewind($lock);fwrite($lock,(string)microtime(true));fflush($lock);
  require_once __DIR__.'/zones.php';$url=rtrim($endpoint,'/').'/?'.http_build_query(['q'=>$query,'limit'=>5,'lang'=>'de','countrycode'=>'AT']);$raw=dm_zone_fetch($url,1048576);$results=dm_address_results(json_decode($raw,true,32,JSON_THROW_ON_ERROR));
  $tmp=tempnam($dir,'.address-');try{file_put_contents($tmp,json_encode($results,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR),LOCK_EX);chmod($tmp,0600);rename($tmp,$file);}finally{if(is_file($tmp))unlink($tmp);}
  foreach(glob($dir.'/*.json')?:[] as $old)if(filemtime($old)<time()-86400)unlink($old);
  return ['results'=>$results,'source'=>'Photon / OpenStreetMap'];
 }finally{flock($lock,LOCK_UN);fclose($lock);}
}
