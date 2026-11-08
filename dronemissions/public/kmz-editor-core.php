<?php
declare(strict_types=1);
// Surgical waypoint edits: never rebuild actions or silently normalize an unfamiliar mission.
function dm_ke_children(DOMNode $node,string $name): array {
 $out=[];foreach($node->childNodes as $child)if($child instanceof DOMElement&&$child->localName===$name)$out[]=$child;return $out;
}
function dm_ke_node(DOMNode $node,string $name,bool $required=true): ?DOMElement {
 $a=dm_ke_children($node,$name);if(count($a)>1||($required&&!$a))throw new InvalidArgumentException('KMZ-Editor: Feld '.$name.' fehlt oder ist mehrdeutig.');return $a[0]??null;
}
function dm_ke_text(DOMNode $node,string $name,bool $required=true): ?string {return ($n=dm_ke_node($node,$name,$required))?trim($n->textContent):null;}
function dm_ke_number(mixed $v,float $min,float $max): float {
 if(!is_int($v)&&!is_float($v)&&!is_string($v))throw new InvalidArgumentException('Ungültiger Zahlenwert.');
 if(!is_numeric($v)||!is_finite((float)$v)||(float)$v<$min||(float)$v>$max)throw new InvalidArgumentException('Koordinate oder Höhe außerhalb des erlaubten Bereichs.');return (float)$v;
}
function dm_ke_xml(string $raw): DOMDocument {
 dm_xml($raw);$doc=new DOMDocument();$doc->preserveWhiteSpace=true;if(!$doc->loadXML($raw,LIBXML_NONET))throw new InvalidArgumentException('Ungültiges XML.');return $doc;
}
function dm_ke_marks(DOMElement $folder): array {
 $marks=dm_ke_children($folder,'Placemark');if(count($marks)<2||count($marks)>2000)throw new InvalidArgumentException('KMZ-Editor unterstützt 2 bis 2000 Wegpunkte.');
 foreach($marks as $i=>$p){if(dm_ke_text($p,'index')!==(string)$i)throw new InvalidArgumentException('Wegpunktnummern müssen eindeutig und fortlaufend ab 0 sein; Original zuerst prüfen.');}
 return $marks;
}
function dm_ke_coords(DOMElement $p): array {
 $n=dm_ke_node(dm_ke_node($p,'Point'),'coordinates');$c=explode(',',trim($n->textContent));if(count($c)<2||count($c)>3)throw new InvalidArgumentException('Wegpunktkoordinaten nicht eindeutig.');
 if(isset($c[2])&&dm_ke_number($c[2],-10000,100000)!==0.0)throw new InvalidArgumentException('Zusätzliche KML-Koordinatenhöhe wird noch nicht bearbeitet.');
 return ['lng'=>dm_ke_number($c[0],-180,180),'lat'=>dm_ke_number($c[1],-85,85)];
}
function dm_ke_load(string $path): array {
 $details=dm_inspect($path);$z=new ZipArchive();$z->open($path);
 try{
  $seen=[];for($i=0;$i<$z->numFiles;$i++){$name=$z->getNameIndex($i);if(isset($seen[$name]))throw new InvalidArgumentException('Doppelte Dateinamen in KMZ.');$seen[$name]=true;}
  $route=dm_ke_xml($z->getFromName('wpmz/waylines.wpml'));$template=dm_ke_xml($z->getFromName('wpmz/template.kml'));
 }finally{$z->close();}
 $folders=(new DOMXPath($route))->query('//*[local-name()="Folder"]');if($folders->length!==1)throw new InvalidArgumentException('KMZ-Editor unterstützt zunächst genau eine Flugroute.');$folder=$folders->item(0);
 $mode=dm_ke_text($folder,'executeHeightMode');if(!in_array($mode,['relativeToStartPoint','WGS84'],true))throw new InvalidArgumentException('Dieser Höhenbezug ist im KMZ-Editor noch nicht unterstützt.');
 $marks=dm_ke_marks($folder);$points=[];foreach($marks as $i=>$p){$points[]=dm_ke_coords($p)+['index'=>$i,'height'=>dm_ke_number(dm_ke_text($p,'executeHeight'),-1000,10000)];}
 $tm=[];$tf=null;$xp=new DOMXPath($template);$all=$xp->query('//*[local-name()="Placemark"]');
 if($all->length){
  $fs=$xp->query('//*[local-name()="Folder"]');if($fs->length!==1)throw new InvalidArgumentException('Vorlage lässt sich nicht eindeutig der Flugroute zuordnen.');$tf=$fs->item(0);
  if(dm_ke_text($tf,'templateType')!=='waypoint')throw new InvalidArgumentException('Nur Wegpunktvorlagen sind editierbar, keine Mapping-Templates.');
  if(dm_ke_text($tf,'templateId')!==dm_ke_text($folder,'templateId'))throw new InvalidArgumentException('Vorlagenkennung und Route stimmen nicht überein.');
  $cs=dm_ke_node($tf,'waylineCoordinateSysParam');if(dm_ke_text($cs,'coordinateMode')!=='WGS84'||dm_ke_text($cs,'heightMode')!==$mode)throw new InvalidArgumentException('Vorlage und Route verwenden unterschiedliche Koordinaten-/Höhenbezüge.');
  $tm=dm_ke_marks($tf);if(count($tm)!==count($marks))throw new InvalidArgumentException('Vorlage und Route haben unterschiedliche Wegpunkte.');
  foreach($tm as $i=>$p){$c=dm_ke_coords($p);if(abs($c['lat']-$points[$i]['lat'])>1e-7||abs($c['lng']-$points[$i]['lng'])>1e-7)throw new InvalidArgumentException('Vorlage und Route enthalten abweichende Positionen.');
   $global=dm_ke_text($p,'useGlobalHeight',false);if($global!==null&&!in_array($global,['0','1'],true))throw new InvalidArgumentException('Unbekannte globale Höheneinstellung.');
   $h=dm_ke_number($global==='1'?dm_ke_text($tf,'globalHeight'):dm_ke_text($p,'height'),-1000,10000);
   if(abs($h-$points[$i]['height'])>.01)throw new InvalidArgumentException('Vorlage und Route enthalten abweichende Höhen.');
   if($e=dm_ke_node($p,'ellipsoidHeight',false))dm_ke_number($e->textContent,-1000,10000);
  }
 }elseif($xp->query('//*[local-name()="templateType"]')->length){throw new InvalidArgumentException('Leere oder generierte Vorlage wird nicht bearbeitet.');}
 return compact('details','route','template','folder','marks','tm','tf','points','mode');
}
function dm_ke_value(DOMElement $parent,string $name,string $value,?DOMElement $namespaceSource=null): void {
 $node=dm_ke_node($parent,$name,false);if(!$node){$source=$namespaceSource??dm_ke_node($parent,'index');$node=$parent->ownerDocument->createElementNS($source->namespaceURI,($source->prefix?$source->prefix.':':'').$name);$parent->appendChild($node);}$node->textContent=$value;
}
function dm_ke_position(DOMElement $p,array $point): void {
 $n=dm_ke_node(dm_ke_node($p,'Point'),'coordinates');$old=explode(',',trim($n->textContent));$n->textContent=sprintf('%.9F,%.9F',$point['lng'],$point['lat']).(isset($old[2])?',0':'');
}
function dm_ke_edit(string $source,string $destination,array $changes,array $deletions=[],array $insertions=[]): array {
 $data=dm_ke_load($source);if((!$changes&&!$deletions&&!$insertions)||count($changes)>2000||count($deletions)>2000||count($insertions)>2000)throw new InvalidArgumentException('Mindestens eine Änderung erforderlich.');$changed=[];$seen=[];
 foreach($changes as $change){if(!is_array($change)||array_diff(array_keys($change),['index','lat','lng','height'])||!is_int($change['index']??null))throw new InvalidArgumentException('Ungültige Wegpunktänderung.');$i=$change['index'];if(!isset($data['points'][$i])||isset($seen[$i]))throw new InvalidArgumentException('Wegpunkt fehlt oder wurde doppelt übergeben.');$seen[$i]=true;$old=$data['points'][$i];$new=['index'=>$i];foreach(['lat'=>[-85,85],'lng'=>[-180,180],'height'=>[-1000,10000]] as $k=>$limits)$new[$k]=array_key_exists($k,$change)?dm_ke_number($change[$k],...$limits):$old[$k];
  if($old==$new)continue;$mark=$data['marks'][$i];if($new['lat']!==$old['lat']||$new['lng']!==$old['lng'])dm_ke_position($mark,$new);
  if($new['height']!==$old['height'])dm_ke_value($mark,'executeHeight',sprintf('%.3F',$new['height']));
  if($t=$data['tm'][$i]??null){if($new['lat']!==$old['lat']||$new['lng']!==$old['lng'])dm_ke_position($t,$new);if($new['height']!==$old['height']){
   dm_ke_value($t,'height',sprintf('%.3F',$new['height']));dm_ke_value($t,'useGlobalHeight','0');
   if($e=dm_ke_node($t,'ellipsoidHeight',false))$e->textContent=sprintf('%.3F',(float)$e->textContent+$new['height']-$old['height']);
  }}$data['points'][$i]=$new;$changed[]=['index'=>$i,'before'=>$old,'after'=>$new];
 }
 if($deletions||$insertions){
  if(!dm_ke_structure_allowed($data))throw new InvalidArgumentException('Einfügen/Löschen ist bei verknüpften oder unbekannten Aktionen gesperrt. Position und Höhe bleiben bearbeitbar.');
  $deleted=[];foreach($deletions as $i){if(!is_int($i)||!isset($data['points'][$i])||isset($deleted[$i])||isset($seen[$i]))throw new InvalidArgumentException('Ungültige oder zugleich bearbeitete Löschposition.');$deleted[$i]=true;}
  $added=[];foreach($insertions as $item){if(!is_array($item)||array_diff(array_keys($item),['after','lat','lng','height'])||!is_int($item['after']??null))throw new InvalidArgumentException('Ungültiger neuer Wegpunkt.');$after=$item['after'];if(!isset($data['points'][$after])||isset($deleted[$after])||isset($added[$after]))throw new InvalidArgumentException('Einfügeposition fehlt oder ist doppelt.');
   $added[$after]=['lat'=>dm_ke_number($item['lat']??null,-85,85),'lng'=>dm_ke_number($item['lng']??null,-180,180),'height'=>dm_ke_number($item['height']??null,-1000,10000)];
  }
  $count=count($data['points'])-count($deleted)+count($added);if($count<2||$count>2000)throw new InvalidArgumentException('Mindestens zwei, maximal 2000 Wegpunkte erforderlich.');
  $newPoints=[];$newMarks=[];$newTemplates=[];
  foreach($data['points'] as $i=>$point){
   if(isset($deleted[$i])){foreach([$data['marks'][$i],$data['tm'][$i]??null] as $node)if($node)$node->parentNode->removeChild($node);$changed[]=['index'=>$i,'deleted'=>$point];continue;}
   $index=count($newPoints);$point['index']=$index;$newPoints[]=$point;
   foreach([$data['marks'][$i],$data['tm'][$i]??null] as $node)if($node){dm_ke_reindex($node,$index);}
   $newMarks[]=$data['marks'][$i];if($data['tm'])$newTemplates[]=$data['tm'][$i];
   if(isset($added[$i])){$next=$added[$i]+['index'=>count($newPoints)];$newPoints[]=$next;
    foreach([$data['marks'][$i],$data['tm'][$i]??null] as $which=>$node)if($node){$clone=$node->cloneNode(true);foreach(dm_ke_children($clone,'actionGroup') as $group)$clone->removeChild($group);dm_ke_reindex($clone,$next['index']);dm_ke_position($clone,$next);
     dm_ke_value($clone,$which===0?'executeHeight':'height',sprintf('%.3F',$next['height']));
     if($which===1){dm_ke_value($clone,'useGlobalHeight','0');if($e=dm_ke_node($clone,'ellipsoidHeight',false))$e->textContent=sprintf('%.3F',(float)$e->textContent+$next['height']-$point['height']);}
     $node->parentNode->insertBefore($clone,$node->nextSibling);if($which===0)$newMarks[]=$clone;else $newTemplates[]=$clone;
    }$changed[]=['insertedAfter'=>$i,'after'=>$next,'actions'=>'none'];
   }
  }$data['points']=$newPoints;$data['marks']=$newMarks;$data['tm']=$newTemplates;
 }
 if(!$changed)throw new InvalidArgumentException('Keine Änderungen an Wegpunkten.');
 // Update derived route distance; duration remains an estimate with existing non-travel time retained.
 $dist=0;$travel=function($points){$sum=0;for($i=1;$i<count($points);$i++){if(!isset($points[$i]['speed'])||$points[$i]['speed']<=0)return null;$sum+=hypot(dm_distance($points[$i-1],$points[$i]),$points[$i]['height']-$points[$i-1]['height'])/$points[$i]['speed'];}return $sum;};
 foreach($data['points'] as $i=>&$p){$p['speed']=dm_num(dm_ke_text($data['marks'][$i],'waypointSpeed',false),dm_num(dm_ke_text($data['folder'],'autoFlightSpeed',false)));if($i)$dist+=hypot(dm_distance($data['points'][$i-1],$p),$p['height']-$data['points'][$i-1]['height']);}unset($p);
 $oldTravel=$travel($data['details']['points']);$newTravel=$travel($data['points']);
 if($n=dm_ke_node($data['folder'],'distance',false))$n->textContent=sprintf('%.3F',$dist);
 if(($n=dm_ke_node($data['folder'],'duration',false))&&is_numeric($n->textContent)&&$oldTravel!==null&&$newTravel!==null)$n->textContent=sprintf('%.3F',max(0,(float)$n->textContent-$oldTravel)+$newTravel);
 if(!copy($source,$destination))throw new RuntimeException('Übertragungskopie konnte nicht erstellt werden.');$z=new ZipArchive();if($z->open($destination)!==true)throw new RuntimeException('KMZ-Kopie nicht lesbar.');
 try{$z->addFromString('wpmz/waylines.wpml',$data['route']->saveXML());if($data['tm'])$z->addFromString('wpmz/template.kml',$data['template']->saveXML());}finally{if(!$z->close())throw new RuntimeException('KMZ nicht gespeichert.');}
 dm_ke_load($destination);return $changed;
}

