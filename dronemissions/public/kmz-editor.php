<?php
if(in_array($action,['kmz-edit-load','kmz-edit-save'],true)){
 if($current&&$current['role']!=='edit')problem('Wegpunktbearbeitung ist nur mit Bearbeitungsrechten verfügbar.',403);
 if(($action==='kmz-edit-load'&&$method!=='GET')||($action==='kmz-edit-save'&&$method!=='POST'))problem('Methode nicht unterstützt.',405);
 require_once __DIR__.'/kmz-editor-core.php';
 $id=(string)($method==='GET'?($_GET['id']??''):($input['id']??''));$m=mission($id,true);
 $v=stmt('SELECT * FROM versions WHERE mission=? ORDER BY ordinal DESC LIMIT 1',[$id])->fetch();
 $details=json_decode($v['details'],true,512,JSON_THROW_ON_ERROR);if(dm_format($details)!=='kmz')problem('Bitte eine DJI-Waypoint-KMZ auswählen.');
 $path=dm_private().'/blobs/'.$v['sha256'].'.kmz';if(!is_file($path)||!hash_equals($v['sha256'],hash_file('sha256',$path)))problem('Archivdatei fehlt oder ist beschädigt.',500);
 if($action==='kmz-edit-load'){$d=dm_ke_load($path);respond(['id'=>$id,'name'=>$m['name'],'folder'=>$m['folder'],'revision'=>(int)$m['revision'],'version'=>$v['id'],'ordinal'=>(int)$v['ordinal'],'sha256'=>$v['sha256'],'heightMode'=>$d['mode'],'structureEditable'=>dm_ke_structure_allowed($d),'points'=>$d['points'],'pois'=>$d['details']['pois'],'pointInfo'=>dm_ke_point_info($d)]);}
 if(($input['version']??null)!==$v['id']||($input['sha256']??null)!==$v['sha256']||($input['revision']??null)!==(int)$m['revision'])problem('Mission wurde inzwischen geändert. Bitte Editor neu öffnen.',409);
 if(!is_array($input['changes']??null)||!is_array($input['deletions']??[])||!is_array($input['insertions']??[]))problem('Wegpunktänderungen fehlen.');
 $tmp=tempnam(dm_private().'/tmp','edit-');try{
  $changes=dm_ke_edit($path,$tmp,$input['changes'],$input['deletions']??[],$input['insertions']??[]);$next=dm_inspect($tmp);$sha=hash_file('sha256',$tmp);$blob=dm_private().'/blobs/'.$sha.'.kmz';
  if(!is_file($blob)&&!copy($tmp,$blob))throw new RuntimeException('Neue KMZ konnte nicht gesichert werden.');chmod($blob,0600);if(!hash_equals($sha,hash_file('sha256',$blob)))throw new RuntimeException('Neue KMZ-Prüfsumme falsch.');
  $next['sourceFormat']='dji-kmz';$next['editor']=['format'=>'waypoint-edit/1','sourceVersion'=>$v['id'],'sourceSha256'=>$v['sha256'],'changes'=>$changes];
  $now=gmdate('c');$vid=dm_id();$db->beginTransaction();
  $s=stmt('UPDATE missions SET updated=?,revision=revision+1 WHERE id=? AND revision=?',[$now,$id,$m['revision']]);
  $latest=stmt('SELECT id FROM versions WHERE mission=? ORDER BY ordinal DESC LIMIT 1',[$id])->fetchColumn();
  if(!$s->rowCount()||$latest!==$v['id']){$db->rollBack();unlink($tmp);problem('Mission wurde inzwischen geändert. Bitte Editor neu öffnen.',409);}
  $ordinal=(int)$v['ordinal']+1;stmt('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',[$vid,$id,$ordinal,$v['filename'],$sha,filesize($blob),json_encode($next,JSON_THROW_ON_ERROR),$now]);
  // Preserve picture history, but do not present an old route image as this edited route.
  stmt('DELETE FROM mission_preview_selection WHERE mission=?',[$id]);
  if(!empty($input['deletions'])||!empty($input['insertions']))stmt('UPDATE missions SET overview_waypoint=NULL,overview_version=NULL WHERE id=?',[$id]);
  elseif($m['overview_version']===$v['id'])stmt('UPDATE missions SET overview_version=? WHERE id=?',[$vid,$id]);
  $db->commit();$result=['id'=>$id,'version'=>$ordinal,'versionId'=>$vid,'changed'=>count($changes),'sha256'=>$sha];
 }finally{if(is_file($tmp))unlink($tmp);}
 respond($result);
}
