<?php
declare(strict_types=1);
// Independently implemented protocol adapter. Reference endpoints/field names:
// arpanghosh8453/Drone-Cloud-Sync, inspected 2026-11-22. No upstream source copied.
function dm_cloud_dir(): string {
    $dir=dm_private().'/dji-cloud';
    if(!is_dir($dir)&&!mkdir($dir,0700,true))throw new RuntimeException('DJI-Ablage nicht verfügbar.');
    return $dir;
}
function dm_cloud_write(string $path,array $value): void {
    $tmp=tempnam(dirname($path),'.write-');if($tmp===false)throw new RuntimeException('DJI-Ablage nicht verfügbar.');
    try{if(!chmod($tmp,0600)||file_put_contents($tmp,json_encode($value,JSON_THROW_ON_ERROR),LOCK_EX)===false||!rename($tmp,$path))throw new RuntimeException('DJI-Daten nicht gespeichert.');}finally{if(is_file($tmp))unlink($tmp);}
}
function dm_cloud_session(?array $save=null,bool $clear=false): ?array {
    $dir=dm_cloud_dir();$path=$dir.'/session.json';
    if($clear){if(is_file($path)&&!unlink($path))throw new RuntimeException('DJI-Sitzung nicht entfernt.');return null;}
    $master=$dir.'/session.key';
    if(!is_file($master)){
        $h=@fopen($master,'x');if($h){chmod($master,0600);fwrite($h,random_bytes(32));fclose($h);}
    }
    $key=file_get_contents($master);if(strlen($key)!==32)throw new RuntimeException('DJI-Sitzungsschlüssel fehlt.');
    if($save!==null){$iv=random_bytes(12);$cipher=openssl_encrypt(json_encode($save,JSON_THROW_ON_ERROR),'aes-256-gcm',$key,OPENSSL_RAW_DATA,$iv,$tag,'dm-dji-session-v1');if($cipher===false)throw new RuntimeException('DJI-Sitzung nicht gespeichert.');dm_cloud_write($path,['iv'=>base64_encode($iv),'tag'=>base64_encode($tag),'data'=>base64_encode($cipher)]);return $save;}
    if(!is_file($path))return null;
    $v=json_decode(file_get_contents($path),true,16,JSON_THROW_ON_ERROR);
    $raw=openssl_decrypt(base64_decode($v['data'],true),'aes-256-gcm',$key,OPENSSL_RAW_DATA,base64_decode($v['iv'],true),base64_decode($v['tag'],true),'dm-dji-session-v1');
    if($raw===false)throw new RuntimeException('DJI-Sitzung nicht lesbar. Bitte neu verbinden.');
    return json_decode($raw,true,16,JSON_THROW_ON_ERROR);
}
function dm_cloud_public_ip(string $ip): bool {return filter_var($ip,FILTER_VALIDATE_IP,FILTER_FLAG_NO_PRIV_RANGE|FILTER_FLAG_NO_RES_RANGE)!==false;}
function dm_cloud_host(string $url): string {
    $p=parse_url($url);$host=strtolower($p['host']??'');
    if(($p['scheme']??'')!=='https'||isset($p['user'])||isset($p['pass'])||($p['port']??443)!==443)throw new RuntimeException('DJI-Downloadziel abgelehnt.');
    foreach(['dji.com','djicdn.com','djistatic.com','amazonaws.com'] as $root)if($host===$root||str_ends_with($host,'.'.$root))return $host;
    throw new RuntimeException('DJI-Downloadziel abgelehnt.');
}
function dm_cloud_http(string $url,?string $body=null,array $headers=[],int $limit=4194304): array {
    $host=dm_cloud_host($url);$ips=gethostbynamel($host);
    if(!$ips)throw new RuntimeException('DJI ist nicht erreichbar.');
    foreach($ips as $ip)if(!dm_cloud_public_ip($ip))throw new RuntimeException('DJI-Downloadziel abgelehnt.');
    $curl=curl_init($url);$data='';$responseHeaders=[];
    curl_setopt_array($curl,[CURLOPT_RETURNTRANSFER=>false,CURLOPT_FOLLOWLOCATION=>false,CURLOPT_CONNECTTIMEOUT=>10,CURLOPT_TIMEOUT=>35,CURLOPT_PROTOCOLS=>CURLPROTO_HTTPS,CURLOPT_SSL_VERIFYPEER=>true,CURLOPT_SSL_VERIFYHOST=>2,CURLOPT_RESOLVE=>[$host.':443:'.$ips[0]],CURLOPT_USERAGENT=>'DroneMissions/1.0',CURLOPT_HTTPHEADER=>$headers,CURLOPT_WRITEFUNCTION=>function($c,$chunk)use(&$data,$limit){if(strlen($data)+strlen($chunk)>$limit)return 0;$data.=$chunk;return strlen($chunk);},CURLOPT_HEADERFUNCTION=>function($c,$line)use(&$responseHeaders){if(str_contains($line,':')){[$k,$v]=explode(':',$line,2);$responseHeaders[strtolower(trim($k))]=trim($v);}return strlen($line);}]);
    if($body!==null){curl_setopt($curl,CURLOPT_POST,true);curl_setopt($curl,CURLOPT_POSTFIELDS,$body);}
    $ok=curl_exec($curl);$code=curl_getinfo($curl,CURLINFO_RESPONSE_CODE);curl_close($curl);
    if($ok===false)throw new RuntimeException('DJI-Anfrage fehlgeschlagen oder Datei zu groß. Bitte später erneut versuchen.');
    if(in_array($code,[401,403],true))throw new RuntimeException('DJI lehnt die Anmeldung ab. Bitte neu verbinden.',401);
    if($code===429)throw new RuntimeException('DJI-Abfragelimit erreicht. Bitte später erneut versuchen.',429);
    if($code>=400||$code<200)throw new RuntimeException('DJI-Dienst derzeit nicht verfügbar.');
    return ['status'=>$code,'headers'=>$responseHeaders,'body'=>$data];
}
function dm_cloud_json(array $response): array {
    $data=json_decode($response['body'],true,64,JSON_THROW_ON_ERROR);if(!is_array($data))throw new RuntimeException('DJI-Antwort unvollständig.');
    $code=(string)($data['code']??$data['Code']??'0');
    if(!in_array($code,['0','200'],true)){
        $msg=strtolower((string)($data['message']??$data['Message']??$data['msg']??''));
        if(in_array($code,['401','403'],true)||((str_contains($msg,'token')||str_contains($msg,'session'))&&(str_contains($msg,'invalid')||str_contains($msg,'expir'))))throw new RuntimeException('DJI-Sitzung abgelaufen. Bitte neu verbinden.',401);
        throw new RuntimeException('DJI hat die Anfrage abgelehnt. Anmeldung bzw. App Key prüfen.');
    }return $data;
}
function dm_cloud_find(array $data,array $keys): mixed {
    foreach($keys as $key)if(array_key_exists($key,$data))return $data[$key];
    foreach($data as $value)if(is_array($value)){ $found=dm_cloud_find($value,$keys);if($found!==null)return $found; }
    return null;
}
function dm_cloud_records(array $data): array {
    $rows=dm_cloud_find($data,['list','List','FileList','fileList','records','Records']);
    if(!is_array($rows)||!array_is_list($rows))throw new RuntimeException('DJI-Flugliste nicht erkannt.');
    $out=[];
    foreach($rows as $row){if(!is_array($row))throw new RuntimeException('DJI-Flugliste unvollständig.');$name=dm_cloud_find($row,['file_name','filename','FileName','fileName','name']);
        if(!is_string($name)||strlen($name)>240||preg_match('~[\\\\/\x00-\x1f]~',$name)||!preg_match('/\.(txt|zip)$/i',$name))throw new RuntimeException('Unbekannter DJI-Dateiname.');
        $get=function(array $keys)use($row){$v=dm_cloud_find($row,$keys);return is_scalar($v)?substr((string)$v,0,200):'';};
        $out[]=['filename'=>$name,'time'=>$get(['start_time','flight_start_time','startTime','create_time','flightTime']),'aircraft'=>$get(['aircraft_name','aircraftName','drone_name','product_name']),'serial'=>$get(['aircraft_sn','aircraftSn','drone_sn','sn']),'md5'=>$get(['md5','Md5','MD5'])];
    }return $out;
}
function dm_cloud_login_headers(): array {
    $uuid=fn()=>sprintf('%s-%s-4%s-a%s-%s',bin2hex(random_bytes(4)),bin2hex(random_bytes(2)),substr(bin2hex(random_bytes(2)),1),substr(bin2hex(random_bytes(2)),1),bin2hex(random_bytes(6)));
    $h=['AppId-Mc'=>'djigo','ClientName-Mc'=>'android-9-4.3.61','DeviceId-Mc'=>$uuid(),'InvokeId-Mc'=>$uuid(),'Timestamp-Mc'=>(string)time()];$signed='';foreach($h as $k=>$v)$signed.=$k.$v;
    $h['Sign-Mc']=base64_encode(hash_hmac('sha1',$signed,'221edf0e-edf7-42b5-a451-776a5872ae4c',true));$h['Encrypted-Mc']='1';$h['Content-Type']='application/x-www-form-urlencoded';return array_map(fn($k,$v)=>$k.': '.$v,array_keys($h),array_values($h));
}
function dm_cloud_password(string $password): string {return bin2hex(openssl_encrypt($password,'aes-128-cbc','221edf0e-edf7-42',OPENSSL_RAW_DATA,'1wdv$ESZ@QAX3rfc'));}
function dm_cloud_download(string $token,string $filename): string {
    $url='https://mydjiflight.dji.com/flight/zipdownload?'.http_build_query(['token'=>$token,'filename'=>$filename]);
    for($hop=0;$hop<6;$hop++){
        $r=dm_cloud_http($url,null,[],16777216);
        if($r['status']>=300&&$r['status']<400){$next=$r['headers']['location']??'';if(str_starts_with($next,'/'))$next='https://'.dm_cloud_host($url).$next;dm_cloud_host($next);$url=$next;continue;}
        if(str_contains($r['headers']['content-type']??'','json')){dm_cloud_json($r);throw new RuntimeException('DJI lieferte kein Fluglog.');}
        $raw=$r['body'];if(strlen($raw)<16)throw new RuntimeException('DJI-Fluglog ist leer.');return $raw;
    }throw new RuntimeException('Zu viele DJI-Weiterleitungen.');
}
function dm_cloud_extract(string $raw): string {
    // DJI also returns RFC 1950 Zlib streams without an archive extension.
    if(strlen($raw)>=2&&(ord($raw[0])&15)===8&&(ord($raw[0])>>4)<=7&&((ord($raw[0])*256+ord($raw[1]))%31)===0){$decoded=@gzuncompress($raw,16777217);if(!is_string($decoded)||strlen($decoded)<16||strlen($decoded)>16777216)throw new RuntimeException('DJI-Zlib nicht lesbar oder zu groß.');return $decoded;}
    if(str_starts_with($raw,"\x1f\x8b")){$decoded=@gzdecode($raw,16777217);if(!is_string($decoded)||strlen($decoded)>16777216)throw new RuntimeException('DJI-GZIP nicht lesbar oder zu groß.');return $decoded;}
    if(!str_starts_with($raw,"PK\x03\x04"))return $raw;
    $tmp=tempnam(dm_cloud_dir(),'.zip-');file_put_contents($tmp,$raw);chmod($tmp,0600);$z=new ZipArchive();
    try{if($z->open($tmp)!==true||$z->numFiles>16)throw new RuntimeException('DJI-Archiv nicht lesbar.');$found=null;
        for($i=0;$i<$z->numFiles;$i++){$s=$z->statIndex($i);if(!str_ends_with(strtolower($s['name']),'.txt'))continue;if($found!==null||$s['size']>16777216)throw new RuntimeException('DJI-Archiv enthält mehrere oder zu große Logs.');$found=$z->getFromIndex($i,16777217);}
        if(!is_string($found)||strlen($found)<16||strlen($found)>16777216)throw new RuntimeException('Kein gültiges DJI-TXT im Archiv.');return $found;
    }finally{$z->close();unlink($tmp);}
}
function dm_cloud_decoder(string $mode,string $path='',?array $chains=null): array {
    $node=is_file('/usr/local/bin/node')?'/usr/local/bin/node':(is_file('/usr/bin/node')?'/usr/bin/node':'node');
    $proc=proc_open([$node,'--max-old-space-size=384',__DIR__.'/dji-decoder.js',$mode,$path],[0=>['pipe','r'],1=>['pipe','w'],2=>['pipe','w']],$pipes);
    if(!is_resource($proc))throw new RuntimeException('DJI-Decoder konnte nicht gestartet werden.');
    $input=json_encode($chains);$written=0;$stdinOpen=true;foreach($pipes as $pipe)stream_set_blocking($pipe,false);$out='';$start=microtime(true);$exit=-1;
    try{do{if($stdinOpen){$n=@fwrite($pipes[0],substr($input,$written,8192));if($n===false){fclose($pipes[0]);$stdinOpen=false;}else{$written+=$n;if($written>=strlen($input)){fclose($pipes[0]);$stdinOpen=false;}}}$out.=stream_get_contents($pipes[1]);stream_get_contents($pipes[2]);if(strlen($out)>16777216||microtime(true)-$start>40){proc_terminate($proc,9);throw new RuntimeException('DJI-Decoder: Zeit-/Größenlimit erreicht.');}$status=proc_get_status($proc);if(!$status['running']){$exit=$status['exitcode'];$out.=stream_get_contents($pipes[1]);break;}usleep(10000);}while(true);
    }finally{if($stdinOpen)fclose($pipes[0]);fclose($pipes[1]);fclose($pipes[2]);proc_close($proc);}
    if($exit!==0)throw new RuntimeException('DJI-Fluglog konnte nicht entschlüsselt werden. App Key bzw. Logversion prüfen.');return json_decode($out,true,64,JSON_THROW_ON_ERROR);
}
function dm_cloud_decode(string $path,string $hash): array {
    $info=dm_cloud_decoder('request',$path);$chains=null;
    if($info['version']>=13){$cache=dm_cloud_dir().'/keychains-'.$hash.'.json';
        if(is_file($cache))$chains=json_decode(file_get_contents($cache),true,64,JSON_THROW_ON_ERROR);
        else{$settings=dm_private().'/dji-log-key.json';$key=is_file($settings)?(json_decode(file_get_contents($settings),true)['apiKey']??''):'';if(!$key)throw new RuntimeException('DJI Open API App Key fehlt für dieses verschlüsselte Fluglog.');
            try{$r=dm_cloud_http('https://dev.dji.com/openapi/v1/flight-records/keychains',json_encode($info['request'],JSON_THROW_ON_ERROR),['Content-Type: application/json','Api-Key: '.$key]);}catch(Throwable $e){throw new RuntimeException('DJI-Entschlüsselungsanfrage fehlgeschlagen. App Key prüfen; die Cloud-Sitzung bleibt verbunden.');}$d=json_decode($r['body'],true,64,JSON_THROW_ON_ERROR);
            if(($d['result']['code']??-1)!==0||!is_array($d['data']??null))throw new RuntimeException('DJI hat den Entschlüsselungsschlüssel nicht geliefert. App Key prüfen.');$chains=$d['data'];
        }
    }
    try{$decoded=dm_cloud_decoder('decode',$path,$chains);}catch(Throwable $e){if(isset($cache)&&is_file($cache))unlink($cache);throw $e;}
    if(isset($cache)&&!is_file($cache))dm_cloud_write($cache,$chains);
    return $decoded;
}

function dm_cloud_selected(array $meta,string $account): bool {
    $path=dm_cloud_dir().'/selection.json';if(!is_file($path))return true;
    $selection=json_decode(file_get_contents($path),true,16,JSON_THROW_ON_ERROR);
    if(($selection['account']??'')!==$account)return true;
    return in_array($meta['serial']??'',array_filter($selection['serials']??[]),true)||in_array(strtolower(trim($meta['aircraft']??'')),$selection['names']??[],true);
}
