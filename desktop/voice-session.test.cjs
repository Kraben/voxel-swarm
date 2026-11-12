const {test}=require('node:test');const assert=require('node:assert/strict');
const {createConversation}=require('../static/voice-session.js');
const defer=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('varios turnos: no vuelve a capturar hasta terminar la respuesta y una sola sesión',async()=>{
 const first=defer(),playback=defer(),second=defer(),events=[];let captures=0;
 const session=createConversation({capture:()=>{events.push('capture');return ++captures===1?first.promise:second.promise;},transcribe:async()=>{events.push('transcribe');return 'hola';},respond:async()=>{events.push('respond');await playback.promise;},wait:async()=>{},onState:s=>events.push(s)});
 const running=session.start();assert.equal(session.start(),running);first.resolve('audio');await tick();
 assert.equal(captures,1);assert.equal(events.includes('respond'),true);
 playback.resolve();await tick();assert.equal(captures,2);
 session.stop();second.resolve('late audio');await running;
 assert.equal(events.filter(x=>x==='transcribe').length,1);assert.equal(session.running,false);
});
test('cancelar durante la transcripción impide enviar un mensaje tardío',async()=>{
 const transcription=defer();let responses=0;
 const session=createConversation({capture:async()=> 'audio',transcribe:()=>transcription.promise,respond:()=>{responses++;}});
 const running=session.start();await tick();session.stop();transcription.resolve('no enviar');await running;
 assert.equal(responses,0);assert.equal(session.active,false);
});
test('silencio no se transcribe y la sesión termina por inactividad',async()=>{
 let time=0,calls=0;const states=[];
 const session=createConversation({now:()=>time,idleMs:100,capture:async()=>{time+=50;return null;},transcribe:()=>{calls++;},respond:()=>{},onState:s=>states.push(s)});
 await session.start();assert.equal(calls,0);assert.ok(states.includes('inactive'));assert.equal(states.at(-1),'off');
});
test('un borrador o una confirmación pendiente pausa nuevas capturas',async()=>{
 const paused=defer();let captures=0,allowed=false,session;
 session=createConversation({ready:()=>allowed,capture:async()=>{captures++;return 'audio';},transcribe:async()=> 'hola',respond:async()=>false,wait:()=>paused.promise});
 const running=session.start();await tick();assert.equal(captures,0);
 allowed=true;paused.resolve();await running;assert.equal(captures,1);
});
test('fallos de micrófono o proveedor detienen el ciclo sin reintentos de pago',async()=>{
 for(const failedStep of ['capture','transcribe','respond']){
  let errors=0,captures=0;
  const session=createConversation({capture:async()=>{captures++;if(failedStep==='capture')throw Error('mic');return 'audio';},transcribe:async()=>{if(failedStep==='transcribe')throw Error('red');return 'hola';},respond:async()=>{throw Error('respuesta');},onError:()=>errors++});
  await session.start();assert.equal(errors,1);assert.equal(captures,1);assert.equal(session.running,false);
 }
});
