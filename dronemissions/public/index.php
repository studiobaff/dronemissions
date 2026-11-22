<?php
$releaseFile=__DIR__.'/release.json';if(is_file($releaseFile)){$release=json_decode(file_get_contents($releaseFile),true);if(preg_match('/^[a-f0-9]{40}$/D',$release['commit']??''))header('X-Drone-Release: '.$release['commit']);}
header('Content-Type: text/html; charset=utf-8');
header('X-Content-Type-Options: nosniff');header('X-Frame-Options: DENY');header('Referrer-Policy: strict-origin-when-cross-origin');  // OpenStreetMap sperrt Kachelanfragen ohne Referer; Freigabe-Token stehen nur im #-Teil und werden nie gesendet
header('Cache-Control: no-store');
$extra='';try{require_once __DIR__.'/lib.php';$extra=implode(' ',array_map(fn($h)=>preg_replace('/[^A-Za-z0-9.*:\/-]/','',$h),dm_layer_hosts(dm_db())));}catch(Throwable $e){$extra='';}  // eigene Kachel-Ebenen aus den Einstellungen
$googleEnabled=function_exists('dm_google_maps_key')&&dm_google_maps_key()!=='';$nonce=base64_encode(random_bytes(18));
$googleSources=$googleEnabled?' https://*.googleapis.com https://*.gstatic.com https://*.google.com https://*.googleusercontent.com':'';
header("Content-Security-Policy: default-src 'self'; script-src 'self'".($googleEnabled?" 'nonce-".$nonce."' 'strict-dynamic' 'unsafe-eval' blob:":'')."; style-src 'self' 'unsafe-inline'".($googleEnabled?' https://fonts.googleapis.com':'')."; img-src 'self' data: blob: https://*.tile.openstreetmap.org https://server.arcgisonline.com https://mapsneu.wien.gv.at".($extra!==''?' '.$extra:'').$googleSources."; connect-src 'self'".$googleSources.($googleEnabled?" data: blob:; font-src 'self' https://fonts.gstatic.com; frame-src https://*.google.com; worker-src blob:":'')."; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
$author='';$path=(getenv('DRONEMISSIONS_PRIVATE') ?: dirname(__DIR__).'/private').'/config.json';
if(is_file($path)){$config=json_decode(file_get_contents($path),true);if(is_array($config)&&is_string($config['authorName']??null))$author=$config['authorName'];}
$escaped=htmlspecialchars($author,ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
echo strtr(str_replace('<script ', '<script nonce="'.$nonce.'" ',file_get_contents(__DIR__.'/view.html')),[
 '{{AUTHOR_TITLE}}'=>$author!==''?' · '.$escaped:'',
 '{{AUTHOR_HEADER}}'=>$author!==''?$escaped:'dronemissions',
 '{{AUTHOR_BADGE}}'=>$author!==''?'<small>'.$escaped.'</small>':''
]);
