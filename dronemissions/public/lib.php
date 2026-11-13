<?php
declare(strict_types=1);
const MAX_KMZ = 16777216;
/* Privater Ordner (SQLite, Blobs, config.json): über DRONEMISSIONS_PRIVATE setzen; die Vorgabe ist bewusst neutral und gehört nicht zum Betreiber. */
/* User-Agent für externe Dienste (OSM, Höhendaten): nennt den Host der jeweiligen Installation, keinen festen Betreiber. */
function dm_user_agent(string $component): string { return $component.' ('.preg_replace('/[^A-Za-z0-9.:-]/','',$_SERVER['HTTP_HOST']??'localhost').')'; }
function dm_private(): string { return getenv('DRONEMISSIONS_PRIVATE') ?: dirname(__DIR__).'/private'; }
/* Kartenstart aus config.json (Einstellungen → Kartenstart); ohne Eintrag Österreich-Mitte. Wird an alle Rollen geliefert, enthält keine Missionsdaten. */
function dm_map_start(): array { $file=dm_private().'/config.json'; $config=is_file($file)?json_decode((string)file_get_contents($file),true):null; $m=is_array($config)?($config['mapStart']??null):null; if(is_array($m)&&is_numeric($m['lat']??null)&&is_numeric($m['lng']??null)&&abs((float)$m['lat'])<=85&&abs((float)$m['lng'])<=180){$zoom=(int)($m['zoom']??13);return ['lat'=>round((float)$m['lat'],5),'lng'=>round((float)$m['lng'],5),'zoom'=>max(3,min(19,$zoom))];} return ['lat'=>47.6,'lng'=>14.1,'zoom'=>7]; }
function dm_db(): PDO {
 $dir=dm_private(); if(!is_dir($dir))throw new RuntimeException('Installation nicht eingerichtet.');
 $db=new PDO('sqlite:'.$dir.'/missions.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
 $db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;'); dm_migrate($db); return $db;
}
function dm_migrate(PDO $db): void {
 // Ergänzt Spalten und Tabellen, die seit 1.0 hinzugekommen sind, ohne bestehende Daten anzufassen. Neue Installationen laufen über dm_schema().
 if(!$db->query("SELECT name FROM sqlite_master WHERE type='table' AND name='missions'")->fetch())return;
 $columns=array_column($db->query('PRAGMA table_info(missions)')->fetchAll(),'name');
 foreach(['map_sort'=>'INTEGER','overview_waypoint'=>'INTEGER','overview_version'=>'TEXT','litchi_url'=>'TEXT NOT NULL DEFAULT ""','takeoff_lat'=>'REAL','takeoff_lng'=>'REAL','map_capture_type'=>"TEXT NOT NULL DEFAULT 'photo'"] as $column=>$type)if(!in_array($column,$columns,true))$db->exec("ALTER TABLE missions ADD COLUMN $column $type");
 $shareColumns=array_column($db->query('PRAGMA table_info(shares)')->fetchAll(),'name');if(!in_array('presentation',$shareColumns,true))$db->exec("ALTER TABLE shares ADD COLUMN presentation TEXT NOT NULL DEFAULT 'library'");
 dm_preview_schema($db);dm_layer_schema($db);
 $db->exec('CREATE TABLE IF NOT EXISTS mission_attachments(mission TEXT NOT NULL REFERENCES missions(id),version TEXT NOT NULL REFERENCES versions(id),PRIMARY KEY(mission,version))');
}
function dm_schema(PDO $db): void {
 dm_preview_schema($db);dm_layer_schema($db);
 $db->exec('CREATE TABLE IF NOT EXISTS mission_attachments(mission TEXT NOT NULL REFERENCES missions(id),version TEXT NOT NULL REFERENCES versions(id),PRIMARY KEY(mission,version)); CREATE TABLE IF NOT EXISTS points(id TEXT PRIMARY KEY,folder TEXT NOT NULL REFERENCES folders(id),name TEXT NOT NULL,notes TEXT NOT NULL DEFAULT "",lat REAL NOT NULL,lng REAL NOT NULL,settings TEXT NOT NULL DEFAULT "{}",revision INTEGER NOT NULL DEFAULT 1); CREATE TABLE IF NOT EXISTS folders(id TEXT PRIMARY KEY,parent TEXT REFERENCES folders(id),name TEXT NOT NULL,archived INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS missions(id TEXT PRIMARY KEY,folder TEXT REFERENCES folders(id),name TEXT NOT NULL,notes TEXT NOT NULL DEFAULT "",archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,map_sort INTEGER,overview_waypoint INTEGER,overview_version TEXT,litchi_url TEXT NOT NULL DEFAULT "",takeoff_lat REAL,takeoff_lng REAL,map_capture_type TEXT NOT NULL DEFAULT "photo"); CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY,mission TEXT NOT NULL REFERENCES missions(id),ordinal INTEGER NOT NULL,filename TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,details TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(mission,ordinal)); CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY,folder TEXT NOT NULL REFERENCES folders(id),token_hash TEXT NOT NULL UNIQUE,role TEXT NOT NULL,expires INTEGER NOT NULL,created TEXT NOT NULL,presentation TEXT NOT NULL DEFAULT "library"); CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT NOT NULL,happened INTEGER NOT NULL);');
}
/* Eigene Kartenebenen: Kachel-Ebenen (XYZ/WMTS mit optionalem API-Schlüssel) und Vektor-Ebenen (GeoJSON-Datei im Blob-Speicher). */
function dm_layer_schema(PDO $db): void {
 $db->exec('CREATE TABLE IF NOT EXISTS map_layers(id TEXT PRIMARY KEY,kind TEXT NOT NULL,name TEXT NOT NULL,config TEXT NOT NULL,hash TEXT,ordinal INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL)');
}
function dm_layers(PDO $db): array {
 $rows=$db->query('SELECT * FROM map_layers ORDER BY ordinal,created,id')->fetchAll();foreach($rows as &$r)$r['config']=json_decode($r['config'],true,32,JSON_THROW_ON_ERROR);unset($r);return $rows;
}
function dm_layer_url(array $config): string {
 // Der Schlüssel wird in die Kachel-URL eingesetzt; Kacheln lädt der Browser, daher sehen alle Kartennutzer den Schlüssel (bei Mapbox per URL-Beschränkung absichern).
 return str_replace('{key}',rawurlencode((string)($config['key']??'')),(string)$config['url']);
}
function dm_layer_visible(PDO $db,array $layer,?array $scope): bool {
 $folder=$layer['config']['folder']??null;
 if($folder===null)return true; // Existing global reference layers retain their established visibility.
 if($scope===null)return true;
 return $scope['role']==='edit'&&in_array($folder,dm_folder_ids($db,$scope['folder']),true);
}
function dm_layers_public(PDO $db,?array $scope=null): array {
 $out=[];foreach(dm_layers($db) as $l){if(!dm_layer_visible($db,$l,$scope))continue;$c=$l['config'];
  if($l['kind']==='tile')$out[]=['id'=>$l['id'],'kind'=>'tile','name'=>$l['name'],'url'=>dm_layer_url($c),'attribution'=>$c['attribution']??'','maxZoom'=>$c['maxZoom']??19,'overlay'=>!empty($c['overlay']),'opacity'=>$c['opacity']??1];
  else $out[]=['id'=>$l['id'],'kind'=>'vector','folder'=>$c['folder']??null,'name'=>$l['name'],'color'=>$c['color']??'#2f8f4e','weight'=>$c['weight']??1.5,'useSourceStyle'=>$c['useSourceStyle']??true,'features'=>$c['features']??0,'attribution'=>$c['attribution']??''];
 }return $out;
}
function dm_layer_hosts(PDO $db): array {
 $hosts=[];foreach(dm_layers($db) as $l)if($l['kind']==='tile'){$url=$l['config']['url'];$h=parse_url(str_replace(['{s}','{z}','{x}','{y}','{-y}','{key}'],['sub','0','0','0','0','k'],$url),PHP_URL_HOST);if($h)$hosts['https://'.(str_contains($url,'{s}.')?preg_replace('/^sub\./','*.',$h):$h)]=true;}
 return array_keys($hosts);
}
function dm_id(): string { return bin2hex(random_bytes(16)); }
function dm_text(mixed $v,int $limit=200): string { if(!is_string($v))throw new InvalidArgumentException('Text erwartet.'); $v=trim($v);if(strlen($v)>$limit||preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F]/',$v))throw new InvalidArgumentException('Text zu lang oder ungültig.');return $v; }
function dm_xml(string $text): SimpleXMLElement {
 if(strlen($text)>8388608||preg_match('/<!\s*(DOCTYPE|ENTITY)/i',$text))throw new InvalidArgumentException('XML enthält unzulässige Definitionen.');
 $old=libxml_use_internal_errors(true);try{$xml=simplexml_load_string($text,SimpleXMLElement::class,LIBXML_NONET|LIBXML_NOBLANKS);if($xml===false)throw new InvalidArgumentException('Ungültiges XML in der KMZ-Datei.');return $xml;}finally{libxml_clear_errors();libxml_use_internal_errors($old);}
}
function dm_value(SimpleXMLElement $el,string $tag,?string $default=null): ?string { $a=$el->xpath('.//*[local-name()="'.$tag.'"]');return $a?trim((string)$a[0]):$default; }
function dm_num(?string $v,?float $default=null): ?float {if($v===null||$v===''||!is_numeric($v))return $default;$n=(float)$v;return is_finite($n)?$n:$default;}
function dm_distance(array $a,array $b): float { $p1=deg2rad($a['lat']);$p2=deg2rad($b['lat']);$dp=$p2-$p1;$dl=deg2rad($b['lng']-$a['lng']);$h=sin($dp/2)**2+cos($p1)*cos($p2)*sin($dl/2)**2;return 6371000*2*asin(min(1,sqrt($h))); }
function dm_inspect(string $path): array {
 if(!is_file($path)||filesize($path)>MAX_KMZ)throw new InvalidArgumentException('KMZ fehlt oder ist größer als 16 MB.');
 $zip=new ZipArchive();if($zip->open($path)!==true)throw new InvalidArgumentException('Keine gültige KMZ-/ZIP-Datei.');
 try {
  if($zip->numFiles>1000)throw new InvalidArgumentException('Zu viele Dateien im KMZ.');
  $total=0; for($i=0;$i<$zip->numFiles;$i++){$s=$zip->statIndex($i);$total+=$s['size'];if($total>67108864)throw new InvalidArgumentException('Entpackte KMZ ist zu groß.');if(str_contains($s['name'],'..')||str_starts_with($s['name'],'/'))throw new InvalidArgumentException('Ungültiger Dateipfad im KMZ.');}
  $templateText=$zip->getFromName('wpmz/template.kml');$waylineText=$zip->getFromName('wpmz/waylines.wpml');
  if($templateText===false||$waylineText===false)throw new InvalidArgumentException('DJI-WPML-Dateien wpmz/template.kml und wpmz/waylines.wpml fehlen.');
  $template=dm_xml($templateText);$route=dm_xml($waylineText);$points=[];$routeFolders=[];
  foreach($route->xpath('//*[local-name()="Folder"]') as $folder){
   $folderId=dm_value($folder,'waylineId','');$base=count($points);$globalSpeed=dm_num(dm_value($folder,'autoFlightSpeed'));
   foreach($folder->xpath('./*[local-name()="Placemark"]') as $p){
    $coords=dm_value($p,'coordinates');if($coords===null)continue;$c=explode(',',trim($coords));$lng=dm_num($c[0]??null);$lat=dm_num($c[1]??null);
    if($lat===null||$lng===null||abs($lat)>90||abs($lng)>180)throw new InvalidArgumentException('Ungültige Wegpunktkoordinaten.');
    $points[]=['lat'=>$lat,'lng'=>$lng,'height'=>dm_num(dm_value($p,'executeHeight')),'speed'=>dm_num(dm_value($p,'waypointSpeed'),$globalSpeed),'index'=>dm_value($p,'index',(string)(count($points)-$base)),'wayline'=>$folderId];
    if(count($points)>20000)throw new InvalidArgumentException('Zu viele Wegpunkte.');
   }
   if(count($points)>$base)$routeFolders[]=['id'=>$folderId,'start'=>$base,'count'=>count($points)-$base,'heightMode'=>dm_value($folder,'executeHeightMode','unbekannt')];
  }
  if(!$points)throw new InvalidArgumentException('Keine ausführbaren Wegpunkte im KMZ gefunden.');
  $distance=0;$duration=0;foreach($routeFolders as $f){for($i=$f['start']+1;$i<$f['start']+$f['count'];$i++){$d=dm_distance($points[$i-1],$points[$i]);$distance+=$d;$speed=$points[$i]['speed'];if($speed!==null&&$speed>0)$duration+=$d/$speed;}}
  return ['pois'=>dm_wpml_pois($route),'points'=>$points,'routes'=>$routeFolders,'count'=>count($points),'distance'=>round($distance,1),'estimatedSeconds'=>round($duration),'droneEnum'=>dm_value($template,'droneEnumValue'),'droneSubEnum'=>dm_value($template,'droneSubEnumValue'),'author'=>dm_value($template,'author',''),'heightMode'=>count($routeFolders)===1?$routeFolders[0]['heightMode']:'mehrere Flugrouten','originalName'=>dm_value($template,'name',''),'flightValidation'=>'nicht auf DJI Fly getestet'];
 }finally{$zip->close();}
}
function dm_preview(array $details): string {
 $points=$details['points'];$label=($details['sourceFormat']??'')==='mapcreator-project'?'Map-Creator-Projekt':'Litchi Original';if(!$points)return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="300" viewBox="0 0 480 300"><rect width="480" height="300" fill="#152e2b"/><text x="240" y="140" text-anchor="middle" font-family="sans-serif" font-size="26" fill="#b5d969">'.$label.'</text><text x="240" y="178" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#b1c6bc">Route noch nicht ausgelesen</text></svg>';$fit=array_merge($points,$details['pois']??[]);$lats=array_column($fit,'lat');$lngs=array_column($fit,'lng');$mid=array_sum($lats)/count($lats);$scale=max(.05,cos(deg2rad($mid)));$xs=array_map(fn($x)=>$x*$scale,$lngs);$minx=min($xs);$maxx=max($xs);$miny=min($lats);$maxy=max($lats);$span=max($maxx-$minx,($maxy-$miny)*1.6,.00001);$paths='';
 foreach($details['routes'] as $route){$pts=[];for($i=$route['start'];$i<$route['start']+$route['count'];$i++)$pts[]=sprintf('%.2f,%.2f',30+($xs[$i]-($minx+$maxx)/2)/$span*420+210,150-($lats[$i]-($miny+$maxy)/2)/$span*420);$paths.='<polyline points="'.implode(' ',$pts).'" fill="none" stroke="#87d8ba" stroke-width="3" stroke-linejoin="round"/>';}
 foreach($details['pois']??[] as $poi){$x=240+($poi['lng']*$scale-($minx+$maxx)/2)/$span*420;$y=150-($poi['lat']-($miny+$maxy)/2)/$span*420;$paths.='<g transform="translate('.$x.','.$y.')"><path d="M0 -6L6 0L0 6L-6 0Z" fill="#b45ee3" stroke="white"/><text x="9" y="4" font-family="sans-serif" font-size="12" fill="white">'.htmlspecialchars($poi['label'],ENT_XML1|ENT_QUOTES,'UTF-8').'</text></g>';}
 return '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="300" viewBox="0 0 480 300"><rect width="480" height="300" fill="#152e2b"/><path d="M0 75H480M0 150H480M0 225H480M120 0V300M240 0V300M360 0V300" stroke="#25423d"/>'.$paths.'</svg>';
}
function dm_folder_ids(PDO $db,string $root): array {
 $s=$db->prepare('WITH RECURSIVE tree(id) AS (SELECT id FROM folders WHERE id=? UNION SELECT f.id FROM folders f JOIN tree t ON f.parent=t.id) SELECT id FROM tree');$s->execute([$root]);return $s->fetchAll(PDO::FETCH_COLUMN);
}
function dm_payload(PDO $db,?array $scope): array {
 $folders=$db->query('SELECT * FROM folders ORDER BY name COLLATE NOCASE')->fetchAll();$allowed=$scope?dm_folder_ids($db,$scope['folder']):null;
 foreach($folders as &$f){$q=$db->prepare('WITH RECURSIVE ancestors(id,parent,archived) AS (SELECT id,parent,archived FROM folders WHERE id=? UNION SELECT f.id,f.parent,f.archived FROM folders f JOIN ancestors a ON f.id=a.parent) SELECT MAX(archived) FROM ancestors');$q->execute([$f['parent']]);$f['inheritedArchived']=(bool)$q->fetchColumn();}unset($f);
 if($allowed!==null)$folders=array_values(array_filter($folders,fn($f)=>in_array($f['id'],$allowed,true)));
 $missions=$db->query('SELECT m.*,v.id AS versionId,v.ordinal AS version,v.filename,v.sha256,v.bytes,v.details FROM missions m JOIN versions v ON v.mission=m.id AND v.ordinal=(SELECT MAX(ordinal) FROM versions WHERE mission=m.id) ORDER BY m.updated DESC')->fetchAll();
 if($allowed!==null)$missions=array_values(array_filter($missions,fn($m)=>in_array($m['folder'],$allowed,true)));
 foreach($missions as &$m){$m['details']=json_decode($m['details'],true,512,JSON_THROW_ON_ERROR);$m['archived']=(bool)$m['archived'];$m['captureType']=$m['map_capture_type']??'photo';$m['mapOrder']=$m['map_sort']===null?null:(int)$m['map_sort'];$m['overviewPoint']=dm_overview_point($m);$m['takeoffPoint']=$m['takeoff_lat']!==null&&$m['takeoff_lng']!==null?['lat'=>(float)$m['takeoff_lat'],'lng'=>(float)$m['takeoff_lng']]:null;$m['panoPoint']=isset($m['details']['points'][1])?array_intersect_key($m['details']['points'][1],['lat'=>true,'lng'=>true]):null;if($m['takeoffPoint']!==null||($scope['presentation']??'')==='map')$m['overviewPoint']=$m['panoPoint'];}unset($m);
 foreach($missions as &$m){$q=$db->prepare('SELECT v.id,v.filename,v.sha256,v.bytes,v.details FROM mission_attachments a JOIN versions v ON v.id=a.version WHERE a.mission=? ORDER BY v.created');$q->execute([$m['id']]);$m['attachments']=[];foreach($q->fetchAll() as $file){$file['format']=dm_format(json_decode($file['details'],true,512,JSON_THROW_ON_ERROR));unset($file['details']);$m['attachments'][]=$file;}}unset($m);
 $points=$db->query('SELECT * FROM points ORDER BY name')->fetchAll();foreach($points as &$point)$point['settings']=json_decode($point['settings'],true,32,JSON_THROW_ON_ERROR);unset($point);if($allowed!==null)$points=array_values(array_filter($points,fn($p)=>in_array($p['folder'],$allowed,true)));
 if($scope&&$scope['role']==='view'){
  $hidden=[];foreach($folders as $f)if($f['archived']||$f['inheritedArchived'])$hidden[$f['id']]=true;
  $missions=array_values(array_filter($missions,fn($m)=>!$m['archived']&&!isset($hidden[$m['folder']])&&($m['overviewPoint']!==null||$m['takeoffPoint']!==null)));
  foreach($missions as &$m){$point=$m['overviewPoint'];$m=['id'=>$m['id'],'folder'=>$m['folder'],'name'=>$m['name'],'updated'=>$m['updated'],'archived'=>false,'overviewPoint'=>$point,'captureType'=>$m['captureType'],'mapOrder'=>$m['mapOrder'],'panoPoint'=>($m['takeoffPoint']!==null||($scope['presentation']??'')==='map'||(int)($m['overview_waypoint']??-1)===1)?$point:null,'takeoffPoint'=>$m['takeoffPoint'],'overview_waypoint'=>$m['overview_waypoint'],'notes'=>'','filename'=>'','versionId'=>$m['versionId'],'version'=>$m['version'],'details'=>['points'=>$point?[['lat'=>$point['lat'],'lng'=>$point['lng'],'height'=>null]]:[],'routes'=>[],'count'=>$point?1:0,'distance'=>0,'previewAvailable'=>true,'heightMode'=>'Standort']];}unset($m);
  $points=array_values(array_filter($points,fn($p)=>!isset($hidden[$p['folder']])));foreach($points as &$p){$p['notes']='';$p['settings']=[];}unset($p);
  if(($scope['presentation']??'')==='map')$points=[];
  $folders=array_values(array_filter($folders,fn($f)=>!isset($hidden[$f['id']])));
 }
 return ['folders'=>$folders,'missions'=>$missions,'points'=>$points,'role'=>$scope?($scope['role']==='edit'?'editor':'viewer'):'owner','scope'=>$scope['folder']??null,'presentation'=>$scope['presentation']??'library','layers'=>dm_layers_public($db,$scope),'mapStart'=>dm_map_start()];
}

function dm_format(array $details): string { return match($details['sourceFormat']??'dji-kmz'){'litchi-csv'=>'csv','litchi-lchm'=>'lchm','litchi-lchz'=>'lchz','mapcreator-project'=>'mproj',default=>'kmz'}; }
function dm_inspect_csv(string $path): array {
 if(!is_file($path)||filesize($path)>MAX_KMZ)throw new InvalidArgumentException('CSV fehlt oder ist größer als 16 MB.');
 $h=fopen($path,'rb');if(!$h)throw new RuntimeException('CSV kann nicht gelesen werden.');
 try{
  $line=fgets($h,65538);if($line===false||strlen($line)>65536)throw new InvalidArgumentException('CSV-Kopfzeile fehlt oder ist zu lang.');
  $header=str_getcsv(preg_replace('/^\xEF\xBB\xBF/','',$line),',','"','');if(count($header)>256)throw new InvalidArgumentException('Zu viele CSV-Spalten.');
  $header=array_map(fn($v)=>strtolower(trim($v)),$header);if(count(array_unique($header))!==count($header))throw new InvalidArgumentException('Doppelte CSV-Spalten.');$cols=array_flip($header);
  foreach(['latitude','longitude','altitude(m)','heading(deg)'] as $key)if(!isset($cols[$key]))throw new InvalidArgumentException('Keine Litchi-Missions-CSV: Spalte '.$key.' fehlt.');
  $points=[];$modes=[];$distance=0;$duration=0;
  while(($row=fgetcsv($h,65538,',','"',''))!==false){
   if($row===[null])continue;if(count($row)>256||count($row)>count($header))throw new InvalidArgumentException('Ungültige CSV-Spaltenzahl.');
   $value=fn($key)=>isset($cols[$key])?($row[$cols[$key]]??null):null;
   $lat=dm_num($value('latitude'));$lng=dm_num($value('longitude'));$height=dm_num($value('altitude(m)'));$heading=dm_num($value('heading(deg)'));
   if($lat===null||$lng===null||abs($lat)>90||abs($lng)>180||$height===null||$heading===null)throw new InvalidArgumentException('Ungültige Koordinaten, Höhe oder Blickrichtung in CSV-Zeile '.(count($points)+2).'.');
   $speed=dm_num($value('speed(m/s)'));$points[]=['lat'=>$lat,'lng'=>$lng,'height'=>$height,'speed'=>$speed,'index'=>(string)count($points),'wayline'=>'0'];
   if(count($points)>20000)throw new InvalidArgumentException('Zu viele CSV-Wegpunkte.');
   $mode=$value('altitudemode');if($mode!==null&&strlen($mode)<20)$modes[$mode]=true;
   if(count($points)>1){$d=dm_distance($points[count($points)-2],$points[count($points)-1]);$distance+=$d;if($speed!==null&&$speed>0)$duration+=$d/$speed;}
  }
  if(!$points)throw new InvalidArgumentException('Keine Wegpunkte in der Litchi-CSV.');
  $heightMode='Litchi-CSV: Höhenbezug nicht verifiziert';
  return ['sourceFormat'=>'litchi-csv','points'=>$points,'routes'=>[['id'=>'0','start'=>0,'count'=>count($points),'heightMode'=>$heightMode]],'count'=>count($points),'distance'=>round($distance,1),'estimatedSeconds'=>round($duration),'droneEnum'=>null,'droneSubEnum'=>null,'author'=>'','heightMode'=>$heightMode,'originalName'=>'','csvAltitudeModes'=>array_keys($modes),'flightValidation'=>'nicht auf DJI Fly getestet'];
 }finally{fclose($h);}
}

function dm_inspect_native(string $path,string $extension): array {
 if(!in_array($extension,['lchm','lchz'],true)||!is_file($path)||filesize($path)>MAX_KMZ||filesize($path)<8)throw new InvalidArgumentException('Ungültige native Litchi-Datei.');
 $h=fopen($path,'rb');try{$magic=fread($h,4);}finally{fclose($h);}
 if($magic!==$extension)throw new InvalidArgumentException('Litchi-Dateisignatur passt nicht zur Dateiendung.');
 if($extension==='lchz'){
  $z=new ZipArchive();$zipPath=null;if($z->open($path)!==true){$zipPath=tempnam(sys_get_temp_dir(),'dm-litchi-');$in=fopen($path,'rb');$out=fopen($zipPath,'wb');try{fseek($in,8);stream_copy_to_stream($in,$out);}finally{fclose($in);fclose($out);}if($z->open($zipPath)!==true){unlink($zipPath);throw new InvalidArgumentException('Ungültiges Litchi-Archiv.');}}
  try{$total=0;if($z->numFiles>1000)throw new InvalidArgumentException('Zu viele Dateien im Litchi-Archiv.');for($i=0;$i<$z->numFiles;$i++){$entry=$z->statIndex($i);$total+=$entry['size'];if($total>67108864||str_contains($entry['name'],'..')||str_starts_with($entry['name'],'/'))throw new InvalidArgumentException('Unzulässiges Litchi-Archiv.');}$flight=$z->getFromName('flight.lch2',8);if($flight===false||!str_starts_with($flight,'lch2'))throw new InvalidArgumentException('Litchi-Flugdatei fehlt im Archiv.');}finally{$z->close();if($zipPath!==null)unlink($zipPath);}
 }
 return ['sourceFormat'=>'litchi-'.$extension,'previewAvailable'=>false,'points'=>[],'routes'=>[],'count'=>null,'distance'=>0,'estimatedSeconds'=>null,'droneEnum'=>null,'droneSubEnum'=>null,'author'=>'','heightMode'=>'Native Litchi-Daten noch nicht ausgelesen','originalName'=>'','flightValidation'=>'Original archiviert; keine Konvertierung oder Flugprüfung'];
}

function dm_overview_point(array $m): ?array {
 $index=$m['overview_waypoint']??null;if($index===null||($m['overview_version']??null)!==$m['versionId'])return null;
 $p=$m['details']['points'][(int)$index]??null;return $p?['lat'=>$p['lat'],'lng'=>$p['lng']]:null;
}
function dm_inspect_mproj(string $path): array {
 if(filesize($path)>1048576)throw new InvalidArgumentException('Map-Creator-Projekt ist größer als 1 MB.');
 $d=json_decode(file_get_contents($path),true,32,JSON_THROW_ON_ERROR);
 if(!is_array($d)||($d['version']??null)!==1||!in_array($d['type']??null,['circle','polygon'],true)||!is_array($d['polygon']??null)||!is_array($d['settings']??null))throw new InvalidArgumentException('Unbekanntes Map-Creator-Projektformat.');
 foreach($d['polygon'] as $p)if(!is_array($p)||count($p)!==2||!is_numeric($p[0])||!is_numeric($p[1])||!is_finite((float)$p[0])||!is_finite((float)$p[1]))throw new InvalidArgumentException('Ungültige Planungsgeometrie.');
 return ['sourceFormat'=>'mapcreator-project','previewAvailable'=>false,'points'=>[],'routes'=>[],'count'=>null,'distance'=>0,'estimatedSeconds'=>null,'droneEnum'=>null,'droneSubEnum'=>null,'author'=>'','heightMode'=>'Map-Creator-Projekt – kein Flugexport','originalName'=>'','planningType'=>$d['type'],'planningVertexCount'=>count($d['polygon']),'flightValidation'=>'Originalprojekt archiviert. Für die Übertragung auf DJI Fly einen DJI-KMZ-Export zuordnen.'];
}

function dm_preview_schema(PDO $db): void {
 $db->exec('CREATE TABLE IF NOT EXISTS mission_previews(id TEXT PRIMARY KEY,mission TEXT NOT NULL REFERENCES missions(id),source_version TEXT NOT NULL REFERENCES versions(id),hash TEXT NOT NULL,photo_hash TEXT,settings TEXT NOT NULL,created TEXT NOT NULL); CREATE TABLE IF NOT EXISTS mission_preview_selection(mission TEXT PRIMARY KEY REFERENCES missions(id),preview TEXT NOT NULL REFERENCES mission_previews(id)); CREATE INDEX IF NOT EXISTS mission_previews_mission ON mission_previews(mission)');
}
function dm_active_preview(PDO $db,string $mission): ?array {
 $s=$db->prepare('SELECT p.* FROM mission_previews p JOIN mission_preview_selection s ON s.preview=p.id WHERE s.mission=? AND p.mission=?');$s->execute([$mission,$mission]);return $s->fetch()?:null;
}

// WPML POI coordinates are latitude,longitude,altitude (unlike KML).
// Only towardPOI is active; placeholder values of other heading modes are ignored.
function dm_wpml_pois(SimpleXMLElement $route): array {
 $pois=[];$index=0;
 foreach($route->xpath('//*[local-name()="Folder"]/*[local-name()="Placemark"]') as $p){
  if(dm_value($p,'coordinates')===null)continue;
  if(dm_value($p,'waypointHeadingMode')==='towardPOI'){
   $c=explode(',',dm_value($p,'waypointPoiPoint',''));
   if(count($c)===3){[$lat,$lng,$alt]=array_map(fn($v)=>dm_num(trim($v)),$c);
    if($lat!==null&&$lng!==null&&$alt!==null&&abs($lat)<=90&&abs($lng)<=180){
     $key=json_encode([$lat,$lng,$alt],JSON_THROW_ON_ERROR);
     if(!isset($pois[$key])){$src=dm_value($p,'waypointHeadingPoiIndex','');$pois[$key]=['lat'=>$lat,'lng'=>$lng,'altitude'=>$alt,'sourceIndex'=>ctype_digit($src)?(int)$src:null,'waypoints'=>[]];}
     $pois[$key]['waypoints'][]=$index;
    }
   }
  }$index++;
 }
 $used=[];foreach($pois as &$poi){$n=$poi['sourceIndex']!==null?$poi['sourceIndex']+1:1;while(isset($used[$n]))$n++;$used[$n]=true;$poi['id']=$n;$poi['label']='POI '.$n;}unset($poi);return array_values($pois);
}
