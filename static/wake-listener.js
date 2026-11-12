'use strict';
(async()=>{
 const boot=new URLSearchParams(location.hash.slice(1)),token=boot.get('access')||'';
 history.replaceState(null,'',location.pathname);
 const controller=new AbortController();let stream,context,node,source,segmenter,processing=false,awaiting=false,commandTimer,stopped=false;
 function phase(value){window.voxelWake.phase(value);}
 function arm(){clearTimeout(commandTimer);awaiting=false;segmenter?.reset();phase('armed');}
 function awaitCommand(){
  awaiting=true;segmenter.reset();phase('command');
  commandTimer=setTimeout(()=>{if(!processing)arm();},15000);
 }
 async function recognize(chunks){
  if(processing||stopped)return;processing=true;clearTimeout(commandTimer);phase('transcribing');
  const isCommand=awaiting;
  try{
   const blob=window.VoxelVoiceCapture.encodeWav(chunks,context.sampleRate);
   const audio=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(blob);});
   const timeout=setTimeout(()=>controller.abort(),125000);
   let response;
   try{response=await fetch('/api/voice/local/transcribe',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({audio,mime:'audio/wav',consent:true,wake:!isCommand})});}
   finally{clearTimeout(timeout);}
   const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'No pude reconocer la voz local.');
   if(stopped)return;
   const text=String(data.texto||'').trim();
   if(data.wake){
    if(text){phase('command');if(window.VoxelWakeDetection.muteCommand(text))window.voxelWake.mute();else window.voxelWake.command(text);cleanup();return;}
    awaitCommand();return;
   }
   if(isCommand&&text){
    phase('command');if(window.VoxelWakeDetection.muteCommand(text))window.voxelWake.mute();else window.voxelWake.command(text);cleanup();return;
   }
   arm();
  }catch(error){if(!stopped){window.voxelWake.error(error.message||'Falló la escucha local.');cleanup();}}
  finally{processing=false;segmenter?.reset();}
 }
 function cleanup(){
  stopped=true;clearTimeout(commandTimer);controller.abort();
  if(node){node.port.onmessage=null;node.port.close();node.disconnect();}source?.disconnect();
  stream?.getTracks().forEach(track=>track.stop());context?.close().catch(()=>{});
 }
 window.addEventListener('beforeunload',cleanup);
 try{
  stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});
  if(stopped){stream.getTracks().forEach(track=>track.stop());return;}
  context=new AudioContext();await context.resume();await context.audioWorklet.addModule('/static/pcm-worklet.js');
  if(stopped){cleanup();return;}
  segmenter=window.VoxelWakeDetection.createSegmenter(context.sampleRate);
  node=new AudioWorkletNode(context,'voxel-pcm');source=context.createMediaStreamSource(stream);source.connect(node);node.connect(context.destination);
  node.onprocessorerror=()=>{window.voxelWake.error('Falló la captura de Oye Vox. Reinténtalo desde el menú.');cleanup();};
  stream.getAudioTracks().forEach(track=>track.addEventListener('ended',()=>{if(!stopped){window.voxelWake.error('Se desconectó el micrófono. Revisa el dispositivo.');cleanup();}},{once:true}));
  node.port.onmessage=event=>{
   if(stopped||processing||!event.data.samples)return;
   const chunks=segmenter.push(event.data.samples);
   if(chunks)recognize(chunks);
  };
  arm();
 }catch(error){if(!stopped)window.voxelWake.error(error.name==='NotAllowedError'?'macOS no permitió el micrófono. Autoriza Núcleo en Privacidad y seguridad → Micrófono.':error.message);cleanup();}
})();
