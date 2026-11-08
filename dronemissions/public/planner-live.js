/* Coalesce edits, serialize requests, and never apply a superseded route. */
class DmLivePreview {
 constructor({ready,request,apply,error,start,finish,delay=650}){Object.assign(this,{ready,request,apply,error,start,finish,delay});this.revision=0;this.pending=false;this.running=false;this.timer=null;}
 change(){this.revision++;this.pending=true;clearTimeout(this.timer);this.timer=setTimeout(()=>this.run(),this.delay);}
 flush(){this.pending=true;clearTimeout(this.timer);return this.run();}
 cancel(){this.revision++;this.pending=false;clearTimeout(this.timer);}
 async run(){if(this.running||!this.pending||!this.ready())return;this.pending=false;this.running=true;const revision=this.revision;try{this.start();const result=await this.request();if(revision===this.revision&&this.ready())this.apply(result);}catch(e){if(revision===this.revision&&this.ready())this.error(e);}finally{this.running=false;this.finish();if(this.pending){clearTimeout(this.timer);this.timer=setTimeout(()=>this.run(),this.delay);}}}
}
if(typeof module!=='undefined')module.exports=DmLivePreview;
