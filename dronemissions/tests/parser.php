<?php
declare(strict_types=1);
require __DIR__.'/../public/lib.php';
function check(bool $ok,string $message): void {if(!$ok)throw new RuntimeException($message);}
function archive(array $entries): string {
 $p=tempnam(sys_get_temp_dir(),'dm-test-');$z=new ZipArchive();check($z->open($p,ZipArchive::OVERWRITE)===true,'zip open');foreach($entries as $name=>$body)$z->addFromString($name,$body);$z->close();return $p;
}
$template='<kml xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><wpml:droneEnumValue>99</wpml:droneEnumValue></Document></kml>';
function placemark(string $coords,string $height='50'): string {return '<Placemark><Point><coordinates>'.$coords.'</coordinates></Point><wpml:executeHeight>'.$height.'</wpml:executeHeight></Placemark>';}
$route='<kml xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Document><Folder><wpml:waylineId>0</wpml:waylineId><wpml:executeHeightMode>relativeToStartPoint</wpml:executeHeightMode>'.placemark('16,48').placemark('16.001,48','60').'</Folder><Folder><wpml:waylineId>0</wpml:waylineId><wpml:executeHeightMode>WGS84</wpml:executeHeightMode>'.placemark('17,49').placemark('17.001,49','').'</Folder></Document></kml>';
$valid=['wpmz/template.kml'=>$template,'wpmz/waylines.wpml'=>$route];
$p=archive($valid);try{$d=dm_inspect($p);check($d['count']===4&&count($d['routes'])===2,'multi route');check($d['distance']>100&&$d['distance']<200,'no distance across route boundaries');check($d['points'][3]['height']===null,'missing height');check($d['heightMode']==='mehrere Flugrouten','mixed height references');check(str_contains(dm_preview($d),'<svg'),'preview');}finally{unlink($p);}
$bad=[
 ['wpmz/template.kml'=>$template],
 $valid+['../escape'=>'bad'],
 ['wpmz/template.kml'=>'<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><kml>&xxe;</kml>','wpmz/waylines.wpml'=>$route],
 ['wpmz/template.kml'=>'<broken','wpmz/waylines.wpml'=>$route],
 ['wpmz/template.kml'=>$template,'wpmz/waylines.wpml'=>str_replace('16,48','181,91',$route)],
 ['wpmz/template.kml'=>$template,'wpmz/waylines.wpml'=>'<kml><Folder/></kml>']
];
foreach($bad as $i=>$entries){$p=archive($entries);try{$rejected=false;try{dm_inspect($p);}catch(InvalidArgumentException $e){$rejected=true;}check($rejected,'invalid fixture '.($i+1).' accepted');}finally{unlink($p);}}
$large=tempnam(sys_get_temp_dir(),'dm-large-');$p=archive($valid);try{$h=fopen($large,'wb');for($i=0;$i<65;$i++)fwrite($h,str_repeat('a',1048576));fclose($h);$z=new ZipArchive();$z->open($p);$z->addFile($large,'oversized.txt');$z->close();$rejected=false;try{dm_inspect($p);}catch(InvalidArgumentException $e){$rejected=true;}check($rejected,'expansion limit');}finally{unlink($p);unlink($large);}
$p=tempnam(sys_get_temp_dir(),'dm-csv-');try{file_put_contents($p,"latitude,longitude,altitude(m),heading(deg),speed(m/s),altitudemode\r\n48,16,50,90,5,0\r\n48.001,16.001,60,180,5,0\r\n");$d=dm_inspect_csv($p);check($d['count']===2&&$d['sourceFormat']==='litchi-csv','CSV parse');check($d['points'][1]['height']===60.0,'CSV height');check(dm_format($d)==='csv','CSV format');file_put_contents($p,"latitude,longitude,altitude(m),heading(deg)\n91,16,50,0\n");$rejected=false;try{dm_inspect_csv($p);}catch(InvalidArgumentException $e){$rejected=true;}check($rejected,'CSV invalid coordinates');file_put_contents($p,"wrong,header\n1,2\n");$rejected=false;try{dm_inspect_csv($p);}catch(InvalidArgumentException $e){$rejected=true;}check($rejected,'CSV invalid header');}finally{unlink($p);}
echo "PASS: CSV original parsing/validation; multiple routes, missing heights, mixed references, preview, missing entries, traversal, XML entities, malformed XML, invalid coordinates, empty routes, expansion limit.\n";

$poiHeading='<wpml:waypointHeadingParam><wpml:waypointHeadingMode>towardPOI</wpml:waypointHeadingMode><wpml:waypointPoiPoint>48.2,16.3,5</wpml:waypointPoiPoint><wpml:waypointHeadingPoiIndex>2</wpml:waypointHeadingPoiIndex></wpml:waypointHeadingParam>';
$poiRoute='<kml xmlns:wpml="http://www.dji.com/wpmz/1.0.6"><Folder>'.str_replace('</Placemark>',$poiHeading.'</Placemark>',placemark('16,48').placemark('16.001,48')).str_replace('</Placemark>',str_replace('towardPOI','followWayline',$poiHeading).'</Placemark>',placemark('16.002,48')).'</Folder></kml>';
$pois=dm_wpml_pois(dm_xml($poiRoute));check(count($pois)===1&&$pois[0]['lat']===48.2&&$pois[0]['lng']===16.3&&$pois[0]['label']==='POI 3'&&$pois[0]['waypoints']===[0,1],'active POI coordinate order and deduplication');
check(dm_wpml_pois(dm_xml(str_replace('48.2,16.3,5','91,16.3,5',$poiRoute)))===[],'invalid POI ignored');
echo "PASS: active WPML POIs, coordinate order, deduplication, optional waypoint indices, inactive and invalid POIs.\n";
