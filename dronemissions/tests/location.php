<?php
require __DIR__.'/../public/lib.php';require __DIR__.'/../public/location.php';
$raw=['reference_time'=>'2026-11-07T12:00:00Z','timestamps'=>['2026-11-07T13:00:00Z','2026-11-07T14:00:00Z'],'features'=>[['properties'=>['parameters'=>['2t'=>['data'=>[0,null]],'10u'=>['data'=>[3,null]],'10v'=>['data'=>[4,1]],'10fg'=>['data'=>[10,null]],'tp'=>['data'=>[0,null]],'tcc'=>['data'=>[50,null]]]]]]];
$result=dm_weather_normalize($raw);if($result['hours'][0]['wind']!==18.0||$result['hours'][0]['gust']!==36.0||$result['hours'][0]['temperature']!==0.0||$result['hours'][1]['wind']!==null||$result['hours'][1]['rain']!==null)throw new RuntimeException('Weather normalization failed');
foreach([[null,16],[90,16],[48,180],['invalid',16]] as [$lat,$lng]){try{dm_location_coords($lat,$lng);throw new LogicException('Expected rejection');}catch(InvalidArgumentException $e){}}
if(dm_location_coords('48.123456','16.123456')!==[48.1235,16.1235])throw new RuntimeException('Coordinate normalization failed');
echo "PASS: weather m/s to km/h, missing values preserved, coordinate bounds/rounding.\n";
