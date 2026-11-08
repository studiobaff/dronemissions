<?php
header('Content-Type: text/html; charset=utf-8');
header('X-Content-Type-Options: nosniff');header('X-Frame-Options: DENY');header('Referrer-Policy: strict-origin-when-cross-origin');  // OpenStreetMap sperrt Kachelanfragen ohne Referer; Freigabe-Token stehen nur im #-Teil und werden nie gesendet
header('Cache-Control: no-store');
$extra='';try{require_once __DIR__.'/lib.php';$extra=implode(' ',array_map(fn($h)=>preg_replace('/[^A-Za-z0-9.*:\/-]/','',$h),dm_layer_hosts(dm_db())));}catch(Throwable $e){$extra='';}  // eigene Kachel-Ebenen aus den Einstellungen
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org https://server.arcgisonline.com https://mapsneu.wien.gv.at".($extra!==''?' '.$extra:'')."; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
$author='';$path=(getenv('DRONEMISSIONS_PRIVATE') ?: '/usr/local/www/vhosts/studiobaff/dronemissions-private').'/config.json';
if(is_file($path)){$config=json_decode(file_get_contents($path),true);if(is_array($config)&&is_string($config['authorName']??null))$author=$config['authorName'];}
$escaped=htmlspecialchars($author,ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
echo strtr(file_get_contents(__DIR__.'/view.html'),[
 '{{AUTHOR_TITLE}}'=>$author!==''?' · '.$escaped:'',
 '{{AUTHOR_HEADER}}'=>$author!==''?$escaped:'dronemissions',
 '{{AUTHOR_BADGE}}'=>$author!==''?'<small>'.$escaped.'</small>':''
]);
