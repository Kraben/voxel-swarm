/* One bounded microphone turn. Every exit releases microphone and audio resources. */
(function(root){
 function encodeWav(chunks,sampleRate){
  if(!Number.isFinite(sampleRate)||sampleRate<8000||sampleRate>192000)throw new Error('Frecuencia de micrófono no compatible.');
  const total=chunks.reduce((sum,chunk)=>sum+chunk.length,0),length=Math.min(total,Math.floor(sampleRate*60));
  const samples=new Float32Array(length);let offset=0;
  for(const chunk of chunks){const part=chunk.subarray(0,length-offset);samples.set(part,offset);offset+=part.length;if(offset===length)break;}
  const frames=Math.floor(length*16000/sampleRate),buffer=new ArrayBuffer(44+frames*2),view=new DataView(buffer);
  const text=(at,value)=>{for(let i=0;i<value.length;i++)view.setUint8(at+i,value.charCodeAt(i));};
  text(0,'RIFF');view.setUint32(4,buffer.byteLength-8,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,frames*2,true);
  for(let i=0;i<frames;i++){
   const start=i*sampleRate/16000,end=(i+1)*sampleRate/16000;let value=0;
   // Average the source interval when downsampling to reduce aliasing.
   if(sampleRate>=16000){let weight=0;for(let j=Math.floor(start);j<Math.ceil(end)&&j<length;j++){const w=Math.min(end,j+1)-Math.max(start,j);value+=samples[j]*w;weight+=w;}value/=weight||1;}
   else{const at=Math.floor(start),fraction=start-at;value=samples[at]*(1-fraction)+(samples[Math.min(at+1,length-1)]||0)*fraction;}
   value=Math.max(-1,Math.min(1,value));view.setInt16(44+i*2,Math.round(value*(value<0?32768:32767)),true);
  }
  return new Blob([buffer],{type:'audio/wav'});
 }
 async function captureWav({signal,automatic,onListening,media,Audio,Worklet,detectorFactory,clock,timers}){
  let stream,context,node,source,analyser,timer,poll,abort,ended;const chunks=[];
  const check=()=>{if(signal.aborted)throw signal.reason||new DOMException('Cancelado','AbortError');};
  try{
   check();if(!Audio||!Worklet)throw new Error('La captura local de audio no está disponible en esta versión.');
   stream=await media.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});check();
   context=new Audio();await context.resume();check();
   await context.audioWorklet.addModule('/static/pcm-worklet.js');check();
   source=context.createMediaStreamSource(stream);node=new Worklet(context,'voxel-pcm');
   analyser=context.createAnalyser();analyser.fftSize=2048;source.connect(analyser);source.connect(node);node.connect(context.destination);
   const samples=new Float32Array(analyser.fftSize),detector=automatic?detectorFactory?.(clock()):null;
   if(automatic&&!detector)throw new Error('Detector de pausas no disponible.');
   return await new Promise((resolve,reject)=>{
    let stopping=false,empty=false,received=0;
    const stop=()=>{if(stopping)return;stopping=true;timers.clearTimeout(timer);timers.clearInterval(poll);node.port.postMessage('flush');timer=timers.setTimeout(()=>reject(new Error('El micrófono no respondió al finalizar. Vuelve a activar la conversación.')),2000);};
    abort=()=>reject(signal.reason||new DOMException('Cancelado','AbortError'));
    ended=()=>reject(new Error('Se desconectó el micrófono. Vuelve a activar la conversación.'));
    signal.addEventListener('abort',abort,{once:true});stream.getAudioTracks().forEach(track=>track.addEventListener('ended',ended,{once:true}));
    node.onprocessorerror=()=>reject(new Error('Falló la captura de voz local. Reinicia el chat.'));
    node.port.onmessage=event=>{
     if(event.data.samples){chunks.push(event.data.samples);received+=event.data.samples.length;if(received>=context.sampleRate*60)stop();}
     if(event.data.flushed){
      if(signal.aborted){reject(signal.reason);return;}
      try{resolve(empty?null:encodeWav(chunks,context.sampleRate));}catch(error){reject(error);}
     }
    };
    timer=timers.setTimeout(stop,60000);
    if(automatic)poll=timers.setInterval(()=>{
     if(stopping)return;
     try{analyser.getFloatTimeDomainData(samples);let sum=0;for(const n of samples)sum+=n*n;
      const result=detector.update(Math.sqrt(sum/samples.length),clock());
      if(result==='finished'||result==='empty'){empty=result==='empty';stop();}
     }catch(error){reject(error);}
    },100);
    onListening(stop);
   });
  }finally{
   timers.clearTimeout(timer);timers.clearInterval(poll);
   if(abort)signal.removeEventListener('abort',abort);
   stream?.getAudioTracks().forEach(track=>{if(ended)track.removeEventListener('ended',ended);});
   if(node){node.port.onmessage=null;node.port.close();node.disconnect();}source?.disconnect();analyser?.disconnect();
   stream?.getTracks().forEach(track=>track.stop());if(context)await context.close().catch(()=>{});
  }
 }
 async function captureTurn({signal,automatic=false,pcm=false,Worklet=globalThis.AudioWorkletNode,onListening=()=>{},media=navigator.mediaDevices,Recorder=MediaRecorder,Audio=globalThis.AudioContext||globalThis.webkitAudioContext,detectorFactory=globalThis.GhostSpeechEnd?.createDetector,clock=()=>performance.now(),timers=globalThis}){
  if(pcm)return captureWav({signal,automatic,onListening,media,Audio,Worklet,detectorFactory,clock,timers});
  let stream,context,recorder,timer,poll,abort,trackEnded,empty=false;
  const check=()=>{if(signal.aborted)throw signal.reason||new DOMException('Cancelado','AbortError');};
  try{
   check();
   stream=await media.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});check();
   const mime=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus'].find(type=>Recorder.isTypeSupported(type));
   recorder=new Recorder(stream,mime?{mimeType:mime,audioBitsPerSecond:64000}:{});
   const chunks=[];
   let analyser,samples,detector;
   if(automatic){
    if(!Audio||!detectorFactory)throw new Error('Detector de pausas no disponible. Usa el dictado manual.');
    context=new Audio();await context.resume();check();
    analyser=context.createAnalyser();analyser.fftSize=2048;
    context.createMediaStreamSource(stream).connect(analyser);
    samples=new Float32Array(analyser.fftSize);detector=detectorFactory(clock());
   }
   return await new Promise((resolve,reject)=>{
    abort=()=>{if(recorder.state==='recording')recorder.stop();reject(signal.reason||new DOMException('Cancelado','AbortError'));};
    trackEnded=()=>reject(new Error('Se desconectó el micrófono. Revisa el dispositivo y vuelve a activar la conversación.'));
    signal.addEventListener('abort',abort,{once:true});
    stream.getAudioTracks().forEach(track=>track.addEventListener('ended',trackEnded,{once:true}));
    recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);};
    recorder.onerror=()=>reject(new Error('La grabación falló. Revisa el micrófono.'));
    recorder.onstop=()=>{
     if(signal.aborted){reject(signal.reason);return;}
     resolve(empty?null:new Blob(chunks,{type:recorder.mimeType}));
    };
    recorder.start();onListening(()=>{if(recorder.state==='recording')recorder.stop();});
    timer=timers.setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},60000);
    if(automatic)poll=timers.setInterval(()=>{
     if(recorder.state!=='recording')return;
     try{
      analyser.getFloatTimeDomainData(samples);let sum=0;for(const n of samples)sum+=n*n;
      const result=detector.update(Math.sqrt(sum/samples.length),clock());
      if(result==='finished'||result==='empty'){empty=result==='empty';recorder.stop();}
     }catch(error){reject(error);}
    },100);
   });
  }finally{
   timers.clearTimeout(timer);timers.clearInterval(poll);
   if(abort)signal.removeEventListener('abort',abort);
   stream?.getAudioTracks().forEach(track=>{if(trackEnded)track.removeEventListener('ended',trackEnded);});
   if(recorder?.state==='recording'){recorder.onstop=null;recorder.stop();}
   stream?.getTracks().forEach(track=>track.stop());
   if(context)await context.close().catch(()=>{});
  }
 }
 const api={captureTurn,encodeWav};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.VoxelVoiceCapture=api;
})(globalThis);
