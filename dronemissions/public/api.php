<?php
declare(strict_types=1);
require __DIR__.'/lib.php';
header('Cache-Control: no-store');header('X-Content-Type-Options: nosniff');header('Referrer-Policy: no-referrer');header('X-Frame-Options: DENY');
function respond(array $data,int $status=200): never {http_response_code($status);header('Content-Type: application/json; charset=utf-8');echo json_encode($data,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);exit;}
function problem(string $message,int $status=400): never {respond(['error'=>$message],$status);}
function stmt(string $sql,array $args=[]): PDOStatement {global $db;$s=$db->prepare($sql);$s->execute($args);return $s;}
function scope(): ?array {
 if(!empty($_SESSION['owner'])&&($_SESSION['expires']??0)>time())return null;
 if(!empty($_SESSION['share'])){$s=stmt('SELECT * FROM shares WHERE id=? AND expires>?',[$_SESSION['share'],time()])->fetch();if($s)return $s;}
 problem('Bitte anmelden oder eine gültige Projektfreigabe öffnen.',401);
}
function may_folder(?string $id,bool $write=false): void {
 global $db;$s=scope();if($write&&$s&&$s['role']!=='edit')problem('Diese Freigabe erlaubt nur Lesen und Herunterladen.',403);
 if($id!==null&&!stmt('SELECT id FROM folders WHERE id=?',[$id])->fetch())problem('Projektordner nicht gefunden.',404);
 if($s&&($id===null||!in_array($id,dm_folder_ids($db,$s['folder']),true)))problem('Kein Zugriff auf dieses Projekt.',403);
}
function mission(string $id,bool $write=false): array {$m=stmt('SELECT * FROM missions WHERE id=?',[$id])->fetch();if(!$m)problem('Mission nicht gefunden.',404);may_folder($m['folder'],$write);return $m;}
function owner(): void {if(scope()!==null)problem('Nur der Eigentümer kann Freigaben verwalten.',403);}
function filename(string $s): string {$s=preg_replace('/[^\pL\pN._ -]/u','_',$s)??'Mission';return substr($s,0,160)?:'Mission';}
function stream_file(string $path,string $mime,string $name,bool $inline=false): never {header('Content-Type: '.$mime);header('Content-Length: '.filesize($path));header('Content-Disposition: '.($inline?'inline':'attachment').'; filename="download"; filename*=UTF-8\'\''.rawurlencode($name));readfile($path);exit;}
try {
 if(!is_file(dm_private().'/config.json'))problem('Serverinstallation noch nicht eingerichtet.',503);
 $config=json_decode(file_get_contents(dm_private().'/config.json'),true,512,JSON_THROW_ON_ERROR);
 ini_set('session.use_strict_mode','1');ini_set('session.use_only_cookies','1');ini_set('session.gc_maxlifetime','28800');session_name('dm_session');session_save_path(dm_private().'/sessions');
 session_set_cookie_params(['lifetime'=>0,'path'=>'/dronemissions/','secure'=>!empty($_SERVER['HTTPS'])&&$_SERVER['HTTPS']!=='off','httponly'=>true,'samesite'=>'Strict']);session_start();
 if(empty($_SESSION['csrf']))$_SESSION['csrf']=bin2hex(random_bytes(32));
 $db=dm_db();$action=$_GET['action']??'session';$method=$_SERVER['REQUEST_METHOD'];$input=[];
 if($method==='POST'){
  if(!hash_equals($_SESSION['csrf'],$_SERVER['HTTP_X_CSRF_TOKEN']??''))problem('Sitzung abgelaufen. Bitte neu laden.',403);
  if(!empty($_SERVER['HTTP_ORIGIN'])){$expected=(!empty($_SERVER['HTTPS'])&&$_SERVER['HTTPS']!=='off'?'https':'http').'://'.($_SERVER['HTTP_HOST']??'');if($_SERVER['HTTP_ORIGIN']!==$expected)problem('Fremde Anfrage abgelehnt.',403);}
  if(str_starts_with($_SERVER['CONTENT_TYPE']??'','application/json')){$input=json_decode(file_get_contents('php://input'),true,64,JSON_THROW_ON_ERROR);if(!is_array($input))problem('Ungültige Anfrage.');}else{$input=$_POST;}
 }elseif($method!=='GET')problem('Methode nicht unterstützt.',405);
 if($action==='session'&&$method==='GET'){$logged=(!empty($_SESSION['owner'])&&($_SESSION['expires']??0)>time())||(!empty($_SESSION['share'])&&stmt('SELECT id FROM shares WHERE id=? AND expires>?',[$_SESSION['share'],time()])->fetch());respond(['authenticated'=>(bool)$logged,'csrf'=>$_SESSION['csrf'],'version'=>'1.0.0']);}
 if($action==='login'&&$method==='POST'){
  $ip=hash_hmac('sha256',$_SERVER['REMOTE_ADDR']??'unknown',$config['rateSecret']);stmt('DELETE FROM login_attempts WHERE happened<?',[time()-86400]);
  if((int)stmt('SELECT COUNT(*) FROM login_attempts WHERE ip=? AND happened>?',[$ip,time()-900])->fetchColumn()>=10)problem('Zu viele Anmeldeversuche. Bitte in 15 Minuten erneut versuchen.',429);
  stmt('INSERT INTO login_attempts VALUES(?,?)',[$ip,time()]);$p=$input['password']??'';if(!is_string($p)||strlen($p)>1024||!password_verify($p,$config['passwordHash']))problem('Zugangsschlüssel nicht korrekt.',401);
  session_regenerate_id(true);$_SESSION=['owner'=>true,'expires'=>time()+28800,'csrf'=>bin2hex(random_bytes(32))];respond(['ok'=>true,'csrf'=>$_SESSION['csrf']]);
 }
 if($action==='share-login'&&$method==='POST'){$token=$input['token']??'';if(!is_string($token)||strlen($token)>128)problem('Ungültige Freigabe.',403);$s=stmt('SELECT * FROM shares WHERE token_hash=? AND expires>?',[hash('sha256',$token),time()])->fetch();if(!$s)problem('Freigabe ist ungültig, abgelaufen oder widerrufen.',403);session_regenerate_id(true);$_SESSION=['share'=>$s['id'],'csrf'=>bin2hex(random_bytes(32))];respond(['ok'=>true,'csrf'=>$_SESSION['csrf']]);}
 if($action==='logout'&&$method==='POST'){$_SESSION=[];session_destroy();respond(['ok'=>true]);}
 $current=scope();
 if($action==='settings'){
  owner();if($method==='GET')respond(['authorName'=>$config['authorName']??'']);
  $config['authorName']=dm_text($input['authorName']??'',100);$tmp=tempnam(dm_private(),'.config-');
  try{if(file_put_contents($tmp,json_encode($config,JSON_THROW_ON_ERROR),LOCK_EX)===false)throw new RuntimeException('Konfiguration nicht gespeichert.');chmod($tmp,0600);if(!rename($tmp,dm_private().'/config.json'))throw new RuntimeException('Konfiguration nicht gespeichert.');}finally{if(is_file($tmp))unlink($tmp);}
  respond(['ok'=>true]);
 }
 if($action==='library'&&$method==='GET')respond(dm_payload($db,$current));
 if($action==='point'&&$method==='POST'){
  $folder=(string)($input['folder']??'');may_folder($folder,true);$name=dm_text($input['name']??'');$notes=dm_text($input['notes']??'',20000);$lat=dm_num(isset($input['lat'])?(string)$input['lat']:null);$lng=dm_num(isset($input['lng'])?(string)$input['lng']:null);if(!$name||$lat===null||$lng===null||abs($lat)>90||abs($lng)>180)problem('Name und Koordinaten prüfen.');
  $settings=$input['settings']??[];if(!is_array($settings))problem('Ungültige Panorama-Einstellungen.');$height=dm_num(isset($settings['height'])?(string)$settings['height']:null);$heading=dm_num(isset($settings['heading'])?(string)$settings['heading']:null);$gimbal=dm_num(isset($settings['gimbal'])?(string)$settings['gimbal']:null);$mode=$settings['heightMode']??'relativeToStartPoint';$capture=$settings['capture']??'sphere';if($height===null||$height< -500||$height>10000||$heading===null||$heading< -180||$heading>360||$gimbal===null||$gimbal< -90||$gimbal>90||!in_array($mode,['relativeToStartPoint','WGS84'],true)||!in_array($capture,['sphere','wideAngle','photo'],true))problem('Panorama-Einstellungen prüfen.');$encoded=json_encode(['height'=>$height,'heading'=>$heading,'gimbal'=>$gimbal,'heightMode'=>$mode,'capture'=>$capture],JSON_THROW_ON_ERROR);
  $id=$input['id']??null;if($id){$p=stmt('SELECT * FROM points WHERE id=?',[$id])->fetch();if(!$p)problem('Punkt nicht gefunden.',404);may_folder($p['folder'],true);$q=stmt('UPDATE points SET folder=?,name=?,notes=?,lat=?,lng=?,settings=?,revision=revision+1 WHERE id=? AND revision=?',[$folder,$name,$notes,$lat,$lng,$encoded,$id,(int)($input['revision']??0)]);if(!$q->rowCount())problem('Punkt wurde inzwischen geändert.',409);}else{$id=dm_id();stmt('INSERT INTO points(id,folder,name,notes,lat,lng,settings) VALUES(?,?,?,?,?,?,?)',[$id,$folder,$name,$notes,$lat,$lng,$encoded]);}respond(['id'=>$id]);
 }
 if($action==='point-delete'&&$method==='POST'){$p=stmt('SELECT * FROM points WHERE id=?',[(string)($input['id']??'')])->fetch();if(!$p)problem('Punkt nicht gefunden.',404);may_folder($p['folder'],true);$q=stmt('DELETE FROM points WHERE id=? AND revision=?',[$p['id'],(int)($input['revision']??0)]);if(!$q->rowCount())problem('Punkt wurde inzwischen geändert.',409);respond(['ok'=>true]);}
 if($action==='folder'&&$method==='POST'){
  $name=dm_text($input['name']??'');if($name==='')problem('Bitte einen Ordnernamen eingeben.');$parent=($input['parent']??null)?:null;may_folder($parent,true);
  $id=$input['id']??null;if($id){may_folder($id,true);if($parent!==null&&in_array($parent,dm_folder_ids($db,$id),true))problem('Ein Ordner kann nicht in sich selbst verschoben werden.');if($current&&$id===$current['folder'])problem('Der freigegebene Hauptordner kann hier nicht verschoben werden.',403);stmt('UPDATE folders SET name=?,parent=? WHERE id=?',[$name,$parent,$id]);}else{$id=dm_id();stmt('INSERT INTO folders(id,parent,name) VALUES(?,?,?)',[$id,$parent,$name]);}respond(['id'=>$id]);
 }
 if($action==='folder-archive'&&$method==='POST'){$id=(string)($input['id']??'');may_folder($id,true);stmt('UPDATE folders SET archived=? WHERE id=?',[(int)(bool)($input['archived']??false),$id]);respond(['ok'=>true]);}
 if($action==='upload'&&$method==='POST'){
  $folder=($input['folder']??null)?:null;$existing=($input['mission']??null)?:null;$m=$existing?mission($existing,true):null;if($m)$folder=$m['folder'];may_folder($folder,true);
  $file=$_FILES['kmz']??null;if(!$file||$file['error']!==UPLOAD_ERR_OK||!is_uploaded_file($file['tmp_name']))problem('Upload fehlgeschlagen. Maximal 16 MB pro Datei.');
  $original=basename(str_replace('\\','/',$file['name']));$extension=strtolower(pathinfo($original,PATHINFO_EXTENSION));if(!in_array($extension,['kmz','csv'],true))problem('Bitte DJI-KMZ oder Litchi-CSV auswählen.');
  $details=$extension==='csv'?dm_inspect_csv($file['tmp_name']):dm_inspect($file['tmp_name']);$details['sourceFormat']=$extension==='csv'?'litchi-csv':'dji-kmz';$sha=hash_file('sha256',$file['tmp_name']);$blob=dm_private().'/blobs/'.$sha.'.'.$extension;
  if(!is_file($blob)&&!move_uploaded_file($file['tmp_name'],$blob))throw new RuntimeException('Datei konnte nicht gespeichert werden.');chmod($blob,0600);if(!hash_equals($sha,hash_file('sha256',$blob)))throw new RuntimeException('Prüfsumme stimmt nicht.');
  $stem=pathinfo($original,PATHINFO_FILENAME);$details['sourceUUID']=preg_match('/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i',$stem)?strtoupper($stem):null;
  $name=dm_text($input['name']??($details['originalName']?:$stem));if(!$name)problem('Bitte Missionsnamen eingeben.');
  if(isset($_FILES['preview'])&&$_FILES['preview']['error']!==UPLOAD_ERR_NO_FILE){$p=$_FILES['preview'];if($p['error']!==UPLOAD_ERR_OK||$p['size']>3145728)problem('Vorschaubild darf maximal 3 MB groß sein.');$info=getimagesize($p['tmp_name']);if(!$info||!in_array($info['mime'],['image/jpeg','image/png'],true)||$info[0]*$info[1]>16000000)problem('Bitte ein JPEG oder PNG bis 16 Megapixel verwenden.');$raw=file_get_contents($p['tmp_name']);$im=imagecreatefromstring($raw);if(!$im)problem('Vorschaubild kann nicht gelesen werden.');$out=imagescale($im,min(1200,imagesx($im)));ob_start();imagejpeg($out,null,85);$jpg=ob_get_clean();imagedestroy($out);imagedestroy($im);$ph=hash('sha256',$jpg);file_put_contents(dm_private().'/blobs/'.$ph.'.jpg',$jpg,LOCK_EX);chmod(dm_private().'/blobs/'.$ph.'.jpg',0600);$details['previewHash']=$ph;}
  $now=gmdate('c');$id=$existing?:dm_id();$vid=dm_id();$db->beginTransaction();
  if($existing){ $changed=stmt('UPDATE missions SET updated=?,revision=revision+1 WHERE id=? AND revision=?',[$now,$id,(int)($input['revision']??0)]);if(!$changed->rowCount()){$db->rollBack();problem('Mission wurde inzwischen geändert. Bitte neu laden.',409);}$ordinal=(int)stmt('SELECT MAX(ordinal) FROM versions WHERE mission=?',[$id])->fetchColumn()+1;}else{$ordinal=1;stmt('INSERT INTO missions(id,folder,name,created,updated) VALUES(?,?,?,?,?)',[$id,$folder,$name,$now,$now]);}
  stmt('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',[$vid,$id,$ordinal,$original,$sha,filesize($blob),json_encode($details,JSON_THROW_ON_ERROR),$now]);$db->commit();respond(['id'=>$id,'version'=>$ordinal]);
 }
 if($action==='mission'&&$method==='POST'){
  $id=(string)($input['id']??'');$m=mission($id,true);$name=dm_text($input['name']??$m['name']);if(!$name)problem('Bitte Missionsnamen eingeben.');$folder=array_key_exists('folder',$input)?($input['folder']?:null):$m['folder'];may_folder($folder,true);$notes=dm_text($input['notes']??$m['notes'],20000);
  $s=stmt('UPDATE missions SET name=?,notes=?,folder=?,archived=?,updated=?,revision=revision+1 WHERE id=? AND revision=?',[$name,$notes,$folder,(int)(bool)($input['archived']??$m['archived']),gmdate('c'),$id,(int)($input['revision']??0)]);if(!$s->rowCount())problem('Mission wurde inzwischen geändert. Bitte neu laden.',409);respond(['ok'=>true]);
 }
 if($action==='versions'&&$method==='GET'){$id=(string)($_GET['id']??'');mission($id);respond(['versions'=>stmt('SELECT id,ordinal,filename,sha256,bytes,created FROM versions WHERE mission=? ORDER BY ordinal DESC',[$id])->fetchAll()]);}
 if(in_array($action,['original','kmz','preview','package'],true)&&$method==='GET'){
  $m=mission((string)($_GET['id']??''));$vid=$_GET['version']??null;$v=$vid?stmt('SELECT * FROM versions WHERE mission=? AND id=?',[$m['id'],$vid])->fetch():stmt('SELECT * FROM versions WHERE mission=? ORDER BY ordinal DESC LIMIT 1',[$m['id']])->fetch();if(!$v)problem('Version nicht gefunden.',404);
  $details=json_decode($v['details'],true,512,JSON_THROW_ON_ERROR);$extension=dm_format($details);$blob=dm_private().'/blobs/'.$v['sha256'].'.'.$extension;if(!is_file($blob)||!hash_equals($v['sha256'],hash_file('sha256',$blob)))throw new RuntimeException('Archivdatei fehlt oder Prüfsumme ist ungültig.');
  if(in_array($action,['original','kmz'],true))stream_file($blob,$extension==='csv'?'text/csv':'application/vnd.google-earth.kmz',filename($m['name']).'.'.$extension);
  if($action==='preview'){if(isset($details['previewHash']))stream_file(dm_private().'/blobs/'.$details['previewHash'].'.jpg','image/jpeg','preview.jpg',true);header('Content-Type: image/svg+xml');header("Content-Security-Policy: default-src 'none'; sandbox");echo dm_preview($details);exit;}
  $tmp=tempnam(dm_private().'/tmp','export-');try{$z=new ZipArchive();$z->open($tmp,ZipArchive::OVERWRITE);$originalEntry='mission.'.$extension;$z->addFile($blob,$originalEntry);$preview=isset($details['previewHash'])?file_get_contents(dm_private().'/blobs/'.$details['previewHash'].'.jpg'):dm_preview($details);$pname=isset($details['previewHash'])?'preview.jpg':'preview.svg';$z->addFromString($pname,$preview);$metadata=['format'=>'drone-missions/1','author'=>$config['authorName']??'','mission'=>$m,'version'=>array_diff_key($v,['details'=>true]),'details'=>$details,'files'=>[$originalEntry=>$v['sha256'],$pname=>hash('sha256',$preview)]];$z->addFromString('manifest.json',json_encode($metadata,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR));$z->close();header('Content-Type: application/zip');header('Content-Disposition: attachment; filename="mission.zip"; filename*=UTF-8\'\''.rawurlencode(filename($m['name']).'-v'.$v['ordinal'].'.zip'));header('Content-Length: '.filesize($tmp));readfile($tmp);}finally{if(is_file($tmp))unlink($tmp);}exit;
 }
 if($action==='share'&&$method==='POST'){owner();$folder=(string)($input['folder']??'');may_folder($folder);$role=$input['role']??'view';if(!in_array($role,['view','edit'],true))problem('Ungültige Berechtigung.');$token=bin2hex(random_bytes(32));$id=dm_id();$expiry=time()+30*86400;stmt('INSERT INTO shares VALUES(?,?,?,?,?,?)',[$id,$folder,hash('sha256',$token),$role,$expiry,gmdate('c')]);respond(['id'=>$id,'token'=>$token,'expires'=>$expiry]);}
 if($action==='shares'&&$method==='GET'){owner();respond(['shares'=>stmt('SELECT s.id,s.folder,s.role,s.expires,s.created,f.name FROM shares s JOIN folders f ON f.id=s.folder ORDER BY s.created DESC')->fetchAll()]);}
 if($action==='revoke'&&$method==='POST'){owner();stmt('DELETE FROM shares WHERE id=?',[(string)($input['id']??'')]);respond(['ok'=>true]);}
 problem('Nicht gefunden.',404);
}catch(InvalidArgumentException|JsonException $e){if(isset($db)&&$db->inTransaction())$db->rollBack();problem($e->getMessage());}catch(Throwable $e){if(isset($db)&&$db->inTransaction())$db->rollBack();error_log('Drone Missions: '.get_class($e));problem('Anfrage konnte nicht verarbeitet werden.',500);}
