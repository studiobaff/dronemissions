<?php
require_once __DIR__.'/planner-core.php';
require_once __DIR__.'/planner-terrain.php';
function dm_planner_schema(PDO $db): void {
 $db->exec('CREATE TABLE IF NOT EXISTS mission_plans(id TEXT PRIMARY KEY,folder TEXT REFERENCES folders(id),name TEXT NOT NULL,body TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,created TEXT NOT NULL,updated TEXT NOT NULL); CREATE TABLE IF NOT EXISTS mission_plan_runs(id TEXT PRIMARY KEY,plan TEXT NOT NULL REFERENCES mission_plans(id),missions TEXT NOT NULL,created TEXT NOT NULL)');
}
function dm_planner_body(array $p): array {return array_intersect_key($p,array_flip(['format','generatorVersion','routeSha256','name','type','geometry','cameraId','camera','params','heightReference']));}
function dm_planner_profile(string $id): array {
 if($id==='')problem('Passende DJI-KMZ als Geräteprofil auswählen.');
 $m=mission($id);$v=stmt('SELECT sha256,details FROM versions WHERE mission=? ORDER BY ordinal DESC LIMIT 1',[$id])->fetch();if(!$v)problem('Profilmission fehlt.',404);$d=json_decode($v['details'],true,512,JSON_THROW_ON_ERROR);if(dm_format($d)!=='kmz')problem('Geräteprofil benötigt eine DJI-KMZ.');$path=dm_private().'/blobs/'.$v['sha256'].'.kmz';if(!is_file($path)||!hash_equals($v['sha256'],hash_file('sha256',$path)))problem('Profilmission beschädigt.',500);return dm_plan_device($path)+['sourceMission'=>$id,'sourceHash'=>$v['sha256']];
}
if(in_array($action,['planner-catalog','planner-list','planner-load','planner-save','planner-preview','planner-export','planner-archive','planner-osm','planner-height-import'],true)){
 if($current&&$current['role']!=='edit')problem('Der Missionsplaner ist nicht für Kunden freigegeben.',403);
 dm_planner_schema($db);
 if($action==='planner-catalog'&&$method==='GET')respond(['cameras'=>dm_plan_catalog(),'version'=>1]);
 if($action==='planner-list'&&$method==='GET'){$rows=stmt('SELECT id,folder,name,revision,updated FROM mission_plans ORDER BY updated DESC')->fetchAll();if($current){$ids=dm_folder_ids($db,$current['folder']);$rows=array_values(array_filter($rows,fn($r)=>in_array($r['folder'],$ids,true)));}respond(['plans'=>$rows]);}
 if($action==='planner-load'&&$method==='GET'){$row=stmt('SELECT * FROM mission_plans WHERE id=?',[(string)($_GET['id']??'')])->fetch();if(!$row)problem('Planung nicht gefunden.',404);may_folder($row['folder']);$row['body']=json_decode($row['body'],true,64,JSON_THROW_ON_ERROR);respond($row);}
 if($method!=='POST')problem('Methode nicht unterstützt.',405);
 if($action==='planner-height-import'){
  may_folder(($input['folder']??null)?:null,true);$file=$_FILES['file']??null;
  if(!$file||$file['error']!==UPLOAD_ERR_OK||!is_uploaded_file($file['tmp_name'])||$file['size']>8388608)problem('KMZ-Höhenreferenz hochladen, maximal 8 MB.');
  $name=basename(str_replace('\\','/',$file['name']));if(strtolower(pathinfo($name,PATHINFO_EXTENSION))!=='kmz')problem('Bitte eine DJI-Waypoint-KMZ wählen.');
  respond(['heightReference'=>dm_plan_height_import($file['tmp_name'],$name)]);
 }
 if($action==='planner-osm'){
  $s=dm_pnum($input,'south',-80,80);$n=dm_pnum($input,'north',$s+.000001,80);$w=dm_pnum($input,'west',-180,180);$e=dm_pnum($input,'east',$w+.000001,180);$area=dm_distance(['lat'=>$s,'lng'=>$w],['lat'=>$n,'lng'=>$w])*dm_distance(['lat'=>$s,'lng'=>$w],['lat'=>$s,'lng'=>$e]);if($area>4000000||$n-$s>.04||$e-$w>.08)problem('Für OSM auf einen kleinen Bereich zoomen (höchstens 4 km²).');
  $key=hash('sha256',json_encode([$s,$w,$n,$e]));$dir=dm_private().'/planner-cache';if(!is_dir($dir))mkdir($dir,0700);$file=$dir.'/'.$key.'.json';
  if(is_file($file)&&filemtime($file)>time()-86400)respond(json_decode(file_get_contents($file),true,64,JSON_THROW_ON_ERROR));
  $rate=$dir.'/osm-rate';$lock=fopen($rate,'c+');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))problem('OSM-Abfrage läuft bereits. Bitte kurz warten.',429);
  try{$last=(float)stream_get_contents($lock);if(microtime(true)-$last<5)problem('OSM-Abfragen bitte mit fünf Sekunden Abstand.',429);ftruncate($lock,0);rewind($lock);fwrite($lock,(string)microtime(true));fflush($lock);
   $q='[out:json][timeout:20];way[building]('.implode(',',[$s,$w,$n,$e]).');out geom 1000;';$ctx=stream_context_create(['http'=>['method'=>'POST','timeout'=>25,'follow_location'=>0,'header'=>"Content-Type: application/x-www-form-urlencoded\r\nUser-Agent: dronemissions-planner/0.1\r\n",'content'=>http_build_query(['data'=>$q])],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);$stream=@fopen('https://overpass-api.de/api/interpreter','rb',false,$ctx);$data=null;$provider='Overpass';
   if($stream){try{$raw=stream_get_contents($stream,8388609);}finally{fclose($stream);}if($raw!==false&&strlen($raw)<=8388608){try{$candidate=json_decode($raw,true,64,JSON_THROW_ON_ERROR);if(empty($candidate['remark'])&&isset($candidate['elements']))$data=$candidate;}catch(JsonException $ignore){}}}
   if($data===null){
    if($area>250000)problem('Overpass derzeit nicht erreichbar. Für die OSM-API auf höchstens 0,25 km² zoomen oder QGIS verwenden.',502);
    $url='https://api.openstreetmap.org/api/0.6/map?'.http_build_query(['bbox'=>implode(',',[$w,$s,$e,$n])]);$ctx=stream_context_create(['http'=>['timeout'=>15,'follow_location'=>0,'header'=>"User-Agent: dronemissions-planner/0.1 (service.studiobaff.com)\r\n"],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);$stream=@fopen($url,'rb',false,$ctx);if(!$stream)problem('OSM-Dienste derzeit nicht erreichbar. QGIS-Umriss oder Zeichnen verwenden.',502);try{$raw=stream_get_contents($stream,8388609);}finally{fclose($stream);}if($raw===false||strlen($raw)>8388608)problem('OSM-Antwort zu groß; Ausschnitt verkleinern.',502);$data=['elements'=>dm_plan_osm_xml($raw)];$provider='OpenStreetMap API';
   }
   $features=[];foreach($data['elements']??[] as $el){$coords=[];foreach($el['geometry']??[] as $pt)if(isset($pt['lon'],$pt['lat']))$coords[]=[(float)$pt['lon'],(float)$pt['lat']];if(count($coords)<4||$coords[0]!==$coords[count($coords)-1])continue;try{$g=dm_plan_geometry(['type'=>'Polygon','coordinates'=>[$coords]])['geometry'];}catch(InvalidArgumentException $ex){continue;}$features[]=['type'=>'Feature','geometry'=>$g,'properties'=>['name'=>$el['tags']['name']??('OSM-Gebäude '.$el['id']),'source'=>'OpenStreetMap','osmId'=>(string)$el['id']]];}
   $result=['provider'=>$provider,'features'=>$features,'attribution'=>'© OpenStreetMap-Mitwirkende · ODbL','limitations'=>'Nur geschlossene Gebäude-Ways im gewählten Ausschnitt; keine Vollständigkeitsgarantie, keine Multipolygon-Relationen.'];file_put_contents($file,json_encode($result,JSON_THROW_ON_ERROR),LOCK_EX);chmod($file,0600);respond($result);
  }finally{flock($lock,LOCK_UN);fclose($lock);}
 }
 $folder=($input['folder']??null)?:null;may_folder($folder,true);$planInput=$input['plan']??[];if(!is_array($planInput))problem('Planungsdaten prüfen.');$plan=dm_plan_build($planInput,'dm_planner_elevations');$body=dm_planner_body($plan);
 if($action==='planner-preview')respond($plan);
 if($action==='planner-save'){
  $id=(string)($input['id']??'');$now=gmdate('c');$body['profileMission']=(string)($input['profileMission']??'');if($body['profileMission']!=='')dm_planner_profile($body['profileMission']);
  if($id!==''){$row=stmt('SELECT * FROM mission_plans WHERE id=?',[$id])->fetch();if(!$row)problem('Planung nicht gefunden.',404);may_folder($row['folder'],true);$s=stmt('UPDATE mission_plans SET folder=?,name=?,body=?,revision=revision+1,updated=? WHERE id=? AND revision=?',[$folder,$plan['name'],json_encode($body,JSON_THROW_ON_ERROR),$now,$id,(int)($input['revision']??0)]);if(!$s->rowCount())problem('Planung wurde inzwischen geändert. Bitte neu laden.',409);$rev=(int)$row['revision']+1;}
  else{$id=dm_id();$rev=1;stmt('INSERT INTO mission_plans(id,folder,name,body,created,updated) VALUES(?,?,?,?,?,?)',[$id,$folder,$plan['name'],json_encode($body,JSON_THROW_ON_ERROR),$now,$now]);}respond(['id'=>$id,'revision'=>$rev,'routeSha256'=>$plan['routeSha256'],'generatorVersion'=>$plan['generatorVersion']]);
 }
 $device=dm_planner_profile((string)($input['profileMission']??''));$files=[];foreach($plan['parts'] as $i=>$part)$files[]=dm_plan_kmz($plan,$part,$device,$i+1);
 if($action==='planner-export'){
  if(count($files)===1){header('Content-Type: application/vnd.google-earth.kmz');header('Content-Disposition: attachment; filename="mission.kmz"; filename*=UTF-8\'\''.rawurlencode(filename($plan['name']).'.kmz'));echo $files[0];exit;}
  $tmp=tempnam(dm_private().'/tmp','plan-export-');try{$z=new ZipArchive();$z->open($tmp,ZipArchive::OVERWRITE);foreach($files as $i=>$raw)$z->addFromString(sprintf('%s-%02d.kmz',filename($plan['name']),$i+1),$raw);$z->addFromString('planung.dmplan.json',json_encode($body,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR));$z->addFromString('HINWEISE.txt',implode("\n",$plan['notes'])."\nGerätekennung aus Referenzmission. Diese neu erzeugten Missionen wurden noch nicht auf DJI Fly getestet.");$z->close();stream_file($tmp,'application/zip',filename($plan['name']).'-Abschnitte.zip');}finally{if(is_file($tmp))unlink($tmp);}
 }
 if($action==='planner-archive'){
  $id=(string)($input['id']??'');$row=stmt('SELECT * FROM mission_plans WHERE id=?',[$id])->fetch();if(!$row)problem('Planung zuerst speichern.',409);may_folder($row['folder'],true);$saved=json_decode($row['body'],true,64,JSON_THROW_ON_ERROR);unset($saved['profileMission']);if((int)$row['revision']!==(int)($input['revision']??0)||$row['folder']!==$folder||json_encode($saved)!==json_encode($body))problem('Planung vor dem Archivieren speichern.',409);
  $run=hash('sha256',$id.':'.$row['revision'].':'.$device['sourceHash']);$old=stmt('SELECT missions FROM mission_plan_runs WHERE id=?',[$run])->fetch();if($old)respond(['ids'=>json_decode($old['missions'],true),'existing'=>true]);
  $ids=[];$now=gmdate('c');$db->beginTransaction();try{foreach($files as $i=>$raw){$sha=hash('sha256',$raw);$path=dm_private().'/blobs/'.$sha.'.kmz';if(!is_file($path)&&file_put_contents($path,$raw,LOCK_EX)===false)throw new RuntimeException('KMZ nicht gespeichert.');chmod($path,0600);$details=dm_inspect($path);$details+=['sourceFormat'=>'dji-kmz','plannerId'=>$id,'plannerRevision'=>(int)$row['revision'],'plannerPart'=>$i+1,'plannerParts'=>count($files),'plannerCamera'=>$body['cameraId'],'plannerCaptureMode'=>$plan['params']['captureMode'],'plannerGenerator'=>$plan['generatorVersion'],'plannerRouteHash'=>$plan['routeSha256'],'flightValidation'=>'Planer-Export, Geräteprüfung offen'];$mid=dm_id();$vid=dm_id();$name=$plan['name'].(count($files)>1?' · '.($i+1).'/'.count($files):'');stmt('INSERT INTO missions(id,folder,name,notes,created,updated) VALUES(?,?,?,?,?,?)',[$mid,$folder,$name,'Mit Missionsplaner erzeugt. Geräteprüfung offen. Höhen relativ zum Startpunkt.',$now,$now]);stmt('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',[$vid,$mid,1,filename($name).'.kmz',$sha,strlen($raw),json_encode($details,JSON_THROW_ON_ERROR),$now]);$ids[]=$mid;}stmt('INSERT INTO mission_plan_runs VALUES(?,?,?,?)',[$run,$id,json_encode($ids),$now]);$db->commit();}catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}respond(['ids'=>$ids,'existing'=>false]);
 }
 problem('Methode nicht unterstützt.',405);
}
