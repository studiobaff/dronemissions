<?php
declare(strict_types=1);

/* Area of interest, not a flight fence. Separate recordings avoid target jumps between orbits. */
function dm_plan_circle_grid(array $in): array {
 $p=$in['params']??[];
 if(!is_array($p))throw new InvalidArgumentException('Planungsparameter fehlen.');
 $mode=$p['captureMode']??'video';if(!in_array($mode,['photo','video'],true))throw new InvalidArgumentException('Orbit Grid: Foto oder Video wählen.');$video=$mode==='video';
 $pathMode=$p['orbitPath']??'separate';if(!in_array($pathMode,['separate','continuous'],true))throw new InvalidArgumentException('Orbit Grid: Pfadmodus prüfen.');$continuous=$pathMode==='continuous';
 if(($p['terrainMode']??'off')!=='off'||($p['poiReference']??'relative')!=='relative')throw new InvalidArgumentException('Orbit Grid: Flug- und Zielhöhen relativ Start wählen. DEM-Anpassung wird hier noch nicht unterstützt.');
 if(($p['pitchMode']??'auto')!=='auto')throw new InvalidArgumentException('Orbit Grid benötigt automatische Ausrichtung zum jeweiligen Kreismittelpunkt.');
 if(($p['entryEnabled']??false)===true)throw new InvalidArgumentException('Orbit Grid: keinen Raster-Startort verwenden.');
 $geo=dm_plan_geometry($in['geometry']??[]);$g=$geo['geometry'];
 if($g['type']!=='Polygon'||count($g['coordinates'])!==1)throw new InvalidArgumentException('Orbit Grid benötigt ein Polygon ohne Löcher. Der Umriss ist das Aufnahmegebiet, keine Fluggrenze.');
 $radius=dm_pnum($p,'orbitRadius',5,200,30);
 $overlap=dm_pnum($p,'circleOverlap',0,80,50);
 $levels=dm_pnum($p,'orbitLevels',1,2,2);if(floor($levels)!==$levels)throw new InvalidArgumentException('Eine oder zwei Höhenebenen wählen.');
 $bottom=dm_pnum($p,'bottom',1,500,30);$top=$levels===2.0?dm_pnum($p,'top',$bottom+.5,500,60):$bottom;
 $target=dm_pnum($p,'targetHeight',-500,500,0)+dm_pnum($p,'poiOffset',-500,500,0);
 if($target>=$bottom)throw new InvalidArgumentException('Zielhöhe muss unter der unteren Flugbahn liegen.');
 $yawLimit=dm_pnum($p,'maxYawRate',1,20,6);$sampleFps=dm_pnum($p,'sampleFps',.2,10,2);
 $requestedSpeed=dm_pnum($p,'speed',.2,15,3);
 // Tangential velocity: cap heading rate and nominal centripetal acceleration (1 m/s²).
 $speed=min($requestedSpeed,deg2rad($yawLimit)*$radius,sqrt($radius));
 if($speed<.2)throw new InvalidArgumentException('Radius oder maximale Drehrate erhöhen: Sollgeschwindigkeit liegt unter 0,2 m/s.');
 $motion=$p['orbitMotion']??'smooth';if(!in_array($motion,['smooth','stop'],true))throw new InvalidArgumentException('Orbit-Flugmodus prüfen.');
 if(!$video)$motion='stop';
 $bearing=dm_pnum($p,'bearing',-180,360,0);$a=deg2rad($bearing);$s=sin($a);$c=cos($a);
 $uv=fn($q)=>[$q[0]*$c+$q[1]*$s,-$q[0]*$s+$q[1]*$c];
 $xy=fn($q)=>[$q[0]*$c-$q[1]*$s,$q[0]*$s+$q[1]*$c];
 $ring=array_map(fn($ll)=>$uv(($geo['project'])($ll)),$g['coordinates'][0]);
 $xs=array_column($ring,0);$ys=array_column($ring,1);$minX=min($xs);$minY=min($ys);$w=max($xs)-$minX;$h=max($ys)-$minY;
 $spacing=2*$radius*(1-$overlap/100);$nx=max(1,(int)ceil($w/$spacing));$ny=max(1,(int)ceil($h/$spacing));
 if($nx*$ny*$levels>100)throw new InvalidArgumentException('Mehr als 100 Orbitaufnahmen. Gebiet verkleinern, Radius erhöhen oder eine Höhenebene wählen.');
 $dx=$w/$nx;$dy=$h/$ny;$centers=[];
 for($row=0;$row<$ny;$row++)for($col=0;$col<$nx;$col++){
  $column=$row%2?$nx-1-$col:$col;$x=$minX+$column*$dx;$y=$minY+$row*$dy;
  $cell=[[$x,$y],[$x+$dx,$y],[$x+$dx,$y+$dy],[$x,$y+$dy],[$x,$y]];
  $hit=false;foreach($cell as $v)if(dm_plan_inside($v,[$ring])){$hit=true;break;}
  if(!$hit)foreach($ring as $v)if(dm_plan_inside($v,[$cell])){$hit=true;break;}
  if(!$hit)for($i=1;$i<count($ring);$i++)for($j=1;$j<count($cell);$j++)if(dm_plan_crosses($ring[$i-1],$ring[$i],$cell[$j-1],$cell[$j]))$hit=true;
  if($hit)$centers[]=($geo['unproject'])($xy([$x+$dx/2,$y+$dy/2]));
 }
 if(!$centers)throw new InvalidArgumentException('Keine Kreismittelpunkte im Aufnahmegebiet erzeugt.');
 $points=[];$parts=[];$sections=[];$seed=null;$orbitCount=0;$direction=$p['turnDirection']??'cw';
 $jobs=[];if($continuous){for($level=0;$level<(int)$levels;$level++)foreach($level%2?array_reverse($centers):$centers as $center)$jobs[]=[$center,$level];}else{foreach($centers as $center)for($level=0;$level<(int)$levels;$level++)$jobs[]=[$center,$level];}
 foreach($jobs as [$center,$level]){
  $input=$in;$input['type']='circle';$input['geometry']=['type'=>'Point','coordinates'=>$center];$input['heightReference']=null;
  $input['params']=array_replace($p,['captureMode'=>$mode,'height'=>$level?$top:$bottom,'bottom'=>$bottom,'top'=>$top,'radius'=>$radius,'standoff'=>$radius,'shape'=>'cylinder','spacingMode'=>'distance','photoDistance'=>$video?2*M_PI*$radius/72:dm_pnum($p,'photoDistance',.1,500,3),'trackDistance'=>13,'pitchMode'=>'auto','speed'=>$speed,'terrainMode'=>'off','poiReference'=>'relative','entryEnabled'=>false,'turnDirection'=>$direction]);
  $plan=dm_plan_build($input);$seed??=$plan;$orbitCount++;
  if($continuous&&$points){
   $last=$points[count($points)-1];$next=$plan['points'][0];$length=hypot(dm_distance($last,$next),$next['height']-$last['height']);$steps=max(1,(int)ceil($length/5));
   for($j=1;$j<$steps;$j++){$t=$j/$steps;$pt=$last;foreach(['lat','lng','height'] as $key)$pt[$key]=$last[$key]+($next[$key]-$last[$key])*$t;
    $pt['poi']=array_map(fn($a,$b)=>$a+($b-$a)*$t,$last['poi'],$next['poi']);$pt['pitch']=-rad2deg(atan2($pt['height']-$pt['poi'][2],max(.001,dm_distance($pt,['lat'=>$pt['poi'][0],'lng'=>$pt['poi'][1]]))));
    $pt['breakBefore']=false;$pt['capture']=false;$pt['connector']=true;$points[]=$pt;
   }
  }
  foreach($plan['points'] as $i=>$pt){$pt['breakBefore']=!$continuous&&$i===0&&count($points)>0;$pt['orbitIndex']=$orbitCount;$pt['level']=$level;$pt['speed']=$speed;$points[]=$pt;}
  foreach($plan['parts'] as $part){foreach($part as &$pt){$pt['orbitIndex']=$orbitCount;$pt['level']=$level;$pt['speed']=$speed;}unset($pt);$parts[]=$part;}
  array_push($sections,...$plan['sections']);
  if(count($points)>5000||count($parts)>100)throw new InvalidArgumentException('Orbit Grid überschreitet 5000 Wegpunkte oder 100 Abschnitte. Gebiet verkleinern.');
 }
 if($continuous){
  // Bound pitch/climb changes along connecting legs; yaw is continuous for equal entry angles.
  $maxClimb=dm_pnum($p,'maxClimbSpeed',.2,5,2);
  for($i=1;$i<count($points);$i++){$prev=$points[$i-1];$cur=$points[$i];$d=hypot(dm_distance($prev,$cur),$cur['height']-$prev['height']);if($d<1e-6)continue;
   $capSpeed=$speed;$dz=abs($cur['height']-$prev['height']);if($dz>0)$capSpeed=min($capSpeed,$maxClimb*$d/$dz);
   $yaw=abs(fmod($cur['yaw']-$prev['yaw']+540,360)-180);$pitch=abs($cur['pitch']-$prev['pitch']);$rotation=max($yaw,$pitch);if($rotation>0)$capSpeed=min($capSpeed,$yawLimit*$d/$rotation);
   if($capSpeed<.2)throw new InvalidArgumentException('Verbindungsweg benötigt weniger als 0,2 m/s. Radius, Höhen oder Drehrate anpassen.');
   $points[$i-1]['speed']=min($points[$i-1]['speed'],$capSpeed);$points[$i]['speed']=min($points[$i]['speed'],$capSpeed);
  }
  $parts=[];$chunk=[];$limit=$seed['params']['photoLimit'];$repeat=$seed['params']['sectionOverlap'];
  foreach($points as $pt){if(count($chunk)>=$limit){$parts[]=$chunk;$chunk=$repeat?array_slice($chunk,-$repeat):[];}$chunk[]=$pt;}if($chunk)$parts[]=$chunk;
  if(count($parts)>100)throw new InvalidArgumentException('Mehr als 100 Abschnitte. Orbit Grid verkleinern.');
 }
 $sections=[];$totalDistance=0;$totalSeconds=0;$photoCount=0;$maxStep=0;
 foreach($parts as $part){$d=0;$seconds=0;$photos=$video?0:count(array_filter($part,fn($pt)=>$pt['capture']??true));
  for($j=1;$j<count($part);$j++){$step=hypot(dm_distance($part[$j-1],$part[$j]),$part[$j]['height']-$part[$j-1]['height']);$d+=$step;$maxStep=max($maxStep,$step);$seconds+=$step/min($part[$j-1]['speed'],$part[$j]['speed']);}
  $seconds+=$photos*($seed['params']['photoPause']+2);$sections[]=['photos'=>$photos,'waypoints'=>count($part),'distance'=>round($d,1),'seconds'=>round($seconds)];$totalDistance+=$d;$totalSeconds+=$seconds;$photoCount+=$photos;
 }
 $refs=dm_plan_height_reference($in['heightReference']??null);$floor=dm_plan_height_floor($refs);
 if($floor){foreach($refs['points'] as $hp)if($hp['selected']&&dm_distance($hp,$points[0])>5000)throw new InvalidArgumentException('Höhenreferenz liegt mehr als 5 km vom Fluggebiet entfernt.');if($bottom<$floor['minimum']-1e-7)throw new InvalidArgumentException('Untere Flugbahn liegt unter der Mindesthöhe aus Höhenreferenzen.');}
 $out=$seed;$out['type']='circleGrid';$out['geometry']=$g;$out['points']=$points;$out['parts']=$parts;$out['sections']=$sections;$out['heightReference']=$refs;$out['heightFloor']=$floor;
 $out['params']=array_replace($seed['params'],['speed'=>$requestedSpeed,'bottom'=>$bottom,'top'=>$top,'orbitRadius'=>$radius,'circleOverlap'=>$overlap,'orbitLevels'=>$levels,'maxYawRate'=>$yawLimit,'sampleFps'=>$sampleFps,'orbitMotion'=>$motion,'orbitPath'=>$pathMode,'bearing'=>$bearing]);
 $s=&$out['summary'];$s['waypoints']=count($points);$s['parts']=count($parts);$s['videoSections']=$video?count($parts):0;$s['photos']=$photoCount;$s['uniquePhotos']=$video?0:count(array_filter($points,fn($pt)=>$pt['capture']??true));$s['maxWaypointStep']=round($maxStep,3);$s['distance']=round($totalDistance,1);$s['seconds']=round($totalSeconds);$s['rows']=$orbitCount;$s['minHeight']=$bottom;$s['maxHeight']=$top;$s['actualTrackSpacing']=round(max($dx,$dy),3);
 $out['circleGrid']=['centers'=>array_map(fn($ll)=>['lng'=>$ll[0],'lat'=>$ll[1]],$centers),'orbits'=>$orbitCount,'levels'=>(int)$levels,'radius'=>$radius,'centerSpacing'=>[round($dx,3),round($dy,3)],'effectiveSpeed'=>$speed,'yawRate'=>rad2deg($speed/$radius),'sampleFps'=>$sampleFps,'nominalViewStep'=>rad2deg($speed/$radius)/$sampleFps,'nominalSampleBaseline'=>$speed/$sampleFps,'motion'=>$motion,'path'=>$pathMode,'connectors'=>count(array_filter($points,fn($pt)=>$pt['connector']??false))];
 $out['notes']=[
  $continuous?'Orbit Grid: verbundener Pfad mit Übergängen zwischen Kreisen/Höhen. Video läuft auch über Verbindungen; Wegpunktlimits teilen die Aufnahme in Abschnitte. Verbindungen sind keine Hindernisumfahrung.':'Orbit Grid: jeder Kreis und jede Höhe separat. Keine exportierten Verbindungen. An-/Rückflüge fehlen in Strecke und Zeit.',
  'Der Polygonumriss ist das Aufnahmegebiet, keine Fluggrenze. Vollständige Kreise und Kurven liegen auch außerhalb. Polygonlöcher werden nicht unterstützt. Hindernisse und Randüberflug separat prüfen.',
  'Kreisüberlappung beschreibt nur die Geometrie der Orbitkreise, keine Bild- oder Oberflächenüberdeckung. Gemeinsame sichtbare Strukturen zwischen Kreisen und Höhen sind für die Rekonstruktion erforderlich.',
  'Geschwindigkeit auf '.round($speed,2).' m/s begrenzt: höchstens '.$yawLimit.'°/s Soll-Drehrate und nominal 1 m/s² Querbeschleunigung. Keine Garantie für den tatsächlichen Flugregler.',
  $motion==='smooth'?'Experimenteller Kurvenexport: innere Wegpunkte ohne geplanten Stopp, Abschnittsanfang/-ende mit Stopp. DJI-Fly-/Geräteannahme und tatsächliche POI-Verfolgung sind noch nicht geprüft.':'Kompatibilitätsmodus: Stopps an jedem Wegpunkt. Für gleichmäßige 3DGS-Videos nur eingeschränkt geeignet.',
  'Frame-Auswahl: '.$sampleFps.' Bilder/s ist eine spätere Extraktionsvorgabe, keine Kamera-Bildrate. Nominale Blickänderung '.round(rad2deg($speed/$radius)/$sampleFps,2).'° und Basislinie '.round($speed/$sampleFps,2).' m je ausgewähltem Bild bei Sollgeschwindigkeit. Stopps, Verdeckung und Oberflächenabstände sind darin nicht modelliert.',
  'Videoformat, tatsächliches FOV/Crop und Bildrate an der Kamera einstellen. Kurze Belichtung, konstante Belichtung/Weißabgleich und scharfe Einzelbilder prüfen. Untere Flächen können zusätzliche tiefere Ansichten benötigen.',
  'Alle Höhen relativ zum tatsächlichen Startpunkt. Keine DEM-Anpassung. Keine nachgewiesene 3DGS-Qualität oder Zeitersparnis.'];
 $out['generatorVersion']='0.6.1';$out['routeSha256']=hash('sha256',json_encode(['points'=>$points,'params'=>$out['params']],JSON_THROW_ON_ERROR));return $out;
}
