<?php
declare(strict_types=1);
// Device credentials never grant owner authority. The legacy Bridge wire format
// is retained, but only newly issued random credentials are accepted.
function dm_device_schema(): void {
 global $db;
 $db->exec('CREATE TABLE IF NOT EXISTS device_keys(id TEXT PRIMARY KEY,name TEXT NOT NULL,issuer TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,created INTEGER NOT NULL,expires INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,last_used INTEGER)');
}
function dm_device_valid(): bool {
 if(empty($_SESSION['device']))return false;
 $key=stmt('SELECT * FROM device_keys WHERE id=?',[$_SESSION['device']])->fetch();
 $valid=$key&&!$key['revoked']&&(int)$key['expires']>time()&&($_SESSION['expires']??0)>time()&&dm_login_allowed($key['issuer']);
 if(!$valid)unset($_SESSION['device'],$_SESSION['expires']);
 return (bool)$valid;
}
function dm_device_guard(string $action,string $method): void {
 if(empty($_SESSION['device']))return;
 if(!dm_device_valid())problem('Gerätezugang abgelaufen oder widerrufen. Bitte neu verbinden.',401);
 $allowed=$method==='GET'?['session','library','original','preview']:['logout','upload','preview-save','missions-move'];
 if(!in_array($action,$allowed,true))problem('Dieser Gerätezugang erlaubt nur Missionsübertragung und Archiv-Sicherung.',403);
}
function dm_device_route(string $action,string $method,array $input): void {
 if($action==='login'&&$method==='POST'&&array_key_exists('password',$input)){
  dm_login_rate('device-ip|'.($_SERVER['REMOTE_ADDR']??''),10);
  $token=$input['password'];
  if(!is_string($token)||!preg_match('/^dmb_[a-f0-9]{64}$/D',$token))problem('Bitte einen neuen Geräteschlüssel im Webarchiv unter Bridge erstellen.',401);
  $key=stmt('SELECT * FROM device_keys WHERE token_hash=?',[hash('sha256',$token)])->fetch();
  if(!$key||$key['revoked']||(int)$key['expires']<=time()||!dm_login_allowed($key['issuer']))problem('Geräteschlüssel ungültig, abgelaufen oder widerrufen.',401);
  session_regenerate_id(true);
  $_SESSION=['device'=>$key['id'],'expires'=>min(time()+43200,(int)$key['expires']),'csrf'=>bin2hex(random_bytes(32))];
  stmt('UPDATE device_keys SET last_used=? WHERE id=?',[time(),$key['id']]);
  dm_session_cookie($_SESSION['expires']);respond(['ok'=>true,'csrf'=>$_SESSION['csrf'],'role'=>'device']);
 }
 if(!in_array($action,['device-keys','device-key-create','device-key-revoke'],true))return;
 owner();
 if($action==='device-keys'&&$method==='GET')respond(['keys'=>stmt('SELECT id,name,created,expires,revoked,last_used FROM device_keys WHERE issuer=? ORDER BY created DESC',[$_SESSION['email']])->fetchAll()]);
 if($action==='device-key-create'&&$method==='POST'){
  $name=dm_text($input['name']??'',80);if($name==='')problem('Bitte einen Gerätenamen eingeben.');
  if((int)stmt('SELECT COUNT(*) FROM device_keys WHERE issuer=? AND revoked=0 AND expires>?',[$_SESSION['email'],time()])->fetchColumn()>=20)problem('Maximal 20 aktive Geräteschlüssel. Bitte einen alten Zugang widerrufen.');
  $token='dmb_'.bin2hex(random_bytes(32));$id=dm_id();$expires=time()+180*86400;
  stmt('INSERT INTO device_keys(id,name,issuer,token_hash,created,expires) VALUES(?,?,?,?,?,?)',[$id,$name,$_SESSION['email'],hash('sha256',$token),time(),$expires]);
  respond(['id'=>$id,'token'=>$token,'expires'=>$expires]);
 }
 if($action==='device-key-revoke'&&$method==='POST'){
  stmt('UPDATE device_keys SET revoked=1 WHERE id=? AND issuer=?',[(string)($input['id']??''),$_SESSION['email']]);respond(['ok'=>true]);
 }
 problem('Methode nicht unterstützt.',405);
}
