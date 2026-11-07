<?php
declare(strict_types=1);
const MAX_KMZ = 16777216;
function dm_private(): string { return getenv('DRONEMISSIONS_PRIVATE') ?: '/usr/local/www/vhosts/studiobaff/dronemissions-private'; }
function dm_db(): PDO {
 $dir=dm_private(); if(!is_dir($dir))throw new RuntimeException('Installation nicht eingerichtet.');
 $db=new PDO('sqlite:'.$dir.'/missions.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC]);
 $db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;'); return $db;
}
function dm_schema(PDO $db): void {
 $db->exec('CREATE TABLE IF NOT EXISTS points(id TEXT PRIMARY KEY,folder TEXT NOT NULL REFERENCES folders(id),name TEXT NOT NULL,notes TEXT NOT NULL DEFAULT "",lat REAL NOT NULL,lng REAL NOT NULL,settings TEXT NOT NULL DEFAULT "{}",revision INTEGER NOT NULL DEFAULT 1); CREATE TABLE IF NOT EXISTS folders(id TEXT PRIMARY KEY,parent TEXT REFERENCES folders(id),name TEXT NOT NULL,archived INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS missions(id TEXT PRIMARY KEY,folder TEXT REFERENCES folders(id),name TEXT NOT NULL,notes TEXT NOT NULL DEFAULT "",archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1); CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY,mission TEXT NOT NULL REFERENCES missions(id),ordinal INTEGER NOT NULL,filename TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,details TEXT NOT NULL,created TEXT NOT NULL,UNIQUE(mission,ordinal)); CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY,folder TEXT NOT NULL REFERENCES folders(id),token_hash TEXT NOT NULL UNIQUE,role TEXT NOT NULL,expires INTEGER NOT NULL,created TEXT NOT NULL); CREATE TABLE IF NOT EXISTS login_attempts(ip TEXT NOT NULL,happened INTEGER NOT NULL);');
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
  return ['points'=>$points,'routes'=>$routeFolders,'count'=>count($points),'distance'=>round($distance,1),'estimatedSeconds'=>round($duration),'droneEnum'=>dm_value($template,'droneEnumValue'),'droneSubEnum'=>dm_value($template,'droneSubEnumValue'),'author'=>dm_value($template,'author',''),'heightMode'=>count($routeFolders)===1?$routeFolders[0]['heightMode']:'mehrere Flugrouten','originalName'=>dm_value($template,'name',''),'flightValidation'=>'nicht auf DJI Fly getestet'];
 }finally{$zip->close();}
}
function dm_preview(array $details): string {
 $points=$details['points'];$lats=array_column($points,'lat');$lngs=array_column($points,'lng');$mid=array_sum($lats)/count($lats);$scale=max(.05,cos(deg2rad($mid)));$xs=array_map(fn($x)=>$x*$scale,$lngs);$minx=min($xs);$maxx=max($xs);$miny=min($lats);$maxy=max($lats);$span=max($maxx-$minx,($maxy-$miny)*1.6,.00001);$paths='';
 foreach($details['routes'] as $route){$pts=[];for($i=$route['start'];$i<$route['start']+$route['count'];$i++)$pts[]=sprintf('%.2f,%.2f',30+($xs[$i]-($minx+$maxx)/2)/$span*420+210,150-($lats[$i]-($miny+$maxy)/2)/$span*420);$paths.='<polyline points="'.implode(' ',$pts).'" fill="none" stroke="#87d8ba" stroke-width="3" stroke-linejoin="round"/>';}
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
 foreach($missions as &$m){$m['details']=json_decode($m['details'],true,512,JSON_THROW_ON_ERROR);$m['archived']=(bool)$m['archived'];}unset($m);
 $points=$db->query('SELECT * FROM points ORDER BY name')->fetchAll();foreach($points as &$point)$point['settings']=json_decode($point['settings'],true,32,JSON_THROW_ON_ERROR);unset($point);if($allowed!==null)$points=array_values(array_filter($points,fn($p)=>in_array($p['folder'],$allowed,true)));
 return ['folders'=>$folders,'missions'=>$missions,'points'=>$points,'role'=>$scope?($scope['role']==='edit'?'editor':'viewer'):'owner','scope'=>$scope['folder']??null];
}

function dm_format(array $details): string { return ($details['sourceFormat']??'dji-kmz')==='litchi-csv'?'csv':'kmz'; }
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
