<?php
require_once __DIR__.'/flight-logs-core.php';
function dm_log_schema(PDO $db): void {
 $db->exec('CREATE TABLE IF NOT EXISTS flight_logs(id TEXT PRIMARY KEY,folder TEXT REFERENCES folders(id),fingerprint TEXT NOT NULL,source_hash TEXT NOT NULL,filename TEXT NOT NULL,summary TEXT NOT NULL,track TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,created TEXT NOT NULL); CREATE UNIQUE INDEX IF NOT EXISTS flight_logs_unique ON flight_logs(COALESCE(folder,\'\'),fingerprint); CREATE TABLE IF NOT EXISTS flight_log_links(log TEXT PRIMARY KEY REFERENCES flight_logs(id),mission TEXT NOT NULL REFERENCES missions(id),version TEXT NOT NULL REFERENCES versions(id),planned TEXT NOT NULL,method TEXT NOT NULL)');
}
function dm_log_uploaded(): array {
 $f=$_FILES['file']??null;if(!$f||$f['error']!==UPLOAD_ERR_OK||!is_uploaded_file($f['tmp_name'])||$f['size']>16777216)problem('Eine OpenDroneLog-CSV/JSON-Datei bis 16 MB wählen.');
 $raw=file_get_contents($f['tmp_name']);return [dm_log_parse($raw,$f['name']),$raw,filename($f['name'])];
}
function dm_log_link(string $log,string $mid,string $vid,string $method): void {
 mission($mid,true);$v=stmt('SELECT details FROM versions WHERE id=? AND mission=?',[$vid,$mid])->fetch();if(!$v)problem('KMZ-Version nicht gefunden. Bitte Zuordnung erneut öffnen.',409);$d=json_decode($v['details'],true,512,JSON_THROW_ON_ERROR);if(dm_format($d)!=='kmz')problem('Fluglog einer KMZ-Mission zuordnen.');
 $planned=['durationSeconds'=>$d['estimatedSeconds']??null,'distanceMeters'=>$d['distance']??null,'points'=>$d['count']??null,'camera'=>$d['plannerCamera']??null];
 stmt('INSERT INTO flight_log_links(log,mission,version,planned,method) VALUES(?,?,?,?,?) ON CONFLICT(log) DO UPDATE SET mission=excluded.mission,version=excluded.version,planned=excluded.planned,method=excluded.method',[$log,$mid,$vid,json_encode($planned,JSON_THROW_ON_ERROR),$method]);
}
if(in_array($action,['flight-log-inspect','flight-log-import','flight-logs','flight-log-link','flight-log-track'],true)){
 if($current&&$current['role']!=='edit')problem('Fluglogs sind nicht für Kunden freigegeben.',403);dm_log_schema($db);
 if(in_array($action,['flight-log-inspect','flight-log-import'],true)&&$method==='POST'){
  $folder=($input['folder']??'')?:null;may_folder($folder,true);[$log,$raw,$filename]=dm_log_uploaded();$library=dm_payload($db,$current);$ids=$folder?dm_folder_ids($db,$folder):[null];$missions=array_values(array_filter($library['missions'],fn($m)=>in_array($m['folder'],$ids,true)&&dm_format($m['details'])==='kmz'));
  $candidates=dm_log_candidates($log,$missions);$auto=count($candidates)===1&&$candidates[0]['coverage']>=.95&&$candidates[0]['nameMatch']?$candidates[0]:null;
  if($action==='flight-log-inspect')respond(['summary'=>$log['summary'],'candidates'=>$candidates,'automatic'=>$auto,'missions'=>array_map(fn($m)=>['id'=>$m['id'],'versionId'=>$m['versionId'],'name'=>$m['name']],$missions)]);
  $duplicate=stmt('SELECT id FROM flight_logs WHERE folder IS ? AND fingerprint=?',[$folder,$log['fingerprint']])->fetchColumn();if($duplicate)respond(['id'=>$duplicate,'duplicate'=>true]);
  $mid=(string)($input['mission']??'');$vid=(string)($input['version']??'');$methodName='manual';if($mid==='auto'){if(!$auto)problem('Keine eindeutige automatische Zuordnung. Bitte Mission wählen.');$mid=$auto['id'];$vid=$auto['versionId'];$methodName='automatic';}
  if($mid!==''){mission($mid,true);if(!stmt('SELECT id FROM versions WHERE id=? AND mission=?',[$vid,$mid])->fetch())problem('Missionsversion fehlt.',409);}
  $sha=hash('sha256',$raw);$path=dm_private().'/blobs/'.$sha.'.flightlog';if(!is_file($path)){if(file_put_contents($path,$raw,LOCK_EX)===false)throw new RuntimeException('Fluglog nicht gespeichert.');chmod($path,0600);}
  $id=dm_id();$db->beginTransaction();try{stmt('INSERT INTO flight_logs(id,folder,fingerprint,source_hash,filename,summary,track,created) VALUES(?,?,?,?,?,?,?,?)',[$id,$folder,$log['fingerprint'],$sha,$filename,json_encode($log['summary'],JSON_THROW_ON_ERROR),json_encode($log['track'],JSON_THROW_ON_ERROR),gmdate('c')]);if($mid!=='')dm_log_link($id,$mid,$vid,$methodName);$db->commit();}catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}respond(['id'=>$id,'duplicate'=>false,'assigned'=>$mid!=='']);
 }
 if($action==='flight-logs'&&$method==='GET'){
  $folder=($_GET['folder']??'')?:null;may_folder($folder);$ids=$folder?dm_folder_ids($db,$folder):null;$out=[];
  foreach(stmt('SELECT l.*,k.mission,k.version,k.planned,k.method,m.folder AS mission_folder,m.name AS mission_name FROM flight_logs l LEFT JOIN flight_log_links k ON k.log=l.id LEFT JOIN missions m ON m.id=k.mission ORDER BY l.created DESC')->fetchAll() as $r){if($ids!==null&&!in_array($r['folder'],$ids,true))continue;if($current&&$r['mission']!==null&&!in_array($r['mission_folder'],dm_folder_ids($db,$current['folder']),true))continue;unset($r['track'],$r['source_hash'],$r['fingerprint'],$r['mission_folder']);$r['summary']=json_decode($r['summary'],true);$r['planned']=$r['planned']?json_decode($r['planned'],true):null;$out[]=$r;}respond(['logs'=>$out]);
 }
 $id=(string)($method==='GET'?($_GET['id']??''):($input['id']??''));$row=stmt('SELECT * FROM flight_logs WHERE id=?',[$id])->fetch();if(!$row)problem('Fluglog nicht gefunden.',404);may_folder($row['folder'],$method==='POST');
 if($action==='flight-log-track'&&$method==='GET'){$link=stmt('SELECT mission,version FROM flight_log_links WHERE log=?',[$id])->fetch();$planned=null;if($link){mission($link['mission']);$v=stmt('SELECT details FROM versions WHERE id=?',[$link['version']])->fetch();$planned=$v?json_decode($v['details'],true):null;}respond(['track'=>json_decode($row['track'],true),'planned'=>$planned]);}
 if($action==='flight-log-link'&&$method==='POST'){
  if((int)($input['revision']??0)!==(int)$row['revision'])problem('Zuordnung wurde inzwischen geändert.',409);
  $mid=(string)($input['mission']??'');$vid=(string)($input['version']??'');if($mid!=='')mission($mid,true);
  $db->beginTransaction();try{$updated=stmt('UPDATE flight_logs SET revision=revision+1 WHERE id=? AND revision=?',[$id,(int)$row['revision']]);if(!$updated->rowCount()){$db->rollBack();problem('Zuordnung wurde inzwischen geändert.',409);}if($mid==='')stmt('DELETE FROM flight_log_links WHERE log=?',[$id]);else dm_log_link($id,$mid,$vid,'manual');$db->commit();}catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}respond(['ok'=>true]);
 }
 problem('Methode nicht unterstützt.',405);
}
