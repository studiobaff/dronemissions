<?php
require_once __DIR__.'/dji-cloud-core.php';
function dm_cloud_schema(): void {
    global $db;
    $db->exec('CREATE TABLE IF NOT EXISTS dji_cloud_records(id TEXT PRIMARY KEY,account TEXT NOT NULL,filename TEXT NOT NULL,metadata TEXT NOT NULL,source_hash TEXT,log TEXT REFERENCES flight_logs(id),status TEXT NOT NULL DEFAULT \'pending\',error TEXT,updated TEXT NOT NULL)');
}
function dm_cloud_rate(string $kind): void {
    $path=dm_cloud_dir().'/rate-'.$kind.'.json';$rows=is_file($path)?json_decode(file_get_contents($path),true):[];$rows=array_values(array_filter($rows,fn($t)=>$t>time()-300));
    if(count($rows)>=10)problem('Zu viele DJI-Anmeldeversuche. Bitte fünf Minuten warten.',429);$rows[]=time();dm_cloud_write($path,$rows);
}
if(str_starts_with($action,'dji-cloud-')) {
    owner();dm_log_schema($db);dm_cloud_schema();
    $lock=fopen(dm_cloud_dir().'/operation.lock','c');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))problem('Eine DJI-Anfrage läuft bereits. Bitte kurz warten.',409);chmod(dm_cloud_dir().'/operation.lock',0600);
    try {
        $session=dm_cloud_session();
        if($action==='dji-cloud-status'&&$method==='GET'){
            $decoder=dm_cloud_decoder('health');respond(['connected'=>$session!==null,'email'=>$session['email']??null,'account'=>$session['account']??null,'decoderReady'=>$decoder['ready']??false]);
        }
        if($method!=='POST')problem('Methode nicht unterstützt.',405);
        if($action==='dji-cloud-disconnect'){dm_cloud_session(null,true);unset($_SESSION['djiChallenge']);respond(['ok'=>true]);}
        if($action==='dji-cloud-captcha'){
            dm_cloud_rate('captcha');$id=substr(bin2hex(random_bytes(8)),0,6);
            $r=dm_cloud_http('https://account-api.dji.com/apis/apprest/v1/vcode?srandom='.$id,null,[],2097152);
            $image=@getimagesizefromstring($r['body']);$mime=$image['mime']??'';if(!$image||!in_array($mime,['image/jpeg','image/png','image/gif','image/webp'],true)||$image[0]<1||$image[1]<1||$image[0]>2048||$image[1]>2048)throw new RuntimeException('DJI lieferte kein CAPTCHA-Bild.');
            $_SESSION['djiChallenge']=['id'=>$id,'created'=>time(),'cookie'=>explode(';',$r['headers']['set-cookie']??'')[0]];
            respond(['challengeId'=>$id,'image'=>'data:'.$mime.';base64,'.base64_encode($r['body'])]);
        }
        if($action==='dji-cloud-login'){
            dm_cloud_rate('login');$challenge=$_SESSION['djiChallenge']??null;unset($_SESSION['djiChallenge']);
            if(!$challenge||$challenge['created']<time()-300||!is_string($input['challengeId']??null)||!hash_equals($challenge['id'],$input['challengeId']))problem('CAPTCHA abgelaufen. Bitte Bild neu laden.');
            $email=strtolower(dm_text($input['email']??'',254));$password=$input['password']??'';$answer=strtoupper(dm_text($input['answer']??'',4));
            if(!filter_var($email,FILTER_VALIDATE_EMAIL)||!is_string($password)||strlen($password)<1||strlen($password)>256||!preg_match('/^[A-Z0-9]{4}$/D',$answer))problem('DJI-E-Mail, Passwort und vierstelligen CAPTCHA-Code eingeben.');
            $body=http_build_query(['email'=>$email,'password'=>dm_cloud_password($password),'srandom'=>$challenge['id'],'verificationCode'=>$answer]);unset($password,$input['password']);
            $headers=dm_cloud_login_headers();if($challenge['cookie']!=='')$headers[]='Cookie: '.$challenge['cookie'];
            $r=dm_cloud_json(dm_cloud_http('https://account-api.dji.com/apis/apprest/v1/email_login',$body,$headers));unset($body);
            $token=dm_cloud_find($r,['token','Token','access_token','accessToken']);if(!is_string($token)||strlen($token)<16||strlen($token)>4096)throw new RuntimeException('DJI lieferte keine gültige Sitzung.');
            dm_cloud_records(dm_cloud_json(dm_cloud_http('https://mydjiflight.dji.com/flight/record_info_list?'.http_build_query(['token'=>$token,'page'=>1,'page_size'=>1]))));
            dm_cloud_session(['email'=>$email,'account'=>hash('sha256',$email),'token'=>$token,'connectedAt'=>gmdate('c')]);respond(['connected'=>true,'email'=>$email]);
        }
        if(!$session)problem('Bitte zuerst dein DJI-Konto verbinden.',409);
        if($action==='dji-cloud-list'){
            $page=filter_var($input['page']??1,FILTER_VALIDATE_INT);if($page===false||$page<1||$page>500)problem('Ungültige Seite.');
            $payload=dm_cloud_json(dm_cloud_http('https://mydjiflight.dji.com/flight/record_info_list?'.http_build_query(['token'=>$session['token'],'page'=>$page,'page_size'=>99])));
            $rows=dm_cloud_records($payload);$out=[];
            foreach($rows as $row){$id=hash('sha256',$session['account']."\0".$row['filename']);stmt('INSERT INTO dji_cloud_records(id,account,filename,metadata,updated) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET metadata=excluded.metadata,updated=excluded.updated',[$id,$session['account'],$row['filename'],json_encode($row,JSON_THROW_ON_ERROR),gmdate('c')]);$saved=stmt('SELECT id,status,log,error FROM dji_cloud_records WHERE id=?',[$id])->fetch();$out[]=$saved+$row+['selected'=>dm_cloud_selected($row,$session['account'])];}
            $more=dm_cloud_find($payload,['has_more','hasMore']);$totalPages=dm_cloud_find($payload,['total_pages','totalPages','page_count']);$total=dm_cloud_find($payload,['total','total_count','totalCount']);
            $done=is_bool($more)?!$more:(is_numeric($totalPages)?$page>=(int)$totalPages:(is_numeric($total)?$page*99>=(int)$total:count($rows)<99));
            respond(['records'=>$out,'done'=>$done,'page'=>$page]);
        }
        if($action==='dji-cloud-sync'){
            set_time_limit(150);$id=dm_text($input['id']??'',64);$row=stmt('SELECT * FROM dji_cloud_records WHERE id=? AND account=?',[$id,$session['account']])->fetch();if(!$row)problem('Flug zuerst aus der DJI-Liste laden.',404);
            if(!dm_cloud_selected(json_decode($row['metadata'],true),$session['account'])||$row['status']==='archived')problem('DJI-Flug liegt außerhalb der gewählten Geräteauswahl und bleibt im Archiv.',409);
            if($row['log'])respond(['id'=>$row['log'],'duplicate'=>true]);
            $folder=($input['folder']??'')?:null;may_folder($folder,true);
            try{
                $hash=$row['source_hash'];$path=$hash?dm_cloud_dir().'/'.$hash.'.txt':null;
                if(!$path||!is_file($path)||!hash_equals($hash,hash_file('sha256',$path))){
                    $download=dm_cloud_download($session['token'],$row['filename']);$raw=dm_cloud_extract($download);$meta=json_decode($row['metadata'],true);$md5=$meta['md5']??'';
                    // The list MD5 has no documented content/payload semantics. Preserve the evidence;
                    // local SHA-256 and successful binary decoding remain required before importing.
                    $md5=strtolower($md5);$integrity=['serverMd5'=>$md5,'contentMd5'=>md5($raw),'payloadMd5'=>md5($download)];
                    $integrity['serverHashKind']=$md5===$integrity['contentMd5']?'content':($md5===$integrity['payloadMd5']?'payload':'unknown');
                    $hash=hash('sha256',$raw);$path=dm_cloud_dir().'/'.$hash.'.txt';if(!is_file($path)){if(file_put_contents($path,$raw,LOCK_EX)===false)throw new RuntimeException('DJI-Fluglog nicht gespeichert.');chmod($path,0600);}
                    dm_cloud_write(dm_cloud_dir().'/integrity-'.$hash.'.json',$integrity);
                    stmt('UPDATE dji_cloud_records SET source_hash=?,status=\'downloaded\',error=NULL WHERE id=?',[$hash,$id]);
                }
                if(!hash_equals($hash,hash_file('sha256',$path)))throw new RuntimeException('Gespeicherte DJI-Datei beschädigt.');
                $export=dm_cloud_decode($path,$hash);$json=json_encode($export,JSON_THROW_ON_ERROR);$log=dm_log_parse($json,$row['filename']);$log['summary']['source']='dji-cloud';
                $missions=dm_payload($db,null)['missions'];$ids=$folder?dm_folder_ids($db,$folder):null;$missions=array_values(array_filter($missions,fn($m)=>($ids===null||in_array($m['folder'],$ids,true))&&dm_format($m['details'])==='kmz'));
                $candidates=dm_log_candidates($log,$missions);$auto=dm_log_auto_candidate($log,$candidates,$missions);
                if($auto){foreach($missions as $m)if($m['id']===$auto['id']){$folder=$m['folder'];break;}}
                $duplicate=stmt('SELECT id FROM flight_logs WHERE folder IS ? AND fingerprint=?',[$folder,$log['fingerprint']])->fetchColumn();
                $db->beginTransaction();try{
                    $lid=$duplicate?:dm_id();
                    if(!$duplicate){$sha=hash('sha256',$json);$blob=dm_private().'/blobs/'.$sha.'.flightlog';if(file_put_contents($blob,$json,LOCK_EX)===false)throw new RuntimeException('Fluglog nicht gespeichert.');chmod($blob,0600);stmt('INSERT INTO flight_logs(id,folder,fingerprint,source_hash,filename,summary,track,created) VALUES(?,?,?,?,?,?,?,?)',[$lid,$folder,$log['fingerprint'],$sha,$row['filename'].'.json',json_encode($log['summary'],JSON_THROW_ON_ERROR),json_encode($log['track'],JSON_THROW_ON_ERROR),gmdate('c')]);if($auto)dm_log_link($lid,$auto['id'],$auto['versionId'],'automatic-route');}
                    stmt('UPDATE dji_cloud_records SET log=?,status=\'imported\',error=NULL WHERE id=?',[$lid,$id]);$db->commit();
                }catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}
                respond(['id'=>$lid,'assigned'=>$auto!==null,'duplicate'=>(bool)$duplicate,'candidates'=>$candidates]);
            }catch(Throwable $e){if($e->getCode()===401)throw $e;stmt('UPDATE dji_cloud_records SET status=\'error\',error=? WHERE id=?',['Abruf oder Entschlüsselung fehlgeschlagen. Bitte erneut versuchen.',$id]);throw $e;}
        }
        problem('Unbekannte DJI-Aktion.',404);
    }catch(Throwable $e){
        if($db->inTransaction())$db->rollBack();
        if($e->getCode()===401){dm_cloud_session(null,true);problem('DJI-Sitzung abgelaufen oder abgelehnt. Bitte neu verbinden.',409);}
        // Do not expose upstream response bodies, request URLs, tokens or parser diagnostics.
        $safe=$e instanceof RuntimeException&&str_starts_with($e->getMessage(),'DJI')?$e->getMessage():'DJI-Verarbeitung fehlgeschlagen. App Key, Verbindung und Logformat prüfen.';
        problem($safe,$e->getCode()===429?429:400);
    }finally{flock($lock,LOCK_UN);fclose($lock);}
}
