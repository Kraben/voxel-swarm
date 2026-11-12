'use strict';
// Owns the microphone window separately from the disposable chat window.
function createWakeService({BrowserWindow,preferences,secureWindow,baseURL,accessToken,enabled,canListen,openChat,getChat,publish,fetcher=(...args)=>fetch(...args),timers=globalThis}){
 let win=null,disposed=false,epoch=0,timer,job=null,ready=false,failure='',model=null,phase='off',checking=false;
 const labels={off:'Oye Vox apagado',paused:'Oye Vox en pausa',loading:'Preparando Oye Vox',armed:'Oye Vox · esperando tu voz',command:'Te escucho · di el comando',transcribing:'Oye Vox · reconociendo voz local',processing:'Oye Vox · respondiendo',model:'Oye Vox · descarga Whisper local',error:'Oye Vox · revisa la configuración'};
 function status(){return {enabled:enabled(),phase,label:labels[phase]||labels.error,error:failure,model};}
 function report(value){phase=value;publish(status());}
 function stopWindow(){epoch++;if(win&&!win.isDestroyed())win.destroy();win=null;checking=false;}
 function cancelJob(){if(job?.timeout)timers.clearTimeout(job.timeout);job=null;}
 function pause(){timers.clearTimeout(timer);stopWindow();report(enabled()?'paused':'off');}
 function deliver(){
  const chat=getChat();if(!job||job.sent||!ready||!chat||chat.isDestroyed())return;
  job.sent=true;timers.clearTimeout(job.timeout);chat.webContents.send('voxel:wake-command',{id:job.id,text:job.text});
 }
 async function update(){
  if(disposed)return;
  if(!enabled()){stopWindow();cancelJob();failure='';report('off');return;}
  if(!canListen()){stopWindow();report(job?'processing':'paused');return;}
  if(job){report('processing');deliver();return;}
  if(failure){report('error');return;}
  if(win&&!win.isDestroyed())return;
  if(checking)return;
  checking=true;const generation=++epoch;report('loading');
  try{
   const response=await fetcher(baseURL()+'/api/voice/local/status',{headers:{Authorization:'Bearer '+accessToken()},signal:AbortSignal.timeout(10000)});
   if(!response.ok)throw Error('Activa el micrófono en Ajustes para usar Oye Vox.');
   const info=await response.json();if(disposed||generation!==epoch)return;checking=false;model=info;
   if(!info.ready){report('model');return;}
   if(info.wake_ready===false)throw Error('Falta el detector de Oye Vox. Instala el paquete completo de esta versión.');
   if(!enabled()||!canListen()){report('paused');return;}
   win=new BrowserWindow({title:'Núcleo · Escucha local',width:1,height:1,show:false,skipTaskbar:true,resizable:false,webPreferences:preferences()});
   const owner=win;
   owner.on('closed',()=>{if(win===owner)win=null;});
   owner.webContents.on('render-process-gone',()=>{if(win===owner){failure='Se detuvo el motor de escucha. Pulsa Reintentar Oye Vox en el menú.';stopWindow();report('error');}});
   secureWindow(owner,'/static/wake-listener.html');
  }catch(error){if(generation!==epoch||disposed)return;checking=false;failure=error.message;report('error');}
 }
 function sync(delay=250){if(disposed)return;timers.clearTimeout(timer);if(!enabled()||!canListen())pause();timer=timers.setTimeout(update,delay);}
 function onPhase(value){
  if(!enabled()||!canListen()||job)return;
  if(!['armed','command','transcribing'].includes(value))return;
  report(value);if(value==='command')openChat();
 }
 function command(text){
  if(disposed||!enabled()||!canListen()||job||typeof text!=='string'||!text.trim()||text.length>6000||!['command','transcribing'].includes(phase))return false;
  stopWindow();job={id:require('node:crypto').randomUUID(),text:text.trim(),sent:false};
  job.timeout=timers.setTimeout(()=>{cancelJob();failure='El chat no pudo recibir el comando. Abre la burbuja y reintenta Oye Vox.';report('error');},30000);
  report('processing');openChat();deliver();return true;
 }
 return {
  sync,pause,status,onPhase,command,cancelDelivery:cancelJob,
  get window(){return win;},
  chatReady(){ready=true;deliver();},
  chatLoading(){ready=false;},
  chatClosed(){ready=false;cancelJob();sync(500);},
  finish(id){if(!job||job.id!==id)return;cancelJob();sync(500);},
  fail(message){failure=String(message||'No pude acceder al micrófono. Revisa el permiso de Núcleo en macOS.').slice(0,300);stopWindow();report('error');},
  retry(){failure='';sync(0);},
  dispose(){disposed=true;timers.clearTimeout(timer);cancelJob();stopWindow();}
 };
}
module.exports={createWakeService};
