<?php
// Disposable local installation only; never points at production data.
require dirname(__DIR__).'/receiver.php';
$root=sys_get_temp_dir().'/dm-deploy-test-'.bin2hex(random_bytes(6));mkdir($root,0700);
$releases=$root.'/releases';$private=$root.'/private';$web=$root.'/web';$live=$web.'/dronemissions';
foreach([$releases,$private,$web,$live] as $dir)mkdir($dir,0755,true);
file_put_contents($live.'/index.php','OLD');
$db=new PDO('sqlite:'.$private.'/missions.sqlite');$db->exec("CREATE TABLE test(value TEXT); INSERT INTO test VALUES ('preserved')");$db=null;
file_put_contents($private.'/config.json','{"owner":"preserved"}');
file_put_contents($private.'/original.kmz','UNCHANGED');
$socket=stream_socket_server('tcp://127.0.0.1:0',$errno,$error);$address=stream_socket_get_name($socket,false);fclose($socket);
$pipes=[];$server=proc_open([PHP_BINARY,'-S',$address,'-t',$web],[0=>['file','/dev/null','r'],1=>['file',$root.'/server.log','a'],2=>['file',$root.'/server.log','a']],$pipes);
function check(bool $ok,string $message): void {if(!$ok)throw new RuntimeException($message);}
function archive(string $root,string $sha,bool $broken=false): string {
 $path=$root.'/test.zip';@unlink($path);$z=new ZipArchive();$z->open($path,ZipArchive::CREATE);
 $files=['index.php'=>$broken?'<?php http_response_code(500); echo "BROKEN";':'<?php echo "NEW";','api.php'=>'<?php echo "API";','lib.php'=>'<?php // lib','view.html'=>'view','app.js'=>'const example = 1;','style.css'=>'body {}'];$hashes=[];
 foreach($files as $name=>$bytes){$z->addFromString($name,$bytes);$hashes[$name]=hash('sha256',$bytes);}
 $z->addFromString('release.json',json_encode(['commit'=>$sha,'files'=>$hashes]));$z->close();return file_get_contents($path);
}
try {
 for($i=0;$i<30;$i++){if(@file_get_contents('http://'.$address.'/dronemissions/')!==false)break;usleep(100000);}
 $cfg=['live'=>$live,'releases'=>$releases,'private'=>$private,'url'=>'http://'.$address.'/dronemissions','node'=>'node'];
 $data=archive($root,str_repeat('a',40));receive($cfg,'deploy '.str_repeat('a',40).' '.hash('sha256',$data),$data);
 check(is_link($live),'Live directory was not converted');$first=readlink($live);
 check(file_get_contents($private.'/original.kmz')==='UNCHANGED','Original changed');
 $db=new PDO('sqlite:'.$private.'/missions.sqlite');check($db->query('SELECT value FROM test')->fetchColumn()==='preserved','DB data lost');$db=null;
 $data=archive($root,str_repeat('b',40),true);$failed=false;
 try{receive($cfg,'deploy '.str_repeat('b',40).' '.hash('sha256',$data),$data);}catch(RuntimeException $e){$failed=true;}
 check($failed,'Broken HTTP deployment accepted');clearstatcache();check(readlink($live)===$first,'Rollback failed');
 $failed=false;try{receive($cfg,'arbitrary shell command','');}catch(RuntimeException $e){$failed=true;}check($failed,'Unrestricted command accepted');
 $data=archive($root,str_repeat('c',40));$failed=false;try{receive($cfg,'deploy '.str_repeat('c',40).' '.str_repeat('0',64),$data);}catch(RuntimeException $e){$failed=true;}check($failed,'Wrong checksum accepted');
 echo "PASS: publish, initial-directory conversion, consistent DB backup, private data preservation, HTTP failure rollback, restricted command, checksum rejection\n";
}finally{
 proc_terminate($server);proc_close($server);
 // All test paths were freshly created under a random /tmp directory.
 $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS),RecursiveIteratorIterator::CHILD_FIRST);
 foreach($it as $p){if($p->isDir()&&!$p->isLink())rmdir($p->getPathname());else unlink($p->getPathname());}rmdir($root);
}
