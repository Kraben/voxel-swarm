const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const detection=require('../static/wake-detection.js'),capture=require('../static/voice-capture.js');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await tick();}throw Error('Listener timeout');}
function fixture(responses){
 const commands=[],phases=[],errors=[],requests=[],events={};let node,closed=false,trackStopped=false,releaseFetch;
 const track=new EventTarget();track.stop=()=>{trackStopped=true;};
 class Audio{constructor(){this.sampleRate=16000;this.audioWorklet={addModule:async()=>{}};this.destination={};}async resume(){}async close(){closed=true;}createMediaStreamSource(){return {connect(){},disconnect(){}};}}
 class Worklet{constructor(){node=this;this.port={close(){},onmessage:null};}connect(){}disconnect(){}}
 const context={window:{VoxelVoiceCapture:capture,VoxelWakeDetection:detection,voxelWake:{phase:value=>phases.push(value),command:value=>commands.push(value),error:value=>errors.push(value),mute:()=>commands.push('MUTE')},addEventListener:(name,callback)=>events[name]=callback},location:{hash:'#access=fixture',pathname:'/static/wake-listener.html'},history:{replaceState(){}},navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[track],getAudioTracks:()=>[track]})}},AudioContext:Audio,AudioWorkletNode:Worklet,AbortController,URLSearchParams,Blob,setTimeout,clearTimeout,console,
 FileReader:class{readAsDataURL(){this.result='data:audio/wav;base64,ZmFrZQ==';queueMicrotask(()=>this.onload());}},fetch:async(url,options)=>{
  requests.push({url,options});let result=responses.shift();if(result==='pending')result=await new Promise(resolve=>{releaseFetch=resolve;});
  return {ok:!result.error,json:async()=>result};
 }};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/wake-listener.js'),'utf8'),context);
 return {commands,phases,errors,requests,get stopped(){return trackStopped&&closed;},finishFetch:result=>releaseFetch(result),async speak(){await until(()=>node?.port.onmessage);for(let i=0;i<5;i++)node.port.onmessage({data:{samples:new Float32Array(1600).fill(.1)}});for(let i=0;i<9;i++)node.port.onmessage?.({data:{samples:new Float32Array(1600).fill(.001)}});await tick();},close(){events.beforeunload();}};
}
test('activación sola espera un comando y lo entrega una vez con el micrófono cerrado',async()=>{
 const f=fixture([{wake:true,texto:''},{wake:false,texto:'abre Safari'}]);try{
  await f.speak();await until(()=>f.phases.includes('command'));assert.equal(f.commands.length,0);
  await f.speak();await until(()=>f.commands.length===1);assert.equal(f.commands[0],'abre Safari');assert.equal(f.stopped,true);assert.equal(JSON.parse(f.requests[0].options.body).wake,true);assert.equal(JSON.parse(f.requests[1].options.body).wake,false);
 }finally{f.close();}
});
test('una frase con llamada y comando no necesita un segundo clic ni otra captura',async()=>{
 const f=fixture([{wake:true,texto:'Abre Calculadora.'}]);try{await f.speak();await until(()=>f.commands.length===1);assert.equal(f.commands[0],'Abre Calculadora.');assert.equal(f.requests.length,1);assert.equal(f.stopped,true);}finally{f.close();}
});
test('el audio sin llamada no abre el chat y un resultado posterior al cierre se descarta',async()=>{
 const f=fixture([{wake:false,texto:''},'pending']);try{
  await f.speak();await until(()=>f.phases.at(-1)==='armed');assert.equal(f.commands.length,0);
  await f.speak();await until(()=>f.requests.length===2);f.close();f.finishFetch({wake:true,texto:'abre Safari'});await tick();assert.equal(f.commands.length,0);assert.equal(f.stopped,true);
 }finally{f.close();}
});
test('un error cierra el micrófono y no reintenta en bucle',async()=>{
 const f=fixture([{error:true,detail:'No model'}]);try{await f.speak();await until(()=>f.errors.length>0);assert.equal(f.stopped,true);assert.equal(f.commands.length,0);assert.equal(f.requests.length,1);}finally{f.close();}
});
