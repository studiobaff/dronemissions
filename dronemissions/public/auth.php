<?php
declare(strict_types=1);
// Publisher is the authority for administrator membership and SMTP configuration.
function dm_auth_path(string $key): string {
 global $config;
 $path=$config['emailLogin'][$key]??null;
 if(!is_string($path)||!str_starts_with($path,'/')||!is_file($path))throw new RuntimeException('Email login configuration unavailable');
 return $path;
}
function dm_login_allowed(string $email): bool {
 $users=new PDO('sqlite:'.dm_auth_path('usersDatabase'),null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
 $users->exec('PRAGMA query_only=ON; PRAGMA busy_timeout=5000');
 $q=$users->prepare("SELECT 1 FROM users WHERE lower(email)=? AND active=1 AND role IN ('admin','superadmin') LIMIT 1");
 $q->execute([$email]);return (bool)$q->fetchColumn();
}
function dm_owner_valid(): bool {
 if(empty($_SESSION['owner']))return false;
 $valid=($_SESSION['expires']??0)>time() && is_string($_SESSION['email']??null) && dm_login_allowed($_SESSION['email']);
 if(!$valid)unset($_SESSION['owner'],$_SESSION['email'],$_SESSION['expires']);
 return $valid;
}
function dm_session_cookie(int $expires): void {
 $params=session_get_cookie_params();unset($params['lifetime']);
 setcookie(session_name(),session_id(),['expires'=>$expires]+$params);
}
function dm_login_rate(string $identity,int $limit): void {
 global $config,$db;
 $key=hash_hmac('sha256','email-login|'.$identity,$config['rateSecret']);
 $db->exec('BEGIN IMMEDIATE');
 try {
  stmt('DELETE FROM login_attempts WHERE happened<?',[time()-86400]);
  $q=stmt('SELECT COUNT(*) FROM login_attempts WHERE ip=? AND happened>?',[$key,time()-900]);$count=(int)$q->fetchColumn();$q->closeCursor();
  if($count >= $limit){$db->exec('COMMIT');problem('Zu viele Versuche. Bitte in 15 Minuten erneut versuchen.',429);}
  stmt('INSERT INTO login_attempts VALUES(?,?)',[$key,time()]);$db->exec('COMMIT');
 }catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}
}
function dm_auth_route(string $action,string $method,array $input): void {
 global $config;
 if($method!=='POST'||!in_array($action,['login','login-verify'],true))return;
 dm_login_rate('ip|'.($_SERVER['REMOTE_ADDR']??''),30);
 if($action==='login'){
  unset($_SESSION['otp']);
  $email=$input['email']??'';if(is_string($email))$email=trim($email);
  if(!is_string($email)||strlen($email)>254||!filter_var($email,FILTER_VALIDATE_EMAIL))problem('Bitte eine gültige E-Mail-Adresse eingeben.');
  $email=strtolower(trim($email));dm_login_rate('email|'.$email,5);
  $challenge=bin2hex(random_bytes(32));$code=str_pad((string)random_int(0,999999),6,'0',STR_PAD_LEFT);
  $allowed=dm_login_allowed($email);
  $_SESSION['otp']=['email'=>$email,'challenge'=>$challenge,'hash'=>hash_hmac('sha256',$challenge.'|'.$code,$config['rateSecret']),'expires'=>time()+480,'tries'=>0,'allowed'=>$allowed];
  if($allowed){try{dm_send_code($email,$code);}catch(Throwable $e){unset($_SESSION['otp']);error_log('Drone Missions: SMTP login delivery failed');problem('E-Mail konnte nicht versendet werden. Bitte später erneut versuchen.',503);}}
  respond(['ok'=>true,'message'=>'Wenn diese Adresse berechtigt ist, erhältst du einen Code. Er gilt 8 Minuten.']);
 }
 $otp=$_SESSION['otp']??null;$code=$input['code']??'';
 if(!$otp||$otp['expires']<=time()||$otp['tries']>=5){unset($_SESSION['otp']);problem('Code abgelaufen. Bitte einen neuen Code anfordern.',401);}
 $_SESSION['otp']['tries']++;
 $valid=is_string($code)&&preg_match('/^[0-9]{6}$/D',$code)&&hash_equals($otp['hash'],hash_hmac('sha256',$otp['challenge'].'|'.$code,$config['rateSecret']));
 if(!$valid||!$otp['allowed']||!dm_login_allowed($otp['email'])){if($_SESSION['otp']['tries']>=5)unset($_SESSION['otp']);problem('Code ungültig oder abgelaufen.',401);}
 session_regenerate_id(true);
 $_SESSION=['owner'=>true,'email'=>$otp['email'],'expires'=>time()+43200,'csrf'=>bin2hex(random_bytes(32))];
 dm_session_cookie($_SESSION['expires']);
 respond(['ok'=>true,'csrf'=>$_SESSION['csrf']]);
}

