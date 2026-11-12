const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');const {randomUUID}=require('node:crypto');
const sessionModule=require('../static/voice-session.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function until(predicate){for(let n=0;n<100;n++){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,2));}throw Error('UI did not reach expected state');}
function fixture({chatResponse,lateTranscription=false,voiceInfo}={}){
 const nodes=new Map(),events={},captures=[],playbacks=[],requests=[];let confirms=0,closing,activePlayback,wakeCallback,wakeStatusCallback;const wakeAcks=[];
 class Element{
  constructor(){this.value='';this.textContent='';this.innerHTML='';this.children=[];this.dataset={};this.className='';this.attributes={};this.classList={contains:name=>this.className.split(' ').includes(name),add:(...names)=>{this.className+=' '+names.join(' ');},remove:(...names)=>{this.className=this.className.split(' ').filter(x=>!names.includes(x)).join(' ');},toggle:(name,value)=>{if(value)this.classList.add(name);else this.classList.remove(name);}};}
  setAttribute(name,value){this.attributes[name]=value;}
  addEventListener(){} append(...children){this.children.push(...children);} prepend(child){this.children.unshift(child);} replaceChildren(...children){this.children=children;} add(child){this.children.push(child);} querySelector(){return null;} remove(){} focus(){} showModal(){this.open=true;} close(){this.open=false;}
 }
 for(const id of fs.readFileSync(path.join(__dirname,'../static/compact-chat.html'),'utf8').matchAll(/id="([^"]+)"/g))nodes.set(id[1],new Element());
 const document={body:new Element(),documentElement:new Element(),getElementById:id=>nodes.get(id)||null,querySelectorAll:()=>[],createElement:()=>new Element(),querySelector:selector=>selector==='dialog[open]'?[...nodes.values()].find(n=>n.open):null};
 const window={addEventListener:(name,callback)=>{events[name]=callback;},confirm:()=>{confirms++;return true;},VoxelVoiceSession:{createConversation:options=>sessionModule.createConversation({...options,wait:()=>new Promise(resolve=>setTimeout(resolve,1))})},VoxelVoiceCapture:{captureTurn:({signal,onListening,pcm})=>new Promise((resolve,reject)=>{
  const capture={signal,pcm,live:true,finish:()=>{capture.live=false;signal.removeEventListener('abort',abort);resolve(new Blob(['fake voice'],{type:'audio/webm'}));}};
  const abort=()=>{capture.live=false;reject(signal.reason);};signal.addEventListener('abort',abort,{once:true});captures.push(capture);onListening(capture.finish);
 })},voxelDesktop:{platform:'darwin',onWakeCommand:fn=>{wakeCallback=fn;},onWakeStatus:fn=>{wakeStatusCallback=fn;},wakeDone:id=>wakeAcks.push(id),chatReady(){},saveSession(){},publishState(){},publishBusy(){},onSkin(){},onChatClosing(callback){closing=callback;},stopSpeech(){activePlayback?.({ok:false,cancelled:true});activePlayback=null;},speakNative:()=>new Promise(resolve=>{activePlayback=resolve;playbacks.push({finish:()=>{activePlayback=null;resolve({ok:true});}});})}};
 let finishTranscription;
 const context={window,document,location:{hash:'',pathname:'/static/compact-chat.html'},history:{replaceState(){}},localStorage:{getItem(){},setItem(){}},crypto:{randomUUID},URLSearchParams,AbortController,URL,Blob,setTimeout,clearTimeout,console,Option:Element,
 FileReader:class{readAsDataURL(){this.result='data:audio/webm;base64,YXVkaW8=';queueMicrotask(()=>this.onload());}},
 fetch:async(url,options)=>{
  requests.push({url,options});let data;
  if(url==='/api/status')data={conectado:true,microfono:true,voz:voiceInfo||{supported:true,provider:'Test'},modelos:[],modelo:'test',proveedor:'openai'};
  else if(url.startsWith('/api/history/'))data={turnos:[]};
  else if(url==='/api/voice/transcribe'){
   if(lateTranscription)await new Promise(resolve=>{finishTranscription=resolve;});
   data={texto:'Mi frase'};
  }else if(url==='/api/voice/local/install')data={mode:'local',supported:true,ready:true,provider:'Whisper local'};
  else if(url==='/chat')data=chatResponse||{respuesta:'Mi respuesta'};
  else throw Error('Unexpected endpoint '+url);
  return {ok:true,json:async()=>data};
 }};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8'),context);
 return {nodes,events,captures,playbacks,requests,wakeAcks,wake:payload=>wakeCallback(payload),wakeStatus:value=>wakeStatusCallback(value),get confirms(){return confirms;},close:()=>closing(),finishTranscription:()=>finishTranscription(),cleanup:()=>{events.beforeunload();vm.runInContext('clearTimeout(stateTimer)',context);}};
}
test('UI real: un permiso inicia dos turnos, espera el audio y cierra el micrófono al terminar',async()=>{
 const f=fixture();try{
  await tick();f.nodes.get('conversation-voice').onclick();assert.equal(f.confirms,1);assert.equal(f.captures.length,1);
  f.captures[0].finish();await until(()=>f.playbacks.length===1);
  assert.equal(f.captures[0].live,false);assert.equal(f.captures.length,1);assert.equal(f.nodes.get('voice-status').dataset.state,'replying');
  f.playbacks[0].finish();await until(()=>f.captures.length===2);
  f.captures[1].finish();await until(()=>f.playbacks.length===2);f.playbacks[1].finish();await until(()=>f.captures.length===3);
  f.nodes.get('conversation-voice').onclick();await tick();
  assert.equal(f.captures[2].live,false);assert.equal(f.confirms,1);assert.equal(f.requests.filter(r=>r.url==='/chat').length,2);assert.equal(f.nodes.get('voice-status').dataset.state,'off');
 }finally{f.cleanup();}
});
test('UI: cerrar durante transcripción impide enviar una frase tardía',async()=>{
 const f=fixture({lateTranscription:true});try{
  await tick();f.nodes.get('conversation-voice').onclick();f.captures[0].finish();await until(()=>f.requests.some(r=>r.url==='/api/voice/transcribe'));
  f.close();f.finishTranscription();await until(()=>f.nodes.get('voice-status').dataset.state==='off');
  assert.equal(f.requests.filter(r=>r.url==='/chat').length,0);assert.equal(f.captures.length,1);
 }finally{f.cleanup();}
});
test('UI: una skill con confirmación no se ejecuta por usar voz continua',async()=>{
 const f=fixture({chatResponse:{respuesta:'¿Abrir la app?',requiere_confirmacion:true,tool_request_id:'test-id'}});try{
  await tick();f.nodes.get('conversation-voice').onclick();f.captures[0].finish();await until(()=>f.nodes.get('skill-confirm').open);
  assert.equal(f.requests.filter(r=>r.url==='/chat').length,1);assert.equal(f.captures.length,1);
  f.nodes.get('conversation-voice').onclick();f.nodes.get('skill-accept').onclick();await until(()=>f.nodes.get('voice-status').dataset.state==='off');
  assert.equal(f.requests.filter(r=>r.url==='/chat').length,1);
 }finally{f.cleanup();}
});
test('UI: un borrador escrito durante el dictado se conserva y requiere revisión',async()=>{
 const f=fixture();try{
  await tick();f.nodes.get('conversation-voice').onclick();f.nodes.get('message').value='Borrador existente';f.captures[0].finish();
  await until(()=>f.nodes.get('voice-status').dataset.state==='off');
  assert.equal(f.nodes.get('message').value,'Borrador existente\nMi frase');assert.equal(f.requests.filter(r=>r.url==='/chat').length,0);
 }finally{f.cleanup();}
});

test('UI: Ollama usa captura WAV local y el mismo ciclo de conversación',async()=>{
 const f=fixture({voiceInfo:{mode:'local',supported:true,ready:true,provider:'Whisper local'}});try{
  await tick();assert.equal(f.nodes.get('local-voice-install').hidden,true);
  f.nodes.get('conversation-voice').onclick();assert.equal(f.captures[0].pcm,true);
  f.captures[0].finish();await until(()=>f.playbacks.length===1);f.playbacks[0].finish();await until(()=>f.captures.length===2);
  assert.equal(f.captures[1].pcm,true);assert.equal(f.confirms,1);f.nodes.get('conversation-voice').onclick();await tick();
 }finally{f.cleanup();}
});
test('UI: un modelo local ausente muestra la descarga e impide abrir el micrófono',async()=>{
 const f=fixture({voiceInfo:{mode:'local',supported:true,ready:false,provider:'Whisper local'}});try{
  await tick();assert.equal(f.nodes.get('local-voice').hidden,false);assert.equal(f.nodes.get('local-voice-install').hidden,false);
  f.nodes.get('conversation-voice').onclick();assert.equal(f.captures.length,0);assert.equal(f.confirms,0);assert.match(f.nodes.get('notice').textContent,/Descargar voz local/);
 }finally{f.cleanup();}
});

test('UI: la instalación del modelo local es explícita y actualiza la disponibilidad de voz',async()=>{
 const f=fixture({voiceInfo:{mode:'local',supported:true,ready:false,provider:'Whisper local'}});try{
  await tick();assert.equal(f.requests.filter(r=>r.url.includes('/local/install')).length,0);
  await f.nodes.get('local-voice-install').onclick();assert.equal(f.confirms,1);
  const installs=f.requests.filter(r=>r.url.includes('/local/install'));
  assert.equal(installs.length,1);assert.equal(JSON.parse(installs[0].options.body).consent,true);
  assert.equal(f.nodes.get('local-voice-install').hidden,true);
  f.nodes.get('conversation-voice').onclick();assert.equal(f.captures.length,1);assert.equal(f.captures[0].pcm,true);
  f.nodes.get('conversation-voice').onclick();await tick();
 }finally{f.cleanup();}
});

test('UI: un comando de Oye Vox fuerza respuesta hablada sin pedir clic al micrófono',async()=>{
 const f=fixture();try{
  await tick();const request=f.wake({id:'wake-1',text:'abre Safari'});await until(()=>f.playbacks.length===1);
  assert.equal(f.captures.length,0);assert.equal(f.confirms,0);assert.equal(f.wakeAcks.length,0);
  f.playbacks[0].finish();await request;assert.deepEqual(f.wakeAcks,['wake-1']);assert.equal(f.requests.filter(r=>r.url==='/chat').length,1);
 }finally{f.cleanup();}
});
test('UI: Oye Vox no sustituye un borrador ni cambia la transcripción cloud del modo manual',async()=>{
 const f=fixture({voiceInfo:{mode:'cloud',provider:'Test',supported:true,ready:true}});try{
  await tick();f.wakeStatus({enabled:true,phase:'armed',label:'Oye Vox',model:{mode:'local',supported:true,ready:true}});
  f.nodes.get('message').value='mi borrador';await f.wake({id:'wake-2',text:'abre Safari'});
  assert.equal(f.nodes.get('message').value,'mi borrador\nabre Safari');assert.equal(f.requests.filter(r=>r.url==='/chat').length,0);
  f.nodes.get('message').value='';f.nodes.get('conversation-voice').onclick();assert.equal(f.captures[0].pcm,false);
  f.nodes.get('conversation-voice').onclick();await tick();
 }finally{f.cleanup();}
});
