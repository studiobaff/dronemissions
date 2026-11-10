<?php
/** Installed outside the webroot; forced-command SSH entry point, PHP 8.3+. */
declare(strict_types=1);
function fail(string $message): never { throw new RuntimeException($message); }
function run(array $command): void {
 $pipes=[];$proc=proc_open($command,[0=>['file','/dev/null','r'],1=>['pipe','w'],2=>['pipe','w']],$pipes);
 if(!is_resource($proc))fail('Cannot start validation');
 $out=stream_get_contents($pipes[1]);$err=stream_get_contents($pipes[2]);fclose($pipes[1]);fclose($pipes[2]);
 if(proc_close($proc)!==0)fail('Validation failed: '.$out.$err);
}
function switch_link(string $live,string $target): void {
 $tmp=$live.'.next-'.bin2hex(random_bytes(6));
 if(!symlink($target,$tmp))fail('Cannot stage release link');
 if(!rename($tmp,$live)){unlink($tmp);fail('Cannot activate release');}
}
function receive(array $config,string $command,string $input): array {
 if(!preg_match('/^deploy ([a-f0-9]{40}) ([a-f0-9]{64})$/D',$command,$match))fail('Only deploy SHA SHA256 is permitted');
 [, $sha,$hash]=$match;
 $root=$config['releases'];$live=$config['live'];$private=$config['private'];
 if(!is_dir($root)||!is_dir($private))fail('Server paths are not configured');
 $lock=fopen($root.'/deploy.lock','c');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))fail('Another deployment is running');
 if(strlen($input)>33554432||!hash_equals($hash,hash('sha256',$input)))fail('Invalid release archive');
 $id=$sha.'-'.bin2hex(random_bytes(4));$stage=$root.'/'.$id;
 if(!mkdir($stage,0755))fail('Cannot create release');chmod($stage,0755);
 $archive=$root.'/.'.$id.'.zip';file_put_contents($archive,$input);chmod($archive,0600);
 $zip=new ZipArchive();if($zip->open($archive)!==true)fail('Invalid ZIP');
 try {
  if($zip->numFiles>1000)fail('Too many release files');
  $raw=$zip->getFromName('release.json');if($raw===false||strlen($raw)>262144)fail('Missing release manifest');
  $manifest=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
  if(($manifest['commit']??null)!==$sha||!is_array($manifest['files']??null))fail('Invalid release manifest');
  if(count($manifest['files'])+1!==$zip->numFiles)fail('Unexpected archive entries');
  foreach(['index.php','api.php','lib.php','view.html','app.js','style.css'] as $name)if(!isset($manifest['files'][$name]))fail('Incomplete application');
  $seen=[];$total=0;
  for($i=0;$i<$zip->numFiles;$i++){
   $stat=$zip->statIndex($i);$name=$stat['name'];
   if(isset($seen[$name]))fail('Duplicate release entry');$seen[$name]=true;
   if(!preg_match('~^[A-Za-z0-9_-]+(?:[./][A-Za-z0-9_-]+)*$~D',$name)||str_contains($name,'..')||str_contains($name,'/.'))fail('Invalid release path');
   if($name!=='release.json'&&!in_array($name,['vendor/leaflet-LICENSE','vendor/fonts/DejaVu-LICENSE'],true)&&!in_array(strtolower(pathinfo($name,PATHINFO_EXTENSION)),['php','js','css','html','png','jpg','jpeg','svg','webp','ico','woff','woff2'],true))fail('Unexpected release file');
   $total+=$stat['size'];if($total>67108864)fail('Unpacked release too large');
   $data=$zip->getFromIndex($i);if($data===false)fail('Cannot read entry');
   if($name!=='release.json'&&(!isset($manifest['files'][$name])||!hash_equals($manifest['files'][$name],hash('sha256',$data))))fail('Release checksum mismatch');
   $dest=$stage.'/'.$name;if(!is_dir(dirname($dest))){mkdir(dirname($dest),0755,true);$dir=dirname($dest);while($dir!==$stage){chmod($dir,0755);$dir=dirname($dir);}}
   if(file_put_contents($dest,$data)!==strlen($data))fail('Cannot write release');chmod($dest,0644);
   if(str_ends_with($name,'.php'))run([PHP_BINARY,'-l',$dest]);
   if(str_ends_with($name,'.js'))run([$config['node']??'/usr/local/bin/node','--check',$dest]);
  }
 } finally { $zip->close();unlink($archive); }
 // SQLite snapshot is consistent even with concurrent readers/writers. Never copy an active DB.
 $backup=$root.'/backups/'.$id;if(!is_dir(dirname($backup)))mkdir(dirname($backup),0700,true);
 mkdir($backup,0700);
 if(is_file($private.'/missions.sqlite')){
  $db=new PDO('sqlite:'.$private.'/missions.sqlite',null,null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
  $db->exec('PRAGMA busy_timeout=10000');$q=$db->prepare('VACUUM INTO ?');$q->execute([$backup.'/missions.sqlite']);chmod($backup.'/missions.sqlite',0600);$db=null;
 }
 if(is_file($private.'/config.json')){if(!copy($private.'/config.json',$backup.'/config.json'))fail('Config backup failed');chmod($backup.'/config.json',0600);}
 // Existing originals/sessions/cache remain at the same private path and are never replaced.
 $previous=is_link($live)?readlink($live):null;
 if($previous===null){
  if(!is_dir($live))fail('Live installation missing');
  $previous=$root.'/pre-actions-'.gmdate('Ymd-His').'-'.bin2hex(random_bytes(3));
  if(!rename($live,$previous))fail('Cannot preserve initial installation');
  try { switch_link($live,$previous); } catch(Throwable $e){rename($previous,$live);throw $e;}
 }
 try {
  switch_link($live,$stage);
  $context=stream_context_create(['http'=>['timeout'=>15,'ignore_errors'=>true],'ssl'=>['verify_peer'=>true,'verify_peer_name'=>true]]);
  $url=rtrim($config['url'],'/').'/';
  $served=@file_get_contents($url.'release.json?deploy='.$sha,false,$context);
  if($served===false||(json_decode($served,true)['commit']??null)!==$sha)fail('HTTPS release verification failed');
  $page=@file_get_contents($url,false,$context);
  if($page===false||!preg_match('~^HTTP/\S+ 200\b~',$http_response_header[0]??''))fail('HTTPS application check failed');
 } catch(Throwable $e){switch_link($live,$previous);throw $e;}
 $receipt=['commit'=>$sha,'previous'=>$previous,'current'=>$stage,'backup'=>$backup,'time'=>gmdate(DATE_ATOM)];
 file_put_contents($root.'/last-deployment.json',json_encode($receipt,JSON_PRETTY_PRINT));chmod($root.'/last-deployment.json',0600);
 return ['commit'=>$sha,'status'=>'published'];
}
if(realpath($_SERVER['SCRIPT_FILENAME']??'')===__FILE__){
 try {
  umask(0077);$config=json_decode(file_get_contents(__DIR__.'/config.json'),true,512,JSON_THROW_ON_ERROR);
  $input=file_get_contents('php://stdin',false,null,0,33554433);
  echo json_encode(receive($config,getenv('SSH_ORIGINAL_COMMAND')?:'', $input),JSON_THROW_ON_ERROR)."\n";
 } catch(Throwable $e){fwrite(STDERR,'Deployment stopped: '.$e->getMessage()."\n");exit(1);}
}