function dm_login_mail(string $sender,string $recipient,string $code): string {
    if(!filter_var($sender,FILTER_VALIDATE_EMAIL)||!filter_var($recipient,FILTER_VALIDATE_EMAIL)||preg_match('/[\r\n]/',$sender.$recipient)||!preg_match('/^[0-9]{6}$/D',$code))throw new RuntimeException('Ungültige Anmeldemail');
    $boundary='baff_'.bin2hex(random_bytes(18));
    $text="Dein Anmeldecode für Drone Missions: ".$code."\r\n\r\nDer Code gilt 8 Minuten und kann einmal verwendet werden. Nach der Anmeldung bleibst du bis zu 12 Stunden angemeldet.\r\n\r\nGib den Code nur auf service.studiobaff.com ein. Wenn du ihn nicht angefordert hast, kannst du diese E-Mail ignorieren.\r\n";
    $html='<!doctype html><html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="margin:0;background:#f3f4f6;color:#17202b;font-family:Arial,Helvetica,sans-serif"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:32px 16px"><table role="presentation" width="520" cellspacing="0" cellpadding="0" style="width:100%;max-width:520px;background:#ffffff;border-radius:16px"><tr><td style="padding:32px"><p style="margin:0 0 28px;font-size:20px;font-weight:bold">Drone Missions</p><h1 style="margin:0 0 16px;font-size:26px">Dein Anmeldecode</h1><p style="font-size:16px;line-height:1.6">Gib diesen sechsstelligen Code bei Drone Missions ein:</p><div style="margin:24px 0;padding:22px 12px;text-align:center;background:#eef3ff;border-radius:12px;font-family:Consolas,monospace;font-size:38px;font-weight:bold;letter-spacing:6px;color:#1646b5">'.$code.'</div><p style="font-size:15px;line-height:1.6"><strong>8 Minuten gültig · einmal verwendbar</strong><br>Nach der Anmeldung bleibst du bis zu 12 Stunden angemeldet.</p><p style="margin-top:28px;font-size:13px;line-height:1.6;color:#586476">Gib den Code nur auf service.studiobaff.com ein. Wenn du ihn nicht angefordert hast, kannst du diese E-Mail ignorieren.</p></td></tr></table></td></tr></table></body></html>';
    $headers='From: Drone Missions <'.$sender.'>'."\r\n".'To: '.$recipient."\r\nSubject: Drone Missions - Anmeldecode\r\nMIME-Version: 1.0\r\n".'Content-Type: multipart/alternative; boundary="'.$boundary.'"'."\r\n\r\n";
    $part=static fn(string $type,string $body): string=>'--'.$boundary."\r\nContent-Type: ".$type."; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n".chunk_split(base64_encode($body),76,"\r\n");
    return $headers.$part('text/plain',$text).$part('text/html',$html).'--'.$boundary."--\r\n";
}
function dm_send_code(string $recipient,string $code): void {$mailConfig=json_decode(file_get_contents(dm_auth_path('smtpConfig')),true,512,JSON_THROW_ON_ERROR);$m=$mailConfig['smtp'];if(!filter_var($recipient,FILTER_VALIDATE_EMAIL)||!filter_var($m['sender'],FILTER_VALIDATE_EMAIL))throw new RuntimeException('Mailadresse ungültig');$message=dm_login_mail($m['sender'],$recipient,$code);$stream=fopen('php://temp','r+');fwrite($stream,$message);rewind($stream);$curl=curl_init(((int)$m['port']===465?'smtps://':'smtp://').$m['host'].':'.$m['port']);curl_setopt_array($curl,[CURLOPT_USERNAME=>$m['username'],CURLOPT_PASSWORD=>$m['password'],CURLOPT_MAIL_FROM=>$m['sender'],CURLOPT_MAIL_RCPT=>[$recipient],CURLOPT_UPLOAD=>true,CURLOPT_READDATA=>$stream,CURLOPT_INFILESIZE=>strlen($message),CURLOPT_USE_SSL=>CURLUSESSL_ALL,CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2,CURLOPT_TIMEOUT=>25,CURLOPT_RETURNTRANSFER=>true]);if(isset($m['caFile']))curl_setopt($curl,CURLOPT_CAINFO,$m['caFile']);$ok=curl_exec($curl);curl_close($curl);fclose($stream);if($ok===false)throw new RuntimeException('SMTP-Versand fehlgeschlagen');}
