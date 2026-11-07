<?php
require __DIR__.'/../public/lib.php';require __DIR__.'/../public/address.php';
$features=[['properties'=>['countrycode'=>'AT','name'=>'Demo <Test>','street'=>'Teststraße','housenumber'=>'10','city'=>'Wien'],'geometry'=>['type'=>'Point','coordinates'=>[16.37,48.2]]],['properties'=>['countrycode'=>'DE','name'=>'Outside'],'geometry'=>['type'=>'Point','coordinates'=>[13,52]]],['properties'=>['countrycode'=>'AT','name'=>'Invalid'],'geometry'=>['type'=>'Point','coordinates'=>[200,48]]]];
$result=dm_address_results(['features'=>$features]);if(count($result)!==1||$result[0]['lat']!==48.2||!str_contains($result[0]['label'],'Teststraße 10'))throw new RuntimeException('Address normalization failed');
try{dm_address('ab','https://photon.komoot.io/api/');throw new LogicException('Expected rejection');}catch(InvalidArgumentException $e){}
echo "PASS: Austrian address result normalization, foreign/invalid-coordinate filtering, short query rejection.\n";
