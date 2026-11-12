/* Bounded, in-memory speech segmentation and an explicit wake phrase gate. */
(function(root){
 function wakePhrase(text){
  const match=String(text).match(/^\s*[¡¿"“]*[oó]ye\s*[,.:;!?-]?\s+(?:v[oó]x|box|voks|vocs)\b[\s,.:;!?¡¿-]*/iu);
  return match?{command:String(text).slice(match[0].length).trim()}:null;
 }
 function muteCommand(text){return /^(?:descansa(?: vox)?|deja de escuchar|silencia(?: el)? microfono)[.!?\s]*$/i.test(String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,''));}
 function createSegmenter(rate,{silenceMs=900,minSpeechMs=250,maxMs=20000,preMs=400}={}){
  let pre=[],preSamples=0,chunks=null,length=0,voicedMs=0,silence=0,noise=.004;
  function reset(){pre=[];preSamples=0;chunks=null;length=0;voicedMs=0;silence=0;}
  return {reset,get active(){return !!chunks;},push(frame){
   const duration=frame.length*1000/rate;let energy=0;for(const sample of frame)energy+=sample*sample;
   const voiced=Math.sqrt(energy/frame.length)>Math.max(.012,noise*3);
   if(!chunks){
    pre.push(frame);preSamples+=frame.length;
    while(pre.length>1&&preSamples-pre[0].length>=rate*preMs/1000)preSamples-=pre.shift().length;
    if(!voiced){noise=noise*.97+Math.sqrt(energy/frame.length)*.03;return null;}
    chunks=pre;length=preSamples;pre=[];preSamples=0;voicedMs=duration;silence=0;
   }else{chunks.push(frame);length+=frame.length;if(voiced){voicedMs+=duration;silence=0;}else silence+=duration;}
   if(voicedMs<minSpeechMs&&silence>=400){reset();return null;}
   if((voicedMs>=minSpeechMs&&silence>=silenceMs)||length*1000/rate>=maxMs){const result=voicedMs>=minSpeechMs?chunks:null;reset();return result;}
   return null;
  }};
 }
 const api={wakePhrase,muteCommand,createSegmenter};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.VoxelWakeDetection=api;
})(globalThis);
