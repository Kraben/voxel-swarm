'use strict';
const {spawn}=require('node:child_process');

function speechCommand(platform=process.platform){
 if(platform==='win32'){
  return {
   bin:'powershell.exe',
   args:['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command','$input=[Console]::In.ReadToEnd();Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak($input)'],
   windowsHide:true
  };
 }
 if(platform==='linux'){
  return {
   bin:'spd-say',
   args:['-e'],
   windowsHide:false
  };
 }
 return {
  bin:'/usr/bin/say',
  args:[],
  windowsHide:false
 };
}

function createSpeech(spawner=spawn,platform=process.platform){
 let active;
 function stop(){if(active){active.cancelled=true;try{active.child.kill();}catch{}active=null;}}
 function speak(text){
  if(typeof text!=='string'||!text.trim()||text.length>6000)return Promise.resolve({ok:false});
  stop();
  return new Promise(resolve=>{
   const cmd=speechCommand(platform);
   // El texto va por stdin: nunca se convierte en argumentos ni código de shell.
   const child=spawner(cmd.bin,cmd.args,{stdio:['pipe','ignore','ignore'],shell:false,windowsHide:cmd.windowsHide});
   const current={child,cancelled:false};active=current;
   child.once('error',()=>{if(active===current)active=null;resolve({ok:false,fallback:true});});
   child.once('close',code=>{if(active===current)active=null;resolve({ok:code===0,cancelled:current.cancelled});});
   child.stdin.on('error',()=>{});child.stdin.end(text);
  });
 }
 return {speak,stop,speechCommand};
}
module.exports={createSpeech,speechCommand};
