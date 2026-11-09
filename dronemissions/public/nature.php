<?php
declare(strict_types=1);
require_once __DIR__.'/location.php';
const DM_NATURE_LAYERS=['NP'=>3,'NSG'=>5,'N2000'=>4,'PARK'=>9,'BIO'=>6,'LAND'=>7,'PART'=>8,'RAMSAR'=>18,'UNESCO'=>19,'OTHER'=>10];
function dm_nature_bbox(mixed $bbox): array {
 if(!is_array($bbox)||count($bbox)!==4||!array_is_list($bbox))throw new InvalidArgumentException('Kartenausschnitt fehlt.');foreach($bbox as $v)if(!is_numeric($v)||!is_finite((float)$v))throw new InvalidArgumentException('Kartenausschnitt ungültig.');
 [$w,$s,$e,$n]=array_map('floatval',$bbox);if($w>=$e||$s>=$n||$w<9.3||$e>17.4||$s<46.2||$n>49.2||($e-$w)*($n-$s)>2)throw new InvalidArgumentException('Für Schutzgebiete bitte näher an Österreich heranzoomen.');return [$w,$s,$e,$n];
}
function dm_nature(string $kind,mixed $bbox): array {
 if(!isset(DM_NATURE_LAYERS[$kind]))throw new InvalidArgumentException('Unbekannte Schutzgebietskategorie.');[$w,$s,$e,$n]=dm_nature_bbox($bbox);
 return dm_location_cache('nature',$kind.'|'.implode(',',[$w,$s,$e,$n]),604800,function()use($kind,$w,$s,$e,$n){
  $url='https://services7.arcgis.com/JhrnFQUbVgiJfOG5/ArcGIS/rest/services/SG_AT_2025_v_April/FeatureServer/'.DM_NATURE_LAYERS[$kind].'/query';$features=[];$more=false;
  for($offset=0;$offset<1200;$offset+=300){$q=['f'=>'geojson','where'=>'1=1','geometry'=>json_encode(['xmin'=>$w,'ymin'=>$s,'xmax'=>$e,'ymax'=>$n,'spatialReference'=>['wkid'=>4326]]),'geometryType'=>'esriGeometryEnvelope','inSR'=>4326,'outSR'=>4326,'spatialRel'=>'esriSpatialRelIntersects','outFields'=>'fid,SG_NAME,KAT,BL,BEZIRK,Flache_ha','returnGeometry'=>'true','geometryPrecision'=>6,'resultOffset'=>$offset,'resultRecordCount'=>300,'orderByFields'=>'fid'];
   $d=json_decode(dm_zone_fetch($url.'?'.http_build_query($q),16777216),true,64,JSON_THROW_ON_ERROR);if(($d['type']??'')!=='FeatureCollection'||!is_array($d['features']??null))throw new RuntimeException('Schutzgebietsquelle nicht verfügbar.');
   foreach($d['features'] as $f){if(!in_array($f['geometry']['type']??'', ['Polygon','MultiPolygon'],true))continue;$p=$f['properties']??[];$features[]=['type'=>'Feature','geometry'=>$f['geometry'],'properties'=>['name'=>(string)($p['SG_NAME']??'Schutzgebiet'),'category'=>$kind,'designation'=>(string)($p['KAT']??''),'state'=>(string)($p['BL']??''),'district'=>(string)($p['BEZIRK']??''),'hectares'=>is_numeric($p['Flache_ha']??null)?(float)$p['Flache_ha']:null]];}
   $more=(bool)($d['properties']['exceededTransferLimit']??$d['exceededTransferLimit']??false);if(!$more&&count($d['features'])<300)break;if(count($d['features'])===0){$more=false;break;}
  }
  return ['type'=>'FeatureCollection','features'=>$features,'incomplete'=>$more,'source'=>'Umweltbundesamt / INSPIRE-Dienste der Bundesländer','dataYear'=>2025,'sourceURL'=>'https://www.data.gv.at/katalog/datasets/106743cf-ea66-479a-9c55-08197b707aa8'];
 });
}
