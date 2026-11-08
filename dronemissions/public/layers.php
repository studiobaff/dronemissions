<?php
// Eigene Kartenebenen. Nach der Anmeldung geladen; Schreiben nur für den Eigentümer, Lesen für alle Kartennutzer.
if(in_array($action,['layers','layer-save','layer-upload','layer-delete','layer-data','wmts-capabilities'],true)){
 if($action==='layer-data'&&$method==='GET'){
  $row=stmt('SELECT * FROM map_layers WHERE id=? AND kind=?',[(string)($_GET['id']??''),'vector'])->fetch();if(!$row)problem('Ebene nicht gefunden.',404);
  $path=dm_private().'/blobs/'.$row['hash'].'.geojson';if(!is_file($path)||!hash_equals($row['hash'],hash_file('sha256',$path)))problem('Ebene fehlt oder ist beschädigt.',500);
  stream_file($path,'application/geo+json','ebene.geojson',true);
 }
 owner();
 if($action==='layers'&&$method==='GET'){
  $rows=dm_layers($db);foreach($rows as &$r){if($r['kind']==='tile'&&!empty($r['config']['key']))$r['config']['keyHint']=substr($r['config']['key'],0,4).'…';unset($r['config']['key']);}unset($r);respond(['layers'=>$rows]);
 }
 if($method!=='POST')problem('Methode nicht unterstützt.',405);
 if($action==='layer-save'){
  $url=dm_text($input['url']??'',600);if(!preg_match('#^https://[^\s"\'<>]+$#',$url)||!str_contains($url,'{z}')||!str_contains($url,'{x}')||!(str_contains($url,'{y}')||str_contains($url,'{-y}')))problem('Kachel-URL prüfen: https und die Platzhalter {z}, {x}, {y} (oder {-y}) sind nötig.');
  $host=parse_url(str_replace(['{s}','{z}','{x}','{y}','{-y}','{key}'],['a','0','0','0','0','k'],$url),PHP_URL_HOST);if(!$host||str_contains($host,'{'))problem('Kachel-URL prüfen: Hostname nicht erkannt.');
  $maxZoom=(int)($input['maxZoom']??19);if($maxZoom<1||$maxZoom>22)problem('Maximaler Zoom zwischen 1 und 22.');
  $opacity=(float)($input['opacity']??1);if($opacity<0.1||$opacity>1)problem('Deckkraft zwischen 0,1 und 1.');
  $id=(string)($input['id']??'');$existing=$id!==''?stmt('SELECT * FROM map_layers WHERE id=? AND kind=?',[$id,'tile'])->fetch():null;if($id!==''&&!$existing)problem('Ebene nicht gefunden.',404);
  $key=$input['key']??null;if($key===null||$key==='')$key=$existing?(json_decode($existing['config'],true)['key']??''):'';$key=dm_text((string)$key,400);
  if(str_contains($url,'{key}')&&$key==='')problem('Die URL enthält {key}, es wurde aber kein API-Schlüssel eingegeben.');
  $config=['url'=>$url,'attribution'=>dm_text($input['attribution']??'',300),'key'=>$key,'maxZoom'=>$maxZoom,'overlay'=>!empty($input['overlay']),'opacity'=>$opacity];
  $name=dm_text($input['name']??'',60);if($name==='')problem('Bitte einen Namen für die Ebene eingeben.');
  if(!$existing&&(int)stmt('SELECT COUNT(*) FROM map_layers')->fetchColumn()>=30)problem('Maximal 30 eigene Ebenen.');
  if($existing)stmt('UPDATE map_layers SET name=?,config=? WHERE id=?',[$name,json_encode($config,JSON_THROW_ON_ERROR),$id]);
  else{$id=dm_id();stmt('INSERT INTO map_layers(id,kind,name,config,hash,ordinal,created) VALUES(?,?,?,?,NULL,?,?)',[$id,'tile',$name,json_encode($config,JSON_THROW_ON_ERROR),(int)stmt('SELECT COALESCE(MAX(ordinal),0)+1 FROM map_layers')->fetchColumn(),gmdate('c')]);}
  respond(['ok'=>true,'id'=>$id]);
 }
 if($action==='layer-upload'){
  $f=$_FILES['file']??null;if(!$f||$f['error']!==UPLOAD_ERR_OK||!is_uploaded_file($f['tmp_name'])||$f['size']>8388608)problem('GeoJSON-Datei fehlt oder ist größer als 8 MB.');
  $raw=file_get_contents($f['tmp_name']);$geo=json_decode($raw,true,64);if(!is_array($geo)||($geo['type']??'')!=='FeatureCollection'||!is_array($geo['features']??null))problem('Die Datei ist keine GeoJSON-FeatureCollection.');
  if(count($geo['features'])>20000)problem('Maximal 20000 Objekte je Ebene.');
  $clean=['type'=>'FeatureCollection','features'=>[]];$allowed=['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon'];
  foreach($geo['features'] as $feature){if(!is_array($feature)||!is_array($feature['geometry']??null)||!in_array($feature['geometry']['type']??'',$allowed,true)||!isset($feature['geometry']['coordinates']))continue;
   $props=[];foreach((array)($feature['properties']??[]) as $k=>$v){if(count($props)>=40)break;if(is_scalar($v)||$v===null)$props[dm_text((string)$k,60)]=is_string($v)?mb_substr($v,0,500):$v;}
   $clean['features'][]=['type'=>'Feature','geometry'=>['type'=>$feature['geometry']['type'],'coordinates'=>$feature['geometry']['coordinates']],'properties'=>$props];}
  if(!$clean['features'])problem('Keine darstellbaren Objekte (Punkte, Linien, Flächen in WGS84) gefunden.');
  $json=json_encode($clean,JSON_THROW_ON_ERROR);if(strlen($json)>16777216)problem('Ebene ist nach der Bereinigung größer als 16 MB.');
  $hash=hash('sha256',$json);$path=dm_private().'/blobs/'.$hash.'.geojson';if(!is_file($path)&&file_put_contents($path,$json,LOCK_EX)===false)throw new RuntimeException('Ebene nicht gespeichert.');
  $name=dm_text($input['name']??'',60);if($name==='')$name=dm_text(pathinfo($f['name'],PATHINFO_FILENAME),60)?:'Ebene';
  $color=dm_text($input['color']??'#2f8f4e',9);if(!preg_match('/^#[0-9a-fA-F]{6}$/',$color))$color='#2f8f4e';
  if((int)stmt('SELECT COUNT(*) FROM map_layers')->fetchColumn()>=30)problem('Maximal 30 eigene Ebenen.');
  $id=dm_id();stmt('INSERT INTO map_layers(id,kind,name,config,hash,ordinal,created) VALUES(?,?,?,?,?,?,?)',[$id,'vector',$name,json_encode(['color'=>$color,'features'=>count($clean['features']),'attribution'=>dm_text($input['attribution']??'',300)],JSON_THROW_ON_ERROR),$hash,(int)stmt('SELECT COALESCE(MAX(ordinal),0)+1 FROM map_layers')->fetchColumn(),gmdate('c')]);
  respond(['ok'=>true,'id'=>$id,'features'=>count($clean['features'])]);
 }
 if($action==='layer-delete'){
  $row=stmt('SELECT * FROM map_layers WHERE id=?',[(string)($input['id']??'')])->fetch();if(!$row)problem('Ebene nicht gefunden.',404);
  stmt('DELETE FROM map_layers WHERE id=?',[$row['id']]);
  if($row['hash']&&!stmt('SELECT id FROM map_layers WHERE hash=?',[$row['hash']])->fetch()){$path=dm_private().'/blobs/'.$row['hash'].'.geojson';if(is_file($path))unlink($path);}
  respond(['ok'=>true]);
 }
 if($action==='wmts-capabilities'){
  $url=dm_text($input['url']??'',600);$parts=parse_url($url);$host=strtolower((string)($parts['host']??''));$dev=getenv('DRONEMISSIONS_DEV')&&in_array($host,['127.0.0.1','localhost'],true);
  if(!$host||!in_array($parts['scheme']??'',$dev?['http','https']:['https'],true))problem('Bitte eine https-Adresse des WMTS-Dienstes (GetCapabilities) eingeben.');
  if(!$dev){$ip=gethostbyname($host);if($ip===$host||filter_var($ip,FILTER_VALIDATE_IP,FILTER_FLAG_NO_PRIV_RANGE|FILTER_FLAG_NO_RES_RANGE)===false)problem('Dienst nicht erreichbar oder keine öffentliche Adresse.');}
  if(!str_contains(strtolower($url),'getcapabilities')&&!str_contains(strtolower($url),'wmtscapabilities')){$url.=(str_contains($url,'?')?'&':'?').'SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0';}
  $context=stream_context_create(['http'=>['timeout'=>12,'follow_location'=>0,'header'=>"User-Agent: DroneMissions/1.0\r\n"],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);
  $stream=@fopen($url,'rb',false,$context);if(!$stream)problem('WMTS-Dienst nicht erreichbar.',502);
  try{$xml=stream_get_contents($stream,4194305);}finally{fclose($stream);}
  if($xml===false||strlen($xml)>4194304)problem('Capabilities-Dokument zu groß (max. 4 MB).');
  respond(['layers'=>dm_wmts_layers($xml,$url)]);
 }
 problem('Methode nicht unterstützt.',405);
}
/* WMTS-Capabilities in XYZ-Vorlagen übersetzen: nur Web-Mercator-Matrixsets (Google-Kacheln), RESTful ResourceURL bevorzugt, sonst KVP-GetTile. */
function dm_wmts_layers(string $xml,string $capabilitiesUrl): array {
 $doc=dm_xml($xml);$ns=['ows'=>'http://www.opengis.net/ows/1.1','wmts'=>'http://www.opengis.net/wmts/1.0','xlink'=>'http://www.w3.org/1999/xlink'];
 $sets=[];foreach($doc->xpath('//*[local-name()="Contents"]/*[local-name()="TileMatrixSet"]') as $set){
  $id=(string)($set->xpath('./*[local-name()="Identifier"]')[0]??'');$crs=(string)($set->xpath('./*[local-name()="SupportedCRS"]')[0]??'');$matrices=array_map(fn($m)=>(string)$m,$set->xpath('./*[local-name()="TileMatrix"]/*[local-name()="Identifier"]'));
  $mercator=preg_match('/3857|900913|googlemapscompatible|webmercator|google3857/i',$id.' '.$crs)===1;$prefix='';
  if($matrices){$first=$matrices[0];if(!ctype_digit($first)&&preg_match('/^(.*?)(\d+)$/',$first,$m))$prefix=$m[1];}
  $sets[$id]=['mercator'=>$mercator,'prefix'=>$prefix,'maxZoom'=>$matrices?max(array_map(fn($m)=>(int)preg_replace('/^\D*/','',$m),$matrices)):19];
 }
 $kvp=null;foreach($doc->xpath('//*[local-name()="OperationsMetadata"]/*[local-name()="Operation"][@name="GetTile"]//*[local-name()="Get"]') as $get){$href=(string)($get->attributes($ns['xlink'])['href']??'');if($href!==''){$kvp=$href;break;}}
 $out=[];
 foreach($doc->xpath('//*[local-name()="Contents"]/*[local-name()="Layer"]') as $layer){
  $id=(string)($layer->xpath('./*[local-name()="Identifier"]')[0]??'');$title=(string)($layer->xpath('./*[local-name()="Title"]')[0]??$id);
  $styles=$layer->xpath('./*[local-name()="Style"]');$style='default';foreach($styles as $st){$sid=(string)($st->xpath('./*[local-name()="Identifier"]')[0]??'');if($sid!==''&&($style==='default'||(string)($st['isDefault']??'')==='true'))$style=$sid;}
  $formats=array_map(fn($f)=>(string)$f,$layer->xpath('./*[local-name()="Format"]'));$format=$formats[0]??'image/png';
  $links=array_map(fn($l)=>(string)$l,$layer->xpath('./*[local-name()="TileMatrixSetLink"]/*[local-name()="TileMatrixSet"]'));
  $dims=[];foreach($layer->xpath('./*[local-name()="Dimension"]') as $d){$dims[(string)($d->xpath('./*[local-name()="Identifier"]')[0]??'')]=(string)($d->xpath('./*[local-name()="Default"]')[0]??'');}
  foreach($links as $setId){$set=$sets[$setId]??null;if(!$set||!$set['mercator'])continue;$z=$set['prefix'].'{z}';$template=null;
   foreach($layer->xpath('./*[local-name()="ResourceURL"][@resourceType="tile"]') as $r){$t=(string)$r['template'];if($t!==''){$template=$t;break;}}
   if($template){$url=str_replace(['{Style}','{style}','{TileMatrixSet}','{TileMatrix}','{TileRow}','{TileCol}'],[$style,$style,$setId,$z,'{y}','{x}'],$template);foreach($dims as $k=>$v)$url=str_replace('{'.$k.'}',$v,$url);}
   elseif($kvp){$url=$kvp.(str_contains($kvp,'?')?'':'?').'SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER='.rawurlencode($id).'&STYLE='.rawurlencode($style).'&TILEMATRIXSET='.rawurlencode($setId).'&TILEMATRIX='.$z.'&TILEROW={y}&TILECOL={x}&FORMAT='.rawurlencode($format);foreach($dims as $k=>$v)$url.='&'.rawurlencode($k).'='.rawurlencode($v);}
   else continue;
   if(preg_match('/\{[A-Za-z]+\}/',str_replace(['{z}','{x}','{y}','{s}'],'',$url)))continue; // offene Platzhalter ohne Standardwert
   $out[]=['id'=>$id,'title'=>$title,'matrixSet'=>$setId,'format'=>$format,'url'=>$url,'maxZoom'=>min(22,max(1,$set['maxZoom']))];
  }
 }
 if(!$out)problem('Keine Ebene mit Web-Mercator-Kacheln (EPSG:3857) im Dienst gefunden.');
 return $out;
}
