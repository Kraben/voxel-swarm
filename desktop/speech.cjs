'use strict';
const {spawn}=require('node:child_process');
function createSpeech(spawner=spawn){
 let active;
 function stop(){if(active){active.cancelled=true;active.child.kill();active=null;}}
 function speak(text){
  if(typeof text!=='string'||!text.trim()||text.length>6000)return Promise.resolve({ok:false});
  stop();
  return new Promise(resolve=>{
   // El texto va por stdin: nunca se convierte en argumentos ni código de shell.
   const child=spawner('/usr/bin/say',[],{stdio:['pipe','ignore','ignore'],shell:false});
   const current={child,cancelled:false};active=current;
   child.once('error',()=>{if(active===current)active=null;resolve({ok:false});});
   child.once('close',code=>{if(active===current)active=null;resolve({ok:code===0,cancelled:current.cancelled});});
   child.stdin.on('error',()=>{});child.stdin.end(text);
  });
 }
 return {speak,stop};
}
module.exports={createSpeech};
