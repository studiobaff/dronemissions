<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require __DIR__.'/../public/lib.php';
umask(0077);$dir=dm_private();if(is_file($dir.'/config.json')){fwrite(STDERR,"Bereits eingerichtet; keine Änderung.\n");exit(1);}
$input=json_decode(stream_get_contents(STDIN),true,16,JSON_THROW_ON_ERROR);$password=$input['password']??'';if(!is_string($password)||strlen($password)<24)throw new RuntimeException('Zugangsschlüssel muss mindestens 24 Zeichen enthalten.');
foreach([$dir,$dir.'/sessions',$dir.'/blobs',$dir.'/tmp'] as $p)if(!is_dir($p)&&!mkdir($p,0700,true))throw new RuntimeException('Privates Verzeichnis konnte nicht angelegt werden.');
$author=dm_text($input['authorName']??'',100);
$db=dm_db();dm_schema($db);$json=json_encode(['authorName'=>$author,'passwordHash'=>password_hash($password,PASSWORD_DEFAULT),'rateSecret'=>bin2hex(random_bytes(32))],JSON_THROW_ON_ERROR);$h=fopen($dir.'/config.json','x');if(!$h)throw new RuntimeException('Konfiguration existiert bereits.');fwrite($h,$json);fclose($h);echo "Installation eingerichtet.\n";
