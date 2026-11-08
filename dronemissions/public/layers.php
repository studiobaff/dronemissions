<?php
// Eigene Kartenebenen. Nach der Anmeldung geladen; Schreiben nur für den Eigentümer, Lesen für alle Kartennutzer.
if(in_array($action,['layers','layer-save','layer-upload','layer-delete','layer-data','layer-order','layer-project','layer-style','layer-original','wmts-capabilities'],true)){
 if(in_array($action,['layer-data','layer-original'],true)&&$method==='GET'){
  $row=stmt('SELECT * FROM map_layers WHERE id=? AND kind=?',[(string)($_GET['id']??''),'vector'])->fetch();if(!$row)problem('Ebene nicht gefunden.',404);
  $row['config']=json_decode($row['config'],true,32,JSON_THROW_ON_ERROR);if(!dm_layer_visible($db,$row,$current))problem('Kein Zugriff auf diese Projektkarte.',403);
  if($action==='layer-original'){
   owner();$source=$row['config']['source']??null;if(!$source)problem('Für diese ältere Ebene ist keine Originaldatei gespeichert.',404);
   $path=dm_private().'/blobs/'.$source['sha256'].'.reference';if(!is_file($path)||!hash_equals($source['sha256'],hash_file('sha256',$path)))problem('Original fehlt oder ist beschädigt.',500);
   stream_file($path,'application/octet-stream',$source['filename']);
  }
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
 if($action==='layer-style'){
  $id=(string)($input['id']??'');$row=stmt('SELECT * FROM map_layers WHERE id=? AND kind=?',[$id,'vector'])->fetch();if(!$row)problem('Ebene nicht gefunden.',404);
  $c=json_decode($row['config'],true,32,JSON_THROW_ON_ERROR);$style=dm_layer_style($input);$c=array_merge($c,$style);
  stmt('UPDATE map_layers SET config=? WHERE id=?',[json_encode($c,JSON_THROW_ON_ERROR),$id]);respond(['ok'=>true]);
 }
 if($action==='layer-project'){
  $id=(string)($input['id']??'');$row=stmt('SELECT * FROM map_layers WHERE id=? AND kind=?',[$id,'vector'])->fetch();if(!$row)problem('Ebene nicht gefunden.',404);
  $c=json_decode($row['config'],true,32,JSON_THROW_ON_ERROR);$folder=($input['folder']??null)?:null;may_folder($folder,true);$c['folder']=$folder;
  stmt('UPDATE map_layers SET config=? WHERE id=?',[json_encode($c,JSON_THROW_ON_ERROR),$id]);respond(['ok'=>true]);
 }
 if($action==='layer-upload'){
  $existingId=(string)($input['id']??'');$existing=$existingId!==''?stmt('SELECT * FROM map_layers WHERE id=? AND kind=?',[$existingId,'vector'])->fetch():null;if($existingId!==''&&!$existing)problem('Ebene nicht gefunden.',404);
  $folder=($input['folder']??null)?:null;may_folder($folder,true);
  $f=$_FILES['file']??null;if(!$f||$f['error']!==UPLOAD_ERR_OK||!is_uploaded_file($f['tmp_name'])||$f['size']>8388608)problem('GeoJSON-Datei fehlt oder ist größer als 8 MB.');
  $raw=file_get_contents($f['tmp_name']);$geo=json_decode($raw,true,64);if(!is_array($geo)||($geo['type']??'')!=='FeatureCollection'||!is_array($geo['features']??null))problem('Die Datei ist keine GeoJSON-FeatureCollection.');
  if(count($geo['features'])>20000)problem('Maximal 20000 Objekte je Ebene.');
  $clean=['type'=>'FeatureCollection','features'=>[]];$allowed=['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon'];
  foreach($geo['features'] as $feature){if(!is_array($feature)||!is_array($feature['geometry']??null)||!in_array($feature['geometry']['type']??'',$allowed,true)||!isset($feature['geometry']['coordinates']))continue;
   $props=[];foreach((array)($feature['properties']??[]) as $k=>$v){if(count($props)>=40)break;if(is_scalar($v)||$v===null)$props[dm_text((string)$k,60)]=is_string($v)?implode('',array_slice(preg_split('//u',$v,-1,PREG_SPLIT_NO_EMPTY)?:[],0,500)):$v;}
   $geometry=dm_layer_geometry($feature['geometry']);$clean['features'][]=['type'=>'Feature','geometry'=>$geometry,'properties'=>$props];}
  if(!$clean['features'])problem('Keine darstellbaren Objekte (Punkte, Linien, Flächen in WGS84) gefunden.');
  $json=json_encode($clean,JSON_THROW_ON_ERROR);if(strlen($json)>16777216)problem('Ebene ist nach der Bereinigung größer als 16 MB.');
  $hash=hash('sha256',$json);$path=dm_private().'/blobs/'.$hash.'.geojson';if(!is_file($path)&&file_put_contents($path,$json,LOCK_EX)===false)throw new RuntimeException('Ebene nicht gespeichert.');
  $name=dm_text($input['name']??'',60);if($name==='')$name=dm_text(pathinfo($f['name'],PATHINFO_FILENAME),60)?:'Ebene';
  $style=dm_layer_style($input);$color=$style['color'];
  if(!$existing&&(int)stmt('SELECT COUNT(*) FROM map_layers')->fetchColumn()>=30)problem('Maximal 30 eigene Ebenen.');
  $source=null;$sf=$_FILES['source']??null;
  if($sf&&$sf['error']!==UPLOAD_ERR_NO_FILE){
   if($sf['error']!==UPLOAD_ERR_OK||!is_uploaded_file($sf['tmp_name'])||$sf['size']>8388608)problem('Originaldatei fehlt oder ist größer als 8 MB.');
   $original=basename(str_replace('\\','/',$sf['name']));if(!in_array(strtolower(pathinfo($original,PATHINFO_EXTENSION)),['kmz','kml','geojson','json','zip'],true))problem('Originalformat nicht unterstützt.');
   $sh=hash_file('sha256',$sf['tmp_name']);$sp=dm_private().'/blobs/'.$sh.'.reference';if(!is_file($sp)&&!move_uploaded_file($sf['tmp_name'],$sp))throw new RuntimeException('Original nicht gespeichert.');chmod($sp,0600);
   if(!hash_equals($sh,hash_file('sha256',$sp)))throw new RuntimeException('Original-Prüfsumme stimmt nicht.');$source=['filename'=>$original,'sha256'=>$sh,'bytes'=>(int)$sf['size']];
  }
  $config=['folder'=>$folder,'source'=>$source,'color'=>$color,'weight'=>$style['weight'],'useSourceStyle'=>$style['useSourceStyle'],'features'=>count($clean['features']),'attribution'=>dm_text($input['attribution']??'',300)];
  if($existing){
   $old=json_decode($existing['config'],true,32,JSON_THROW_ON_ERROR);if(!$source||!isset($old['source']['sha256'])||!hash_equals($old['source']['sha256'],$source['sha256']))problem('Erneutes Einlesen benötigt dieselbe unveränderte Originaldatei.',409);
   $id=$existing['id'];stmt('UPDATE map_layers SET name=?,config=?,hash=? WHERE id=?',[$name,json_encode($config,JSON_THROW_ON_ERROR),$hash,$id]);
  }else{$id=dm_id();stmt('INSERT INTO map_layers(id,kind,name,config,hash,ordinal,created) VALUES(?,?,?,?,?,?,?)',[$id,'vector',$name,json_encode($config,JSON_THROW_ON_ERROR),$hash,(int)stmt('SELECT COALESCE(MAX(ordinal),0)+1 FROM map_layers')->fetchColumn(),gmdate('c')]);}
  respond(['ok'=>true,'id'=>$id,'features'=>count($clean['features'])]);
 }
 if($action==='layer-order'){
  // Reihenfolge = Position in der Kartenwahl und Stapelung der Overlays (spätere liegen oben).
  $ids=$input['ids']??null;if(!is_array($ids)||!$ids||count($ids)>30||count($ids)!==count(array_unique($ids)))problem('Reihenfolge prüfen.');
  $known=array_column(stmt('SELECT id FROM map_layers')->fetchAll(),'id');if(count($known)!==count($ids)||array_diff($ids,$known))problem('Die Ebenenliste hat sich geändert. Bitte Einstellungen neu öffnen.',409);
  $db->beginTransaction();foreach(array_values($ids) as $i=>$id)stmt('UPDATE map_layers SET ordinal=? WHERE id=?',[$i+1,(string)$id]);$db->commit();respond(['ok'=>true]);
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

// Validate every coordinate before storing client-converted KML/GeoJSON; never trust browser conversion alone.
function dm_layer_geometry(array $g): array {
 $depth=match($g['type']){'Point'=>0,'MultiPoint','LineString'=>1,'MultiLineString','Polygon'=>2,'MultiPolygon'=>3,default=>throw new InvalidArgumentException('Geometrie nicht unterstützt.')};
 $vertices=0;$walk=function($c,int $level)use(&$walk,&$vertices){
  if(!is_array($c)||!array_is_list($c))throw new InvalidArgumentException('Koordinatenformat prüfen.');
  if($level===0){if(count($c)<2||count($c)>3)throw new InvalidArgumentException('Koordinaten benötigen Länge und Breite.');foreach($c as $v)if(!is_numeric($v)||!is_finite((float)$v))throw new InvalidArgumentException('Ungültige Koordinaten.');if(abs((float)$c[0])>180||abs((float)$c[1])>90)throw new InvalidArgumentException('WGS84-Koordinaten in Grad erwartet.');if(++$vertices>100000)throw new InvalidArgumentException('Zu viele Koordinaten.');return array_map('floatval',$c);}
  if(!$c)throw new InvalidArgumentException('Leere Geometrie.');return array_map(fn($v)=>$walk($v,$level-1),$c);
 };
 return ['type'=>$g['type'],'coordinates'=>$walk($g['coordinates'],$depth)];
}

function dm_layer_style(array $input): array {
 $color=dm_text($input['color']??'#2f8f4e',7);if(!preg_match('/^#[0-9a-fA-F]{6}$/',$color))throw new InvalidArgumentException('Farbe als #RRGGBB erwartet.');
 $weight=$input['weight']??1.5;if(!is_numeric($weight)||!is_finite((float)$weight)||(float)$weight<0.5||(float)$weight>32)throw new InvalidArgumentException('Linienbreite zwischen 0,5 und 32 Pixel wählen.');
 $source=$input['useSourceStyle']??true;if(!is_bool($source)&&!in_array($source,['true','false','1','0'],true))throw new InvalidArgumentException('Originalstil prüfen.');
 return ['color'=>strtolower($color),'weight'=>(float)$weight,'useSourceStyle'=>filter_var($source,FILTER_VALIDATE_BOOLEAN)];
}
