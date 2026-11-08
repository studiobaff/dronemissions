<?php
// Only a freshly created, empty temporary installation; never production.
declare(strict_types=1);
$dir=$argv[1]??'';
if(!str_starts_with($dir,sys_get_temp_dir().'/dm-preview-')||!is_dir($dir)||count(scandir($dir))!==2)throw new RuntimeException('An empty dm-preview-* temporary directory is required');
foreach(['sessions','blobs','tmp'] as $name)mkdir($dir.'/'.$name,0700);
putenv('DRONEMISSIONS_PRIVATE='.$dir);require __DIR__.'/../public/lib.php';
$db=new PDO('sqlite:'.$dir.'/missions.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);dm_schema($db);
// Verify idempotent migration against existing data/schema as used by old installations.
$db->exec('DROP TABLE mission_preview_selection; DROP TABLE mission_previews');dm_migrate($db);dm_migrate($db);
if((int)$db->query("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('mission_previews','mission_preview_selection')")->fetchColumn()!==2)throw new RuntimeException('Missing preview migration');
$password='synthetic-preview-test-only';file_put_contents($dir.'/config.json',json_encode(['passwordHash'=>password_hash($password,PASSWORD_DEFAULT),'rateSecret'=>bin2hex(random_bytes(32))]));
file_put_contents($dir.'/access.json',json_encode(['password'=>$password]));chmod($dir.'/config.json',0600);chmod($dir.'/access.json',0600);
