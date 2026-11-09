<?php
declare(strict_types=1);
/* Hovering photo sequences: explicit approach (WP1) and capture (WP2), never a ground takeoff point. */
function dm_plan_panorama(array $in, ?callable $elevations): array {
 $type=$in['type'];$p=$in['params']??[];$g=$in['geometry']??[];
 if(($g['type']??'')!=='LineString'||count($g['coordinates']??[])!==2)throw new InvalidArgumentException('Panorama: genau zwei Punkte zeichnen – zuerst Anflugpunkt, dann Aufnahmepunkt.');
 if(($p['terrainMode']??'off')!=='off')throw new InvalidArgumentException('Panorama: Höhen relativ Start wählen. DEM-Anflug kann separat als Linienflug geplant werden.');
 $overlap=dm_pnum($p,'panoOverlap',10,80,30);$pitch=dm_pnum($p,'panoPitch',-60,30,0);$upper=dm_pnum($p,'panoUpperPitch',0,30,20);
 $base=$in;$base['type']='line';$base['params']=array_replace($p,['captureMode'=>'photo','spacingMode'=>'distance','photoDistance'=>500,'trackDistance'=>13,'pitchMode'=>'auto','entryEnabled'=>false,'photoLimit'=>200,'sectionOverlap'=>0]);
 $plan=dm_plan_build($base,$elevations);$camera=dm_plan_camera($in,1);$diagonal=tan(deg2rad($camera['fov'])/2);$ratio=hypot($camera['w'],$camera['h']);
 $hfov=rad2deg(2*atan($diagonal*$camera['w']/$ratio));$vfov=rad2deg(2*atan($diagonal*$camera['h']/$ratio));$cols=max(3,(int)ceil(360/($hfov*(1-$overlap/100))));
 $pitches=[$pitch];if($type==='sphere'){$count=max(1,(int)ceil(($upper+90)/($vfov*(1-$overlap/100))));$pitches=[];for($i=0;$i<$count;$i++)$pitches[]=$upper-($upper+90)*$i/$count;$pitches[]=-90.0;}
 $sequence=[];$bearing=dm_pnum($p,'bearing',-180,360,0);foreach($pitches as $row=>$tilt){$n=$tilt===-90.0?1:$cols;for($i=0;$i<$n;$i++)$sequence[]=['yaw'=>fmod($bearing+$i*360/$n+540,360)-180,'pitch'=>$tilt];}
 if(count($sequence)>200)throw new InvalidArgumentException('Mehr als 200 Panoramafotos. Überlappung reduzieren oder Kamerabildfeld prüfen.');
 $points=$plan['points'];if(count($points)>200)throw new InvalidArgumentException('Panorama-Anflug enthält mehr als 200 Flugpunkte. Anflug verkürzen oder Geländestützpunkte vergrößern.');
 foreach($points as &$pt){$pt['capture']=false;$pt['yaw']=$sequence[0]['yaw'];$pt['pitch']=$sequence[0]['pitch'];$pt['poi']=null;}unset($pt);
 $points[count($points)-1]['capture']=true;$points[count($points)-1]['panorama']=$sequence;
 // Without DEM only the two explicitly chosen endpoints are needed.
 if(!$plan['terrain'])$points=[$points[0],$points[count($points)-1]];
 $count=count($sequence);$pause=$plan['params']['photoPause'];$photoSeconds=$count*($pause+3)+count($pitches)*24;
 $seconds=$plan['summary']['distance']/$plan['params']['speed']+$photoSeconds;
 $plan['type']=$type;$plan['params']=array_replace($plan['params'],['captureMode'=>$type,'panoOverlap'=>$overlap,'panoPitch'=>$pitch,'panoUpperPitch'=>$upper]);
 $plan['points']=$points;$plan['parts']=[$points];$plan['sections']=[['photos'=>$count,'waypoints'=>count($points),'distance'=>$plan['summary']['distance'],'seconds'=>round($seconds)]];
 $plan['summary']=array_replace($plan['summary'],['photos'=>$count,'uniquePhotos'=>$count,'waypoints'=>count($points),'parts'=>1,'seconds'=>round($seconds),'rows'=>count($pitches)]);
 $plan['panorama']=['horizontalFov'=>$hfov,'verticalFov'=>$vfov,'columns'=>$cols,'pitches'=>$pitches,'photos'=>$count,'overlap'=>$overlap,'upperCoverage'=>min(90,$pitches[0]+$vfov/2),'zenithGap'=>$type==='sphere'?max(0,90-$upper-$vfov/2):null];
 $plan['generatorVersion']='0.6.0';$plan['routeSha256']=hash('sha256',json_encode(['points'=>$points,'params'=>$plan['params']],JSON_THROW_ON_ERROR));
 $plan['notes']=['Anflugpunkt zuerst, Aufnahmepunkt zuletzt. Am Aufnahmepunkt schwebt die Drohne und dreht für jede Aufnahme. Kein automatischer Start vom Boden. Höhen relativ zum tatsächlichen Startpunkt.',
 'Export: einzelne Fotos mit rotateYaw, gimbalRotate und Pausen. Bilder anschließend extern zum Panorama zusammensetzen. Kein gerätespezifisches panoShot. Geräte-/Firmwareannahme vor dem Flug prüfen.',
 'Zeit enthält geschätzte Dreh-/Fotopausen und Anflugstrecke; Wind, Beschleunigung, Rückflug und Akkureserve sind nicht enthalten.'];
 if($type==='sphere')$plan['notes'][]='Kugelpanorama: mehrere 360°-Reihen bis senkrecht nach unten. Der Zenit bleibt bei dieser Kameraneigung um '.round($plan['panorama']['zenithGap'],1).'° offen und muss beim Zusammenfügen ergänzt werden. Obere Neigung an der eingesetzten Kamera prüfen.';
 if($plan['terrain'])$plan['notes']=array_merge($plan['notes'],['Anflug folgt dem DEM; Höhen sind relativ zum gewählten Start. Bäume und Bauwerke fehlen im DEM.']);
 return $plan;
}
