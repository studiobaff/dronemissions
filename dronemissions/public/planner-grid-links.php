<?php
declare(strict_types=1);

// Check every interval between boundary intersections, including sub-metre notches.
function dm_grid_link_inside(array $a,array $b,array $rings): bool {
 $dx=$b[0]-$a[0];$dy=$b[1]-$a[1];$cuts=[0.0,1.0];
 foreach($rings as $r)for($i=1;$i<count($r);$i++){
  $c=$r[$i-1];$ex=$r[$i][0]-$c[0];$ey=$r[$i][1]-$c[1];$det=$dx*$ey-$dy*$ex;
  if(abs($det)<1e-12)continue;
  $cx=$c[0]-$a[0];$cy=$c[1]-$a[1];$t=($cx*$ey-$cy*$ex)/$det;$u=($cx*$dy-$cy*$dx)/$det;
  if($t>0&&$t<1&&$u>=-1e-9&&$u<=1+1e-9)$cuts[]=$t;
 }
 sort($cuts,SORT_NUMERIC);
 for($i=1;$i<count($cuts);$i++){
  $t=($cuts[$i-1]+$cuts[$i])/2;
  if(!dm_plan_inside([$a[0]+$dx*$t,$a[1]+$dy*$t],$rings))return false;
 }
 return dm_plan_inside($a,$rings)&&dm_plan_inside($b,$rings);
}

// Adjacent lane endpoints lie on the outer boundary. Follow either boundary
// direction around a concavity, choosing the shorter verified in-polygon path.
// Holes and cross-grid passes remain explicit breaks; never erase them here.
function dm_grid_boundary_link(array $a,array $b,array $ring): ?array {
 $vertices=array_slice($ring,0,-1);$n=count($vertices);
 $edge=function($p)use($ring,$n){$best=INF;$index=null;for($i=0;$i<$n;$i++){
  $v=$ring[$i];$w=$ring[$i+1];$dx=$w[0]-$v[0];$dy=$w[1]-$v[1];$d=$dx*$dx+$dy*$dy;if($d<1e-12)continue;
  $t=max(0,min(1,(($p[0]-$v[0])*$dx+($p[1]-$v[1])*$dy)/$d));$distance=hypot($p[0]-$v[0]-$t*$dx,$p[1]-$v[1]-$t*$dy);
  if($distance<$best){$best=$distance;$index=$i;}
 }return $best<=.0001?$index:null;};
 $start=$edge($a);$end=$edge($b);if($start===null||$end===null)return null;
 $best=null;$bestLength=INF;
 foreach([1,-1] as $direction){
  $corners=[];$i=$start;
  for($steps=0;$i!==$end&&$steps<$n;$steps++){
   $corners[]=$vertices[($i+($direction===1?1:0))%$n];$i=($i+$direction+$n)%$n;
  }
  $path=array_merge([$a],$corners,[$b]);$length=0;$valid=true;
  for($j=1;$j<count($path);$j++){
   if(!dm_grid_link_inside($path[$j-1],$path[$j],[$ring])){$valid=false;break;}
   $length+=hypot($path[$j][0]-$path[$j-1][0],$path[$j][1]-$path[$j-1][1]);
  }
  if($valid&&$length<$bestLength){$best=$corners;$bestLength=$length;}
 }
 return $best;
}
