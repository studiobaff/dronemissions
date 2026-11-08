<?php
// Loaded after authentication. Viewer links never expose private pictures or routes.
if(in_array($action,['previews','preview-save','preview-select','preview-image'],true)){
 if($current&&$current['role']==='view')problem('Vorschaubilder sind nicht für Kunden freigegeben.',403);
 $id=(string)($method==='GET'?($_GET['id']??''):($input['id']??''));$pm=mission($id,$method==='POST');
 if($action==='previews'&&$method==='GET'){
  $rows=stmt('SELECT id,source_version,settings,created FROM mission_previews WHERE mission=? ORDER BY created DESC,id DESC',[$id])->fetchAll();foreach($rows as &$row)$row['settings']=json_decode($row['settings'],true,64,JSON_THROW_ON_ERROR);unset($row);
  $active=dm_active_preview($db,$id);respond(['images'=>$rows,'active'=>$active['id']??null,'revision'=>(int)$pm['revision']]);
 }
 if($action==='preview-image'&&$method==='GET'){
  $row=stmt('SELECT * FROM mission_previews WHERE id=? AND mission=?',[(string)($_GET['image']??''),$id])->fetch();if(!$row)problem('Bild nicht gefunden.',404);
  $hash=isset($_GET['source'])?$row['photo_hash']:$row['hash'];if(!$hash)problem('Kein eigenes Ausgangsbild vorhanden.',404);$path=dm_private().'/blobs/'.$hash.'.jpg';if(!is_file($path)||!hash_equals($hash,hash_file('sha256',$path)))problem('Bild fehlt oder ist beschädigt.',500);stream_file($path,'image/jpeg','preview.jpg',true);
 }
 if(in_array($action,['preview-save','preview-select'],true)&&$method==='POST'){
  if((int)($input['revision']??0)!==(int)$pm['revision'])problem('Mission wurde inzwischen geändert. Bitte neu öffnen.',409);
  if($action==='preview-save'){
   $settings=json_decode((string)($input['settings']??''),true,32,JSON_THROW_ON_ERROR);if(!is_array($settings)||!in_array($settings['mode']??'', ['3d','map','photo'],true))problem('Vorschau-Einstellungen prüfen.');
   $clean=['mode'=>$settings['mode'],'title'=>dm_text($settings['title']??$pm['name'],200),'provider'=>$settings['provider']??'map'];if(!in_array($clean['provider'],['map','aerial'],true))problem('Kartentyp prüfen.');
   foreach(['yaw'=>[-180,180],'pitch'=>[0,90],'zoom'=>[.2,5],'x'=>[-2000,2000],'y'=>[-2000,2000],'mapZoom'=>[2,19]] as $key=>$range){$v=$settings[$key]??null;if(!is_numeric($v)||!is_finite((float)$v)||$v<$range[0]||$v>$range[1])problem('Vorschau-Einstellungen prüfen.');$clean[$key]=(float)$v;}
   $source=(string)($input['sourceVersion']??'');if(!stmt('SELECT id FROM versions WHERE id=? AND mission=?',[$source,$id])->fetch())problem('Missionsversion nicht gefunden.',404);
   if((int)stmt('SELECT COUNT(*) FROM mission_previews WHERE mission=?',[$id])->fetchColumn()>=100)problem('Maximal 100 Vorschaubilder pro Mission.');
   $hash=dm_store_preview_upload('image');$photo=null;
   if($clean['mode']==='photo'){
    if(isset($_FILES['photo'])&&$_FILES['photo']['error']!==UPLOAD_ERR_NO_FILE)$photo=dm_store_preview_upload('photo');
    else{$prior=stmt('SELECT photo_hash FROM mission_previews WHERE id=? AND mission=?',[(string)($input['photoImage']??''),$id])->fetch();$photo=$prior['photo_hash']??null;if(!$photo)problem('Bitte ein eigenes Bild auswählen.');}
   }
   $pid=dm_id();
  }else{$pid=(string)($input['image']??'');if(!stmt('SELECT id FROM mission_previews WHERE id=? AND mission=?',[$pid,$id])->fetch())problem('Bild nicht gefunden.',404);}
  $db->beginTransaction();$changed=stmt('UPDATE missions SET revision=revision+1 WHERE id=? AND revision=?',[$id,(int)$pm['revision']]);if(!$changed->rowCount()){$db->rollBack();problem('Mission wurde inzwischen geändert. Bitte neu öffnen.',409);}
  if($action==='preview-save')stmt('INSERT INTO mission_previews VALUES(?,?,?,?,?,?,?)',[$pid,$id,$source,$hash,$photo,json_encode($clean,JSON_THROW_ON_ERROR),gmdate('c')]);
  stmt('INSERT INTO mission_preview_selection(mission,preview) VALUES(?,?) ON CONFLICT(mission) DO UPDATE SET preview=excluded.preview',[$id,$pid]);$db->commit();respond(['ok'=>true,'image'=>$pid,'revision'=>(int)$pm['revision']+1]);
 }
 problem('Methode nicht unterstützt.',405);
}
function dm_store_preview_upload(string $key): string {
 $p=$_FILES[$key]??null;if(!$p||$p['error']!==UPLOAD_ERR_OK||!is_uploaded_file($p['tmp_name'])||$p['size']>8388608)problem('Bild fehlt oder ist größer als 8 MB.');
 $info=@getimagesize($p['tmp_name']);if(!$info||!in_array($info['mime'],['image/jpeg','image/png'],true)||$info[0]*$info[1]>16000000)problem('JPEG oder PNG bis 16 Megapixel auswählen.');
 $im=@imagecreatefromstring(file_get_contents($p['tmp_name']));if(!$im)problem('Bild kann nicht gelesen werden.');$out=imagescale($im,min(1600,imagesx($im)));ob_start();imagejpeg($out,null,90);$jpg=ob_get_clean();imagedestroy($out);imagedestroy($im);$hash=hash('sha256',$jpg);$path=dm_private().'/blobs/'.$hash.'.jpg';if(file_put_contents($path,$jpg,LOCK_EX)===false)throw new RuntimeException('Bild nicht gespeichert.');chmod($path,0600);return $hash;
}
