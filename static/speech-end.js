/* Detector local de fin de frase por nivel y silencio; no accede al micrófono. */
(function(root){
 function createDetector(start,{silenceMs=1600,noSpeechMs=8000,minSpeechMs=300}={}){
  let noise=.004,last=start,lastVoice=start,speech=0,heard=false;
  return {update(rms,now){
   const elapsed=Math.max(0,Math.min(200,now-last));last=now;
   const voiced=rms>Math.max(.012,noise*3);
   if(voiced){speech+=elapsed;lastVoice=now;if(speech>=minSpeechMs)heard=true;}
   else if(!heard)noise=noise*.97+rms*.03;
   if(heard&&now-lastVoice>=silenceMs)return 'finished';
   if(!heard&&now-start>=noSpeechMs)return 'empty';
   return heard?'speaking':'waiting';
  }};
 }
 const api={createDetector};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.GhostSpeechEnd=api;
})(globalThis);
