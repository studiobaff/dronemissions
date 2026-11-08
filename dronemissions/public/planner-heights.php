<?php
declare(strict_types=1);
/* Imported waypoints are reference positions, not a measured obstacle surface. */
function dm_plan_height_import(string $path,string $name): array {
 $inspected=dm_inspect($path); // Shared ZIP/XML size, path and entity limits.
 $z=new ZipArchive();$z->open($path);try{$xml=dm_xml($z->getFromName('wpmz/waylines.wpml'));}finally{$z->close();}
 $points=[];$leg=-1;
 foreach($xml->xpath('//*[local-name()="Folder"]') as $folder){
  $marks=$folder->xpath('./*[local-name()="Placemark"]');if(!$marks)continue;$leg++;
  $modes=$folder->xpath('./*[local-name()="executeHeightMode"]');
  if(count($modes)!==1||trim((string)$modes[0])!=='relativeToStartPoint')throw new InvalidArgumentException('Höhenreferenzen benötigen DJI-Wegpunkte relativ zum Startpunkt. Fehlende, absolute oder gemischte Höhenmodi werden nicht umgerechnet.');
  foreach($marks as $m){
   $coords=dm_value($m,'coordinates');$c=explode(',',trim($coords??''));$height=dm_value($m,'executeHeight');
   $lat=dm_num($c[1]??null);$lng=dm_num($c[0]??null);$h=dm_num($height);
   if(count($c)<2||$lat===null||$lng===null||abs($lat)>80||abs($lng)>180||$h===null||$h< -500||$h>9000)throw new InvalidArgumentException('Jeder Höhenpunkt braucht gültige Koordinaten und eine explizite endliche Höhe.');
   $points[]=['lat'=>$lat,'lng'=>$lng,'height'=>$h,'selected'=>true,'leg'=>$leg];if(count($points)>1000)throw new InvalidArgumentException('Maximal 1000 Höhenreferenzpunkte.');
  }
 }
 if(!$points||count($points)!==$inspected['count'])throw new InvalidArgumentException('Höhenpunkte konnten nicht vollständig gelesen werden.');
 return ['name'=>dm_text($name,200),'sha256'=>hash_file('sha256',$path),'heightMode'=>'relativeToStartPoint','points'=>$points,'enabled'=>false,'datum'=>'','datumOffset'=>0,'margin'=>10];
}
function dm_plan_height_reference(mixed $raw): ?array {
 if($raw===null)return null;if(!is_array($raw))throw new InvalidArgumentException('Höhenreferenzen prüfen.');
 if(($raw['heightMode']??'')!=='relativeToStartPoint')throw new InvalidArgumentException('Höhenreferenzen benötigen relativen Startbezug.');
 $sha=$raw['sha256']??'';if(!is_string($sha)||!preg_match('/^[a-f0-9]{64}$/D',$sha))throw new InvalidArgumentException('Quellprüfsumme der Höhenreferenzen fehlt.');
 $pts=$raw['points']??null;if(!is_array($pts)||!array_is_list($pts)||count($pts)<1||count($pts)>1000)throw new InvalidArgumentException('1 bis 1000 Höhenpunkte erforderlich.');
 $points=[];foreach($pts as $p){if(!is_array($p)||!is_bool($p['selected']??null))throw new InvalidArgumentException('Höhenpunktauswahl prüfen.');$points[]=['lat'=>dm_pnum($p,'lat',-80,80),'lng'=>dm_pnum($p,'lng',-180,180),'height'=>dm_pnum($p,'height',-500,9000),'selected'=>$p['selected'],'leg'=>(int)dm_pnum($p,'leg',0,999,0)];}
 $datum=$raw['datum']??'';if(!in_array($datum,['','sameStart','offset'],true))throw new InvalidArgumentException('Startbezug wählen.');
 if(!is_bool($raw['enabled']??null))throw new InvalidArgumentException('Höhenreferenz aktivieren oder deaktivieren.');
 $r=['name'=>dm_text($raw['name']??'Höhenreferenz',200),'sha256'=>$sha,'heightMode'=>'relativeToStartPoint','points'=>$points,'enabled'=>$raw['enabled'],'datum'=>$datum,'datumOffset'=>dm_pnum($raw,'datumOffset',-9000,9000,0),'margin'=>dm_pnum($raw,'margin',0,200,10)];
 if($r['enabled']&&($datum===''||!array_filter($points,fn($p)=>$p['selected'])))throw new InvalidArgumentException('Höhenreferenz: mindestens einen Punkt auswählen und Startbezug bestätigen.');
 return $r;
}
function dm_plan_height_floor(?array $r): ?array {
 if(!$r||!$r['enabled'])return null;$points=array_values(array_filter($r['points'],fn($p)=>$p['selected']));$offset=$r['datum']==='offset'?$r['datumOffset']:0;
 $highest=max(array_column($points,'height'))+$offset;$minimum=$highest+$r['margin'];
 if($minimum<1||$minimum>500)throw new InvalidArgumentException('Abgeleitete Mindesthöhe liegt außerhalb 1–500 m relativ Start. Höhenbezug und Abstand prüfen.');
 return ['minimum'=>$minimum,'highest'=>$highest,'margin'=>$r['margin'],'offset'=>$offset,'count'=>count($points)];
}
