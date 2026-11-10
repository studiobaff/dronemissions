'use strict';
/* Session-only display selection. It never changes project membership or access. */
class DmMissionSelection {
 constructor(){this.scopes=new Map();}
 explicit(scope){return this.scopes.has(scope);}
 rows(scope,rows){const ids=this.scopes.get(scope);return ids?rows.filter(m=>ids.has(m.id)):rows.slice();}
 all(scope){this.scopes.delete(scope);}
 only(scope,ids){this.scopes.set(scope,new Set(ids));}
 toggle(scope,id,on,rows){const ids=this.scopes.get(scope)??new Set(rows.map(m=>m.id));if(on)ids.add(id);else ids.delete(id);this.scopes.set(scope,ids);}
}
if(typeof module!=='undefined')module.exports={DmMissionSelection};
