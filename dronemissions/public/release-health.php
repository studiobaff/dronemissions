<?php
declare(strict_types=1);
header('Cache-Control: no-store');
// A short-lived deployment MAC is created server-side; no browser/user session
// can reset OPcache. Keep this entry point independent of cached application PHP.
try {
 clearstatcache(true);
 $public=realpath(dirname($_SERVER['SCRIPT_FILENAME']??__FILE__));
 $manifest=json_decode(file_get_contents($public.'/release.json'),true,512,JSON_THROW_ON_ERROR);
 $private=getenv('DRONEMISSIONS_PRIVATE')?:'/usr/local/www/vhosts/studiobaff/dronemissions-private';
 $config=json_decode(file_get_contents($private.'/config.json'),true,512,JSON_THROW_ON_ERROR);
 $stamp=$_SERVER['HTTP_X_DEPLOY_TIME']??'';$secret=$config['rateSecret']??'';
 if(($_SERVER['REQUEST_METHOD']??'')!=='POST'||!ctype_digit($stamp)||abs(time()-(int)$stamp)>60||!is_string($secret)||strlen($secret)<32||!hash_equals(hash_hmac('sha256','release-reset|'.$manifest['commit'].'|'.$stamp,$secret),$_SERVER['HTTP_X_DEPLOY_MAC']??'')){
  http_response_code(404);exit;
 }
 $enabled=filter_var(ini_get('opcache.enable'),FILTER_VALIDATE_BOOLEAN)&&(PHP_SAPI!=='cli-server'||filter_var(ini_get('opcache.enable_cli'),FILTER_VALIDATE_BOOLEAN));
 if($enabled&&(!function_exists('opcache_reset')||!opcache_reset()))throw new RuntimeException('Cache reset unavailable');
 header('Content-Type: application/json');echo json_encode(['commit'=>$manifest['commit'],'ok'=>true]);
}catch(Throwable $e){http_response_code(503);echo 'Release check unavailable';}
