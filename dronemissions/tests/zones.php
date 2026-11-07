<?php
require __DIR__.'/../public/lib.php';require __DIR__.'/../public/zones.php';
function expect_zone(bool $ok): void {if(!$ok)throw new RuntimeException('Geozonen-Test fehlgeschlagen.');}
$rows='<table><tr><td><a href="/jart/prj3/ac/releases/de/upload/Dronespace/current.zip">Zonen</a></td><td>25.10.2026</td></tr><tr><td><a href="/jart/prj3/ac/releases/de/upload/Dronespace/future.zip">Zonen</a></td><td>01.12.2026</td></tr></table>';
expect_zone(dm_zone_release($rows,'2026-11-07')['validFrom']==='2026-10-25');
try{dm_zone_release('<html>unavailable</html>');throw new LogicException('Expected rejection');}catch(RuntimeException $e){expect_zone(!$e instanceof LogicException);}
$tmp=tempnam(sys_get_temp_dir(),'testzones-');$z=new ZipArchive();$z->open($tmp,ZipArchive::OVERWRITE);$z->addFromString('zones.json',"\xEF\xBB\xBF".json_encode([['name'=>'Synthetic Zone','geometry'=>[['horizontalProjection'=>['type'=>'Polygon','coordinates'=>[[[16,48],[17,48],[17,49],[16,48]]]]]]]]));$z->close();
try{expect_zone(dm_zone_decode(file_get_contents($tmp))[0]['name']==='Synthetic Zone');}finally{unlink($tmp);}
try{dm_zone_decode('not-a-zip');throw new LogicException('Expected rejection');}catch(RuntimeException $e){expect_zone(!$e instanceof LogicException);}
echo "PASS: current/future release selection, missing release rejection, BOM JSON ZIP parsing, invalid ZIP rejection.\n";
