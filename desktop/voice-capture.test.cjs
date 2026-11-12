const {test}=require('node:test');const assert=require('node:assert/strict');
const {captureTurn}=require('../static/voice-capture.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(){
 const track=new EventTarget();track.stopped=false;track.stop=()=>{track.stopped=true;};
 const stream={getTracks:()=>[track],getAudioTracks:()=>[track]};
 let recorder,closed=false,poll;
 class Recorder{
  static isTypeSupported(){return true;}
  constructor(){recorder=this;this.mimeType='audio/webm';this.state='inactive';}
  start(){this.state='recording';}
  stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['audio'])});this.onstop?.();}
 }
 class Audio{
  async resume(){} async close(){closed=true;}
  createMediaStreamSource(){return {connect(){}};}
  createAnalyser(){return {getFloatTimeDomainData(samples){samples.fill(.1);}};}
 }
 const timers={setInterval(fn){poll=fn;return 1;},clearInterval(){poll=null;},setTimeout(){return 2;},clearTimeout(){}};
 return {track,stream,Recorder,Audio,timers,media:{getUserMedia:async()=>stream},get recorder(){return recorder;},get closed(){return closed;},poll(){poll();}};
}
test('detectar fin de frase libera el dispositivo antes de devolver el audio',async()=>{
 const f=fixture(),c=new AbortController();
 const result=captureTurn({...f,signal:c.signal,automatic:true,detectorFactory:()=>({update:()=> 'finished'})});
 await tick();f.poll();const blob=await result;
 assert.equal(blob.type,'audio/webm');assert.equal(await blob.text(),'audio');assert.equal(f.track.stopped,true);assert.equal(f.closed,true);
});
test('el silencio devuelve null y cierra micrófono y contexto',async()=>{
 const f=fixture(),c=new AbortController();const result=captureTurn({...f,signal:c.signal,automatic:true,detectorFactory:()=>({update:()=> 'empty'})});
 await tick();f.poll();assert.equal(await result,null);assert.equal(f.track.stopped,true);assert.equal(f.closed,true);
});
test('cancelar mientras se solicita permiso cierra el dispositivo cuando llegue',async()=>{
 const f=fixture(),c=new AbortController();let grant;
 const result=captureTurn({...f,signal:c.signal,media:{getUserMedia:()=>new Promise(resolve=>{grant=resolve;})}});
 c.abort();grant(f.stream);await assert.rejects(result,{name:'AbortError'});assert.equal(f.track.stopped,true);
});
test('cancelación y desconexión durante captura liberan los recursos',async()=>{
 for(const disconnect of [false,true]){
  const f=fixture(),c=new AbortController();const result=captureTurn({...f,signal:c.signal,automatic:true,detectorFactory:()=>({update:()=> 'speaking'})});
  await tick();if(disconnect)f.track.dispatchEvent(new Event('ended'));else c.abort();
  await assert.rejects(result);assert.equal(f.track.stopped,true);assert.equal(f.closed,true);assert.equal(f.recorder.state,'inactive');
 }
});
test('dictado manual conserva detener para entregar una sola grabación',async()=>{
 const f=fixture(),c=new AbortController();let stop;
 const result=captureTurn({...f,signal:c.signal,onListening:fn=>{stop=fn;}});
 await tick();stop();assert.equal((await result).size,5);assert.equal(f.track.stopped,true);
});

test('PCM local: WAV mono de 16 kHz con remuestreo y saturación válidos',async()=>{
 const {encodeWav}=require('../static/voice-capture.js');
 const blob=encodeWav([new Float32Array(48000).fill(.5)],48000),view=new DataView(await blob.arrayBuffer());
 assert.equal(blob.type,'audio/wav');assert.equal(view.getUint16(22,true),1);assert.equal(view.getUint32(24,true),16000);assert.equal(view.getUint16(34,true),16);assert.equal(view.getUint32(40,true),32000);assert.equal(view.getInt16(44,true),16384);
 const clipped=new DataView(await encodeWav([new Float32Array([-2,2])],16000).arrayBuffer());
 assert.equal(clipped.getInt16(44,true),-32768);assert.equal(clipped.getInt16(46,true),32767);
});
function pcmFixture(){
 const f=fixture();let node,closed=false,disconnected=false;
 class Audio{
  constructor(){this.sampleRate=48000;this.destination={};this.audioWorklet={addModule:async url=>assert.equal(url,'/static/pcm-worklet.js')};}
  async resume(){} async close(){closed=true;}
  createMediaStreamSource(){return {connect(){},disconnect(){}};}
  createAnalyser(){return {getFloatTimeDomainData(samples){samples.fill(.1);},disconnect(){}};}
 }
 class Worklet{
  constructor(){node=this;this.port={postMessage:()=>queueMicrotask(()=>this.port.onmessage?.({data:{flushed:true}})),close(){}};}
  connect(){} disconnect(){disconnected=true;}
 }
 return {...f,Audio,Worklet,get node(){return node;},get closed(){return closed;},get disconnected(){return disconnected;}};
}
test('captura local entrega WAV y libera nodos y micrófono antes de transcribir',async()=>{
 const f=pcmFixture(),c=new AbortController();let stop;
 const result=captureTurn({...f,signal:c.signal,pcm:true,onListening:fn=>{stop=fn;}});
 await tick();f.node.port.onmessage({data:{samples:new Float32Array(48000).fill(.2)}});stop();
 const blob=await result;assert.equal(blob.type,'audio/wav');assert.equal(blob.size,32044);assert.equal(f.track.stopped,true);assert.equal(f.closed,true);assert.equal(f.disconnected,true);
});
test('cancelar captura PCM libera el micrófono sin devolver una grabación tardía',async()=>{
 const f=pcmFixture(),c=new AbortController();const result=captureTurn({...f,signal:c.signal,pcm:true});await tick();c.abort();await assert.rejects(result,{name:'AbortError'});assert.equal(f.track.stopped,true);assert.equal(f.closed,true);
});