function dm_ke_structure_allowed(array $data): bool {
 foreach(array_merge($data['marks'],$data['tm']) as $p){$i=dm_ke_text($p,'index');$xp=new DOMXPath($p->ownerDocument);
  foreach($xp->query('.//*[contains(local-name(),"Index")]', $p) as $node)if(!in_array($node->localName,['actionGroupStartIndex','actionGroupEndIndex','waypointHeadingPoiIndex','payloadPositionIndex'],true))return false;
  foreach(dm_ke_children($p,'actionGroup') as $group){if(dm_ke_text($group,'actionGroupStartIndex',false)!==$i||dm_ke_text($group,'actionGroupEndIndex',false)!==$i)return false;
   $trigger=dm_ke_node($group,'actionTrigger',false);if(!$trigger||dm_ke_text($trigger,'actionTriggerType',false)!=='reachPoint')return false;
   foreach($xp->query('.//*[local-name()="actionActuatorFunc"]',$group) as $f)if(!in_array(trim($f->textContent),['takePhoto','gimbalRotate','rotateYaw','hover','zoom','focus'],true))return false;
  }
 }
 return true;
}
function dm_ke_reindex(DOMElement $p,int $index): void {
 dm_ke_value($p,'index',(string)$index);foreach(dm_ke_children($p,'actionGroup') as $g){dm_ke_value($g,'actionGroupStartIndex',(string)$index);dm_ke_value($g,'actionGroupEndIndex',(string)$index);}
}

// Read-only inspector: preserve the original heading/gimbal/action semantics.
function dm_ke_point_info(array $data): array {
 $out=[];foreach($data['marks'] as $p){$xp=new DOMXPath($p->ownerDocument);$actions=[];
  foreach($xp->query('.//*[local-name()="actionActuatorFunc"]',$p) as $f)$actions[]=trim($f->textContent);
  $heading=dm_ke_node($p,'waypointHeadingParam',false);
  $out[]=['actions'=>$actions,'headingMode'=>$heading?dm_ke_text($heading,'waypointHeadingMode',false):null,'heading'=>$heading?dm_ke_text($heading,'waypointHeadingAngle',false):null,'gimbalPitch'=>dm_ke_text($p,'gimbalPitchAngle',false)];
 }return $out;
}
