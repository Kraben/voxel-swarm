/* Conversation lifecycle shared by the desktop UI and deterministic tests. */
(function(root){
 function delay(ms,signal){
  return new Promise((resolve,reject)=>{
   if(signal.aborted){reject(signal.reason);return;}
   const abort=()=>{clearTimeout(timer);reject(signal.reason);};
   const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve();},ms);
   signal.addEventListener('abort',abort,{once:true});
  });
 }
 function createConversation({capture,transcribe,respond,ready=()=>true,onState=()=>{},onError=()=>{},idleMs=120000,now=Date.now,wait=delay}){
  let run=null;
  function stop(){if(run&&!run.signal.aborted){run.abort();onState('stopping');}}
  function start(){
   if(run)return run.task;
   const current=new AbortController();run=current;
   current.task=(async()=>{
    let activity=now();
    try{
     while(!current.signal.aborted){
      if(now()-activity>=idleMs){onState('inactive');break;}
      if(!ready()){onState('paused');await wait(300,current.signal);continue;}
      onState('listening');
      const audio=await capture(current.signal);
      if(current.signal.aborted)break;
      if(!audio)continue; // Silence never reaches a transcription service.
      activity=now();onState('transcribing');
      const text=String(await transcribe(audio,current.signal)).trim();
      if(current.signal.aborted)break;
      if(!text)throw new Error('No pude reconocer la frase. Activa de nuevo la conversación para intentarlo.');
      onState('thinking');
      if(await respond(text,current.signal)===false)break;
      if(current.signal.aborted)break;
      activity=now();
      // Let the speaker output settle before opening the next microphone turn.
      await wait(450,current.signal);
     }
    }catch(error){if(!current.signal.aborted)onError(error);}
    finally{if(run===current){run=null;onState('off');}}
   })();
   return current.task;
  }
  return {start,stop,get active(){return !!run&&!run.signal.aborted;},get running(){return !!run;}};
 }
 const api={createConversation};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.VoxelVoiceSession=api;
})(globalThis);
