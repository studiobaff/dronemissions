<?php
declare(strict_types=1);
require __DIR__.'/../public/dji-cloud-core.php';
require __DIR__.'/../public/flight-logs-core.php';
function check(bool $yes,string $message):void {if(!$yes)throw new RuntimeException($message);}
foreach(['https://evil.test/a','http://dji.com/a','https://dji.com@evil.test/a','https://evil-dji.com/a','https://dji.com:8443/a'] as $url){$rejected=false;try{dm_cloud_host($url);}catch(Throwable $e){$rejected=true;}check($rejected,'Unsafe redirect accepted');}
check(dm_cloud_host('https://mydjiflight.dji.com/a')==='mydjiflight.dji.com','Host rejected');
foreach(['127.0.0.1','10.0.0.1','169.254.169.254','192.168.1.1','::1'] as $ip)check(!dm_cloud_public_ip($ip),'Private address accepted');
$records=dm_cloud_records(['data'=>['records'=>[['FileName'=>'Synthetic.txt','aircraft_name'=>'Example']]]]);check($records[0]['filename']==='Synthetic.txt','Record normalization');
$rejected=false;try{dm_cloud_records(['list'=>[['filename'=>'../private.txt']]]);}catch(Throwable $e){$rejected=true;}check($rejected,'Unsafe filename');
$points=[['lat'=>48,'lng'=>16],['lat'=>48.001,'lng'=>16.002],['lat'=>48,'lng'=>16.004]];
$log=['summary'=>['name'=>'Other name','distanceMeters'=>400],'track'=>$points];$missions=[['id'=>'a','versionId'=>'v','name'=>'Mission','details'=>['points'=>$points,'distance'=>400]]];
$c=dm_log_candidates($log,$missions);check(dm_log_auto_candidate($log,$c,$missions)!==null,'Unique spatial match');
$missions[]=$missions[0];$missions[1]['id']='b';check(dm_log_auto_candidate($log,dm_log_candidates($log,$missions),$missions)===null,'Ambiguous route assigned');
$log['summary']['distanceMeters']=2000;check(dm_log_auto_candidate($log,$c,[$missions[0]])===null,'Different flight length assigned');
echo "PASS: DJI redirect/IP/filename rejection and unique/ambiguous route matching.\n";
