/* Official Google Maps JS renderer; no tile scraping, proxying or image caching. */
(() => {
 let loading=null,failed=false;
 const active=new Set();
 function load(key){
  if(failed)return Promise.reject(Error('Google Maps konnte nicht autorisiert werden. API-Schlüssel, Domainfreigabe und Abrechnung prüfen.'));
  if(window.google?.maps?.Map)return Promise.resolve();
  if(loading)return loading;
  loading=new Promise((resolve,reject)=>{
   const script=document.createElement('script');let timer;
   const fail=()=>{failed=true;clearTimeout(timer);reject(Error('Google Maps konnte nicht geladen werden. API-Schlüssel und Verbindung prüfen.'));};
   window.dmGoogleReady=()=>{clearTimeout(timer);resolve();};
   window.gm_authFailure=()=>{fail();for(const layer of active)layer.fail();};
   script.nonce=document.querySelector('script[nonce]')?.nonce||'';
   script.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key,loading:'async',callback:'dmGoogleReady',v:'quarterly',language:'de',region:'AT',auth_referrer_policy:'origin'});
   script.async=true;script.onerror=fail;timer=setTimeout(fail,20000);document.head.append(script);
  });return loading;
 }
 const GoogleLayer=L.Layer.extend({
  initialize(key,type){this.key=key;this.type=type;},
  onAdd(map){
   this.map=map;active.add(this);map.dmGoogleActive=true;map.getContainer().classList.add('dm-google-active');
   this.container=L.DomUtil.create('div','dm-google-map');map.getContainer().prepend(this.container);
   const container=this.container;
   load(this.key).then(()=>{
    if(this.map!==map||this.container!==container)return;
    const center=map.getCenter();this.googleMap=new google.maps.Map(container,{center:{lat:center.lat,lng:center.lng},zoom:map.getZoom(),mapTypeId:this.type,renderingType:google.maps.RenderingType.RASTER,tilt:0,heading:0,disableDefaultUI:true,gestureHandling:'none',keyboardShortcuts:false,clickableIcons:false});
    this.sync=()=>{if(!this.googleMap)return;const c=map.getCenter();google.maps.event.trigger(this.googleMap,'resize');this.googleMap.setCenter({lat:c.lat,lng:c.lng});this.googleMap.setZoom(map.getZoom());};
    map.on('move zoom resize',this.sync);this.sync();
   }).catch(()=>{if(this.map===map&&this.container===container)this.fail();});
  },
  fail(){if(this.map)this.map.fire('googlemaperror',{layer:this});},
  onRemove(map){active.delete(this);if(this.sync)map.off('move zoom resize',this.sync);if(this.googleMap)google.maps.event.clearInstanceListeners(this.googleMap);this.googleMap=null;this.container?.remove();this.container=null;this.map=null;map.dmGoogleActive=false;map.getContainer().classList.remove('dm-google-active');}
 });
 window.dmGoogleLayers=key=>key?{'Google · Karte':new GoogleLayer(key,'roadmap'),'Google · Satellit':new GoogleLayer(key,'satellite'),'Google · Satellit mit Beschriftung':new GoogleLayer(key,'hybrid')}:{};
})();
