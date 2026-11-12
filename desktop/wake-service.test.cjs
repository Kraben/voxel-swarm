const {test}=require('node:test');const assert=require('node:assert/strict');const {createWakeService}=require('./wake-service.cjs');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(){
 const windows=[],states=[],tasks=new Map();let next=0,enabled=true,canListen=true,modelReady=true,chat=null,pendingFetch;
 class Window{
  constructor(options){this.options=options;this.events={};this.sent=[];this.destroyed=false;this.webContents={on(){},send:(...args)=>this.sent.push(args)};windows.push(this);}
  on(name,fn){this.events[name]=fn;}isDestroyed(){return this.destroyed;}destroy(){this.destroyed=true;this.events.closed?.();}
 }
 const timers={setTimeout(fn,ms){tasks.set(++next,{fn,ms});return next;},clearTimeout(id){tasks.delete(id);}};
 const service=createWakeService({BrowserWindow:Window,preferences:()=>({sandbox:true}),secureWindow:(win,route)=>{win.route=route;},baseURL:()=> 'http://127.0.0.1:8000',accessToken:()=> 'fixture',enabled:()=>enabled,canListen:()=>canListen,getChat:()=>chat,openChat:()=>{if(!chat)chat=new Window({chat:true});},publish:value=>states.push(value),timers,fetcher:async()=>{if(pendingFetch)await pendingFetch;return {ok:true,json:async()=>({ready:modelReady,mode:'local'})};}});
 return {service,windows,states,setEnabled:value=>{enabled=value;},setCanListen:value=>{canListen=value;},setModelReady:value=>{modelReady=value;},setPendingFetch:value=>{pendingFetch=value;},get chat(){return chat;},async run(ms=0){for(const [id,row] of [...tasks])if(row.ms<=ms){tasks.delete(id);row.fn();}await tick();}};
}
test('Oye Vox tiene su propia ventana invisible y entrega una sola vez al chat ya listo',async()=>{
 const f=fixture();try{
  f.service.sync(0);await f.run();const listener=f.service.window;assert.equal(listener.options.show,false);assert.equal(listener.route,'/static/wake-listener.html');assert.equal(f.chat,null);
  f.service.onPhase('armed');f.service.onPhase('command');assert.ok(f.chat);
  assert.equal(f.service.command('abre Safari'),true);assert.equal(listener.destroyed,true);assert.equal(f.chat.sent.length,0);
  f.service.chatReady();assert.equal(f.chat.sent.length,1);assert.equal(f.chat.sent[0][0],'voxel:wake-command');assert.equal(f.chat.sent[0][1].text,'abre Safari');
  f.service.chatReady();assert.equal(f.chat.sent.length,1);f.service.finish(f.chat.sent[0][1].id);await f.run(500);assert.ok(f.service.window);
 }finally{f.service.dispose();}
});
test('silenciar, bloquear o tomar el micrófono destruye la captura independiente del chat',async()=>{
 const f=fixture();try{
  f.service.sync(0);await f.run();const first=f.service.window;
  f.setCanListen(false);f.service.sync();assert.equal(first.destroyed,true);assert.equal(f.service.window,null);
  f.setCanListen(true);f.service.sync(0);await f.run();assert.ok(f.service.window);
  f.setEnabled(false);f.service.sync(0);await f.run();assert.equal(f.service.window,null);assert.equal(f.service.status().phase,'off');
 }finally{f.service.dispose();}
});
test('sin modelo no abre el micrófono y un fallo requiere reintento explícito',async()=>{
 const f=fixture();try{
  f.setModelReady(false);f.service.sync(0);await f.run();assert.equal(f.windows.length,0);assert.equal(f.service.status().phase,'model');
  f.setModelReady(true);f.service.retry();await f.run();assert.ok(f.service.window);
  f.service.fail('No mic');assert.equal(f.service.window,null);f.service.sync(0);await f.run();assert.equal(f.service.window,null);
  f.service.retry();await f.run();assert.ok(f.service.window);
 }finally{f.service.dispose();}
});
test('un resultado de preparación tardío no reinicia la captura después de silenciar',async()=>{
 const f=fixture();try{
  let resolve;f.setPendingFetch(new Promise(done=>{resolve=done;}));f.service.sync(0);await f.run();f.setEnabled(false);f.service.sync(0);resolve();await f.run();assert.equal(f.service.window,null);assert.equal(f.windows.length,0);
 }finally{f.service.dispose();}
});
test('cerrar el chat no desactiva el modo de espera y comandos cancelados no se entregan',async()=>{
 const f=fixture();try{
  f.service.sync(0);await f.run();f.service.onPhase('command');f.service.command('abre Notas');
  f.service.chatClosed();f.service.chatReady();assert.equal(f.chat.sent.length,0);await f.run(500);assert.ok(f.service.window);
 }finally{f.service.dispose();}
});
