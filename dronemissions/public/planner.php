<?php
require_once __DIR__.'/planner-core.php';
require_once __DIR__.'/planner-terrain.php';
// Device identities are immutable snapshots, not live references to missions.
// profileMission remains the legacy API field name for backward compatibility.
function dm_planner_snapshot(PDO $db,string $id): ?array {
 $q=$db->prepare('SELECT * FROM planner_device_snapshots WHERE id=?');$q->execute([$id]);if($r=$q->fetch())return $r;
 $q=$db->prepare('SELECT m.folder,v.sha256,v.details FROM missions m JOIN versions v ON v.mission=m.id WHERE m.id=? ORDER BY v.ordinal DESC LIMIT 1');$q->execute([$id]);$v=$q->fetch();if(!$v)return null;
 if(dm_format(json_decode($v['details'],true,512,JSON_THROW_ON_ERROR))!=='kmz')return null;
 $path=dm_private().'/blobs/'.$v['sha256'].'.kmz';
 if(!is_file($path)||!hash_equals($v['sha256'],hash_file('sha256',$path)))return null;
 $device=dm_plan_device($path);$json=json_encode($device,JSON_THROW_ON_ERROR);
 $q=$db->prepare('INSERT OR IGNORE INTO planner_device_snapshots(id,folder,device,source_hash,updated) VALUES(?,?,?,?,?)');$q->execute([$id,$v['folder'],$json,$v['sha256'],gmdate('c')]);
 $q=$db->prepare('SELECT * FROM planner_device_snapshots WHERE id=?');$q->execute([$id]);return $q->fetch()?:null;
}
function dm_planner_schema(PDO $db): void {
 $db->exec('CREATE TABLE IF NOT EXISTS mission_plans(id TEXT PRIMARY KEY,folder TEXT REFERENCES folders(id),name TEXT NOT NULL,body TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,created TEXT NOT NULL,updated TEXT NOT NULL); CREATE TABLE IF NOT EXISTS mission_plan_runs(id TEXT PRIMARY KEY,plan TEXT NOT NULL REFERENCES mission_plans(id),missions TEXT NOT NULL,created TEXT NOT NULL); CREATE TABLE IF NOT EXISTS planner_device_snapshots(id TEXT PRIMARY KEY,folder TEXT,device TEXT NOT NULL,source_hash TEXT NOT NULL,updated TEXT NOT NULL); CREATE TABLE IF NOT EXISTS planner_device_profiles(camera TEXT PRIMARY KEY,mission TEXT NOT NULL,updated TEXT NOT NULL)');
 // Upgrade old installations atomically before removing the mission foreign key.
 if($db->query('PRAGMA foreign_key_list(planner_device_profiles)')->fetch()){
  $own=!$db->inTransaction();if($own)$db->beginTransaction();
  try{
   $ids=$db->query('SELECT mission FROM planner_device_profiles')->fetchAll(PDO::FETCH_COLUMN);
   foreach($db->query('SELECT body FROM mission_plans') as $r){$body=json_decode($r['body'],true);if(!empty($body['profileMission']))$ids[]=$body['profileMission'];}
   foreach(array_unique($ids) as $id)if(!dm_planner_snapshot($db,$id))throw new RuntimeException('Bestehendes Drohnenprofil konnte nicht gesichert werden. Referenzdatei prüfen.');
   $db->exec('CREATE TABLE planner_device_profiles_independent(camera TEXT PRIMARY KEY,mission TEXT NOT NULL,updated TEXT NOT NULL); INSERT INTO planner_device_profiles_independent SELECT camera,mission,updated FROM planner_device_profiles; DROP TABLE planner_device_profiles; ALTER TABLE planner_device_profiles_independent RENAME TO planner_device_profiles');
   if($own)$db->commit();
  }catch(Throwable $e){if($own&&$db->inTransaction())$db->rollBack();throw $e;}
 }
}
function dm_planner_body(array $p): array {return array_intersect_key($p,array_flip(['format','generatorVersion','routeSha256','name','type','geometry','cameraId','camera','params','heightReference']));}
function dm_planner_known_profiles(): array {
 global $db,$current;
 $allowed=$current?array_fill_keys(dm_folder_ids($db,$current['folder']),true):null;
 $candidates=[];$explicit=[];$cameraIds=array_column(dm_plan_catalog(),'id');
 $assignments=stmt('SELECT folder,body FROM mission_plans ORDER BY updated DESC')->fetchAll();
 foreach(stmt('SELECT camera,mission FROM planner_device_profiles')->fetchAll() as $r){$v=dm_planner_snapshot($db,$r['mission']);if($v)$assignments[]=['folder'=>$v['folder'],'explicit'=>true,'body'=>json_encode(['cameraId'=>$r['camera'],'profileMission'=>$r['mission']])];}
 foreach($assignments as $row){
  if($allowed!==null&&!isset($allowed[$row['folder']]))continue;
  $body=json_decode($row['body'],true);$camera=$body['cameraId']??'';$id=$body['profileMission']??'';
  if(!$id||!in_array($camera,$cameraIds,true))continue;
  $v=dm_planner_snapshot($db,$id);if(!$v||($allowed!==null&&!isset($allowed[$v['folder']])))continue;
  $device=json_decode($v['device'],true)+['droneSubEnumValue'=>'0','payloadPositionIndex'=>'0'];if(isset($device['payloadEnumValue']))$device+=['payloadSubEnumValue'=>'0'];else unset($device['payloadSubEnumValue']);ksort($device);
  $candidates[$camera][json_encode($device)]=$id;if($row['explicit']??false)$explicit[$camera]=$id;
 }
 $out=[];foreach($candidates as $camera=>$devices)if(count($devices)===1)$out[$camera]=array_values($devices)[0];return array_replace($out,$explicit);
}
function dm_planner_profile(string $id): array {
 global $db,$current;
 if($id==='')problem('Für diese Drohne ist noch kein Exportprofil eingerichtet.');
 $v=dm_planner_snapshot($db,$id);if(!$v)problem('Drohnenprofil nicht verfügbar.',404);may_folder($current?$v['folder']:null);
 return json_decode($v['device'],true,512,JSON_THROW_ON_ERROR)+['sourceHash'=>$v['source_hash']];
}
if(in_array($action,['planner-catalog','planner-list','planner-load','planner-save','planner-preview','planner-export','planner-archive','planner-osm','planner-height-import','planner-export-delete','planner-device-assign'],true)){
 if($current&&$current['role']!=='edit')problem('Der Missionsplaner ist nicht für Kunden freigegeben.',403);
 dm_planner_schema($db);
 if($action==='planner-catalog'&&$method==='GET'){
  $known=dm_planner_known_profiles();$options=[];$allowed=$current?dm_folder_ids($db,$current['folder']):null;
  foreach(stmt('SELECT id,folder,device FROM planner_device_snapshots')->fetchAll() as $r){if($allowed!==null&&!in_array($r['folder'],$allowed,true))continue;$d=json_decode($r['device'],true);$options[]=['id'=>$r['id'],'droneEnum'=>$d['droneEnumValue']];}
  respond(['cameras'=>dm_plan_catalog(),'version'=>2,'deviceProfiles'=>(object)$known,'deviceOptions'=>$options]);
 }
 if($action==='planner-list'&&$method==='GET'){$rows=stmt('SELECT id,folder,name,revision,updated FROM mission_plans ORDER BY updated DESC')->fetchAll();if($current){$ids=dm_folder_ids($db,$current['folder']);$rows=array_values(array_filter($rows,fn($r)=>in_array($r['folder'],$ids,true)));}respond(['plans'=>$rows]);}
 if($action==='planner-load'&&$method==='GET'){$row=stmt('SELECT * FROM mission_plans WHERE id=?',[(string)($_GET['id']??'')])->fetch();if(!$row)problem('Planung nicht gefunden.',404);may_folder($row['folder']);$row['body']=json_decode($row['body'],true,64,JSON_THROW_ON_ERROR);respond($row);}
 if($method!=='POST')problem('Methode nicht unterstützt.',405);
 if($action==='planner-device-assign'){
  if($current)problem('Gerätezuordnungen verwaltet der Eigentümer.',403);
  $camera=(string)($input['cameraId']??'');$id=(string)($input['profileMission']??'');
  if(!in_array($camera,array_column(dm_plan_catalog(),'id'),true))problem('Kameramodell wählen.');
  dm_planner_profile($id);
  stmt('INSERT INTO planner_device_profiles(camera,mission,updated) VALUES(?,?,?) ON CONFLICT(camera) DO UPDATE SET mission=excluded.mission,updated=excluded.updated',[$camera,$id,gmdate('c')]);
  respond(['deviceProfiles'=>(object)dm_planner_known_profiles()]);
 }
 if($action==='planner-export-delete'){
  $id=(string)($input['id']??'');$revision=(int)($input['revision']??0);$exportRevision=(int)($input['exportRevision']??0);
  $expected=$input['missions']??[];if(!is_array($expected)||!array_is_list($expected)||!$expected)problem('Export-Flüge fehlen.');
  $db->beginTransaction();
  $reject=function($message,$code=409)use($db){$db->rollBack();problem($message,$code);};
  try{
   $plan=stmt('SELECT * FROM mission_plans WHERE id=?',[$id])->fetch();if(!$plan)$reject('Planung nicht gefunden.',404);may_folder($plan['folder'],true);
   if((int)$plan['revision']!==$revision)$reject('Planung wurde inzwischen geändert. Bitte neu laden.');
   if($exportRevision<1||$exportRevision>=$revision)$reject('Nur frühere Exporte können hier gelöscht werden.');
   $targets=[];foreach(stmt('SELECT m.id,m.folder,m.revision,v.details FROM missions m JOIN versions v ON v.mission=m.id AND v.ordinal=1')->fetchAll() as $m){$d=json_decode($m['details'],true,512,JSON_THROW_ON_ERROR);if(($d['plannerId']??null)===$id&&(int)($d['plannerRevision']??0)===$exportRevision)$targets[$m['id']]=$m;}
   $seen=[];foreach($expected as $m){if(!is_array($m)||!isset($m['id'],$m['revision'])||isset($seen[$m['id']]))$reject('Export-Auswahl ist ungültig.');$seen[$m['id']]=(int)$m['revision'];}
   if(count($seen)!==count($targets)||!$targets)$reject('Export wurde inzwischen geändert oder gelöscht. Bitte neu laden.');
   foreach($targets as $mid=>$m){may_folder($m['folder'],true);if(($seen[$mid]??null)!==(int)$m['revision'])$reject('Ein Flug wurde inzwischen geändert. Bitte neu laden.');}
   $ids=array_keys($targets);$marks=implode(',',array_fill(0,count($ids),'?'));
   // Device snapshots survive deletion; unrelated flight-log and attachment links still guard deletion.
   if($db->query("SELECT 1 FROM sqlite_master WHERE type='table' AND name='flight_log_links'")->fetchColumn()&&stmt("SELECT 1 FROM flight_log_links WHERE mission IN ($marks) LIMIT 1",$ids)->fetch())$reject('Ein Flug dieses Exports ist mit einem Fluglog verknüpft. Zuerst die Zuordnung lösen.');
   if(stmt("SELECT 1 FROM mission_attachments a JOIN versions v ON v.id=a.version WHERE v.mission IN ($marks) AND a.mission NOT IN ($marks) LIMIT 1",array_merge($ids,$ids))->fetch())$reject('Ein Export wird von einer anderen Mission als Projektdatei verwendet.');
   if(stmt("SELECT 1 FROM mission_previews p JOIN versions v ON v.id=p.source_version WHERE v.mission IN ($marks) AND p.mission NOT IN ($marks) LIMIT 1",array_merge($ids,$ids))->fetch())$reject('Ein Export wird von einer anderen Mission als Vorschauquelle verwendet.');
   $runs=[];foreach(stmt('SELECT id,missions FROM mission_plan_runs WHERE plan=?',[$id])->fetchAll() as $run){$members=json_decode($run['missions'],true,64,JSON_THROW_ON_ERROR);if(array_intersect($members,$ids)){if(array_diff($members,$ids))$reject('Export-Zuordnung ist widersprüchlich.');$runs[]=$run['id'];}}
   stmt("DELETE FROM mission_preview_selection WHERE mission IN ($marks)",$ids);
   stmt("DELETE FROM mission_previews WHERE mission IN ($marks)",$ids);
   stmt("DELETE FROM mission_attachments WHERE mission IN ($marks)",$ids);
   stmt("DELETE FROM versions WHERE mission IN ($marks)",$ids);
   stmt("DELETE FROM missions WHERE id IN ($marks)",$ids);
   foreach($runs as $run)stmt('DELETE FROM mission_plan_runs WHERE id=?',[$run]);
   // Content-addressed blobs can be shared by other missions and snapshots.
   // Do not unlink files here; this action removes only the chosen archive entries.
   $db->commit();respond(['deleted'=>count($ids),'ids'=>$ids]);
  }catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}
 }
 if($action==='planner-height-import'){
  may_folder(($input['folder']??null)?:null,true);
  if(isset($input['mission'])){
   $m=mission((string)$input['mission']);
   $v=stmt('SELECT sha256,details,ordinal FROM versions WHERE mission=? ORDER BY ordinal DESC LIMIT 1',[$m['id']])->fetch();
   if(!$v)problem('Archivmission enthält keine Version.',404);
   if(dm_format(json_decode($v['details'],true,512,JSON_THROW_ON_ERROR))!=='kmz')problem('Höhenreferenz benötigt eine DJI-Waypoint-KMZ.');
   $path=dm_private().'/blobs/'.$v['sha256'].'.kmz';
   if(!is_file($path)||!hash_equals($v['sha256'],hash_file('sha256',$path)))problem('Archivdatei fehlt oder ist beschädigt.',500);
   if(filesize($path)>8388608)problem('KMZ-Höhenreferenz darf höchstens 8 MB groß sein.');
   respond(['heightReference'=>dm_plan_height_import($path,$m['name'].' · V'.$v['ordinal'])]);
  }
  $file=$_FILES['file']??null;
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
    $url='https://api.openstreetmap.org/api/0.6/map?'.http_build_query(['bbox'=>implode(',',[$w,$s,$e,$n])]);$ctx=stream_context_create(['http'=>['timeout'=>15,'follow_location'=>0,'header'=>"User-Agent: ".dm_user_agent('dronemissions-planner/0.1')."\r\n"],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);$stream=@fopen($url,'rb',false,$ctx);if(!$stream)problem('OSM-Dienste derzeit nicht erreichbar. QGIS-Umriss oder Zeichnen verwenden.',502);try{$raw=stream_get_contents($stream,8388609);}finally{fclose($stream);}if($raw===false||strlen($raw)>8388608)problem('OSM-Antwort zu groß; Ausschnitt verkleinern.',502);$data=['elements'=>dm_plan_osm_xml($raw)];$provider='OpenStreetMap API';
   }
   $features=[];foreach($data['elements']??[] as $el){$coords=[];foreach($el['geometry']??[] as $pt)if(isset($pt['lon'],$pt['lat']))$coords[]=[(float)$pt['lon'],(float)$pt['lat']];if(count($coords)<4||$coords[0]!==$coords[count($coords)-1])continue;try{$g=dm_plan_geometry(['type'=>'Polygon','coordinates'=>[$coords]])['geometry'];}catch(InvalidArgumentException $ex){continue;}$features[]=['type'=>'Feature','geometry'=>$g,'properties'=>['name'=>$el['tags']['name']??('OSM-Gebäude '.$el['id']),'source'=>'OpenStreetMap','osmId'=>(string)$el['id']]];}
   $result=['provider'=>$provider,'features'=>$features,'attribution'=>'© OpenStreetMap-Mitwirkende · ODbL','limitations'=>'Nur geschlossene Gebäude-Ways im gewählten Ausschnitt; keine Vollständigkeitsgarantie, keine Multipolygon-Relationen.'];file_put_contents($file,json_encode($result,JSON_THROW_ON_ERROR),LOCK_EX);chmod($file,0600);respond($result);
  }finally{flock($lock,LOCK_UN);fclose($lock);}
 }
 $folder=($input['folder']??null)?:null;may_folder($folder,true);$planInput=$input['plan']??[];if(!is_array($planInput))problem('Planungsdaten prüfen.');$plan=dm_plan_build($planInput,'dm_planner_elevations');$body=dm_planner_body($plan);
 if($action==='planner-preview')respond($plan);
 if($action==='planner-save'){
  $id=(string)($input['id']??'');$now=gmdate('c');$body['profileMission']=(string)($input['profileMission']??'');if($body['profileMission']==='')$body['profileMission']=dm_planner_known_profiles()[$body['cameraId']??'']??'';if($body['profileMission']!=='')dm_planner_profile($body['profileMission']);
  if($id!==''){$row=stmt('SELECT * FROM mission_plans WHERE id=?',[$id])->fetch();if(!$row)problem('Planung nicht gefunden.',404);may_folder($row['folder'],true);$s=stmt('UPDATE mission_plans SET folder=?,name=?,body=?,revision=revision+1,updated=? WHERE id=? AND revision=?',[$folder,$plan['name'],json_encode($body,JSON_THROW_ON_ERROR),$now,$id,(int)($input['revision']??0)]);if(!$s->rowCount())problem('Planung wurde inzwischen geändert. Bitte neu laden.',409);$rev=(int)$row['revision']+1;}
  else{$id=dm_id();$rev=1;stmt('INSERT INTO mission_plans(id,folder,name,body,created,updated) VALUES(?,?,?,?,?,?)',[$id,$folder,$plan['name'],json_encode($body,JSON_THROW_ON_ERROR),$now,$now]);}respond(['id'=>$id,'revision'=>$rev,'routeSha256'=>$plan['routeSha256'],'generatorVersion'=>$plan['generatorVersion']]);
 }
 $profileId=(string)($input['profileMission']??'');if($profileId==='')$profileId=dm_planner_known_profiles()[$body['cameraId']??'']??'';$device=dm_planner_profile($profileId);$files=[];foreach($plan['parts'] as $i=>$part)$files[]=dm_plan_kmz($plan,$part,$device,$i+1);
 if($action==='planner-export'){
  if(count($files)===1){header('Content-Type: application/vnd.google-earth.kmz');header('Content-Disposition: attachment; filename="mission.kmz"; filename*=UTF-8\'\''.rawurlencode(filename($plan['name']).'.kmz'));echo $files[0];exit;}
  $tmp=tempnam(dm_private().'/tmp','plan-export-');try{$z=new ZipArchive();$z->open($tmp,ZipArchive::OVERWRITE);foreach($files as $i=>$raw)$z->addFromString(sprintf('%s-%02d.kmz',filename($plan['name']),$i+1),$raw);$z->addFromString('planung.dmplan.json',json_encode($body,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR));$z->addFromString('HINWEISE.txt',implode("\n",$plan['notes'])."\nGerätekennung aus eigenständigem Drohnenprofil. Diese neu erzeugten Missionen wurden noch nicht auf DJI Fly getestet.");$z->close();stream_file($tmp,'application/zip',filename($plan['name']).'-Abschnitte.zip');}finally{if(is_file($tmp))unlink($tmp);}
 }
 if($action==='planner-archive'){
  $id=(string)($input['id']??'');$row=stmt('SELECT * FROM mission_plans WHERE id=?',[$id])->fetch();if(!$row)problem('Planung zuerst speichern.',409);may_folder($row['folder'],true);$saved=json_decode($row['body'],true,64,JSON_THROW_ON_ERROR);unset($saved['profileMission']);if((int)$row['revision']!==(int)($input['revision']??0)||$row['folder']!==$folder||json_encode($saved)!==json_encode($body))problem('Planung vor dem Archivieren speichern.',409);
  $run=hash('sha256',$id.':'.$row['revision'].':'.$device['sourceHash']);$old=stmt('SELECT missions FROM mission_plan_runs WHERE id=?',[$run])->fetch();if($old)respond(['ids'=>json_decode($old['missions'],true),'existing'=>true]);
  $ids=[];$now=gmdate('c');$db->beginTransaction();try{foreach($files as $i=>$raw){$sha=hash('sha256',$raw);$path=dm_private().'/blobs/'.$sha.'.kmz';if(!is_file($path)&&file_put_contents($path,$raw,LOCK_EX)===false)throw new RuntimeException('KMZ nicht gespeichert.');chmod($path,0600);$details=dm_inspect($path);$details+=['sourceFormat'=>'dji-kmz','plannerId'=>$id,'plannerRevision'=>(int)$row['revision'],'plannerPart'=>$i+1,'plannerParts'=>count($files),'plannerType'=>$body['type'],'plannerCamera'=>$body['cameraId'],'plannerCaptureMode'=>$plan['params']['captureMode'],'plannerGenerator'=>$plan['generatorVersion'],'plannerRouteHash'=>$plan['routeSha256'],'flightValidation'=>'Planer-Export, Geräteprüfung offen'];$mid=dm_id();$vid=dm_id();$name=$plan['name'].(count($files)>1?' · Flug '.($i+1).' von '.count($files):'');stmt('INSERT INTO missions(id,folder,name,notes,created,updated) VALUES(?,?,?,?,?,?)',[$mid,$folder,$name,'Mit Missionsplaner erzeugt. Geräteprüfung offen. Höhen relativ zum Startpunkt.',$now,$now]);stmt('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',[$vid,$mid,1,filename($name).'.kmz',$sha,strlen($raw),json_encode($details,JSON_THROW_ON_ERROR),$now]);stmt('UPDATE missions SET map_capture_type=? WHERE id=?',[$plan['params']['captureMode'],$mid]);if(isset($plan['panorama']))stmt('UPDATE missions SET map_capture_type=?,overview_waypoint=1,overview_version=? WHERE id=?',[$plan['type'],$vid,$mid]);$ids[]=$mid;}stmt('INSERT INTO mission_plan_runs VALUES(?,?,?,?)',[$run,$id,json_encode($ids),$now]);$db->commit();}catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}respond(['ids'=>$ids,'existing'=>false]);
 }
 problem('Methode nicht unterstützt.',405);
}
