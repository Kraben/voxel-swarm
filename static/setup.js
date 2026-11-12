'use strict';
const $=id=>document.getElementById(id),bridge=window.voxelDesktop;
let saved={},working=false,catalog=[];
function service(){return catalog.find(item=>item.id===$('service').value);}
function clearSelection(){ $('setup-key').value=''; $('setup-key').placeholder='Introduce la clave de este proveedor'; $('setup-model').value=''; $('installed').replaceChildren(new Option('Seleccionar un modelo detectado…','')); message(''); }
function selectService(){
  clearSelection(); const selected=service(); $('setup-host').value=selected?.host||'';
  $('provider').value=selected?.provider||'openai'; render();
}
$('service').onchange=selectService;
$('provider-help').onclick=()=>bridge.openProviderHelp($('service').value);
$('ollama-download').onclick=event=>{event.preventDefault();bridge.openOllamaDownload();};
function mode(){return document.querySelector('input[name=mode]:checked').value;}
function input(){return {provider:mode()==='local'?'ollama':(service()?.id==='custom'?$('provider').value:service()?.provider||'openai'),host:$('setup-host').value.trim(),model:$('setup-model').value.trim(),memoryModel:$('setup-model').value.trim(),apiKey:$('setup-key').value,learning:$('setup-learning').checked,skills:saved.fresh?false:saved.skills===true};}
function busy(value){working=value;for(const id of ['discover','pull','finish','setup-host','setup-key','setup-model','installed','provider','service','provider-help'])$(id).disabled=value;document.querySelectorAll('input[name=mode]').forEach(e=>e.disabled=value);}
function message(text){$('setup-message').textContent=text;}
function render(){
 const local=mode()==='local',selected=service(),custom=!local&&selected?.id==='custom';
 $('service').required=!local;$('api-options').hidden=local;$('key-section').hidden=local;$('local-options').hidden=!local;
 $('protocol-options').hidden=!custom;
 const manual=!local&&!selected?.host;
 $('connection-details').open=manual&&!!selected;
 $('setup-host').readOnly=!local&&!!selected?.host;
 $('connection-summary').textContent=local?'Conexión local (opcional)':selected?.host?'Dirección configurada automáticamente':'Dirección de tu servidor';
 $('provider-note').textContent=selected?.locked?'Requiere Pro. Activa la licencia desde Ajustes. Free incluye Ollama local y Gemini.':selected?.note||'Elige un proveedor. Núcleo completará la dirección automáticamente.';
 $('provider-help').hidden=!selected?.help;
 $('privacy').textContent=local?'Los mensajes y recuerdos se procesan en tu Ollama local.':'El proveedor seleccionado recibirá los mensajes y los recuerdos incluidos en el contexto. La clave y el consumo corresponden a tu cuenta.';
}
document.querySelectorAll('input[name=mode]').forEach(e=>e.onchange=()=>{
 clearSelection();$('provider').value='openai';$('service').value='';
 $('setup-host').value=mode()==='local'?'http://127.0.0.1:11434':'';render();
});
$('provider').onchange=()=>{clearSelection();};
$('installed').onchange=()=>{if($('installed').value)$('setup-model').value=$('installed').value;};
$('discover').onclick=async()=>{
 if(mode()==='api'&&!service()){message('Elige primero un proveedor de IA.');return;}
 busy(true);message('Buscando modelos disponibles…');
 try{const value=input();if(!value.model)value.model=value.memoryModel='placeholder';const result=await bridge.setupList(value);if(!result.ok)throw new Error(result.error);$('installed').replaceChildren(new Option('Seleccionar un modelo detectado…',''));for(const model of result.models)$('installed').add(new Option(model,model));if(!$('setup-model').value&&result.models.length)$('setup-model').value=result.models[0];if(result.models.includes($('setup-model').value))$('installed').value=$('setup-model').value;message(result.models.length?'Conexión lista. Elige un modelo y pulsa «Probar y usar».':'Conexión lista. Aún no hay modelos; puedes descargar uno.');}
 catch(error){message(error.message+(mode()==='api'?' Si el servicio no ofrece listado, escribe el modelo y usa la prueba directa.':''));}finally{busy(false);}
};
bridge.onPullProgress(progress=>{$('pull-progress').hidden=false;if(progress.percent===null)$('pull-progress').removeAttribute('value');else $('pull-progress').value=progress.percent;$('progress-label').textContent=progress.total?'Descargando capa actual: '+progress.percent+'% · '+(progress.completed/1e9).toFixed(2)+' / '+(progress.total/1e9).toFixed(2)+' GB':progress.status;});
$('pull').onclick=async()=>{
 if(!$('setup-model').value.trim()){message('Escribe el nombre del modelo que quieres descargar.');return;}
 busy(true);$('cancel-pull').hidden=false;message('Iniciando descarga…');
 try{const result=await bridge.setupPull(input());if(!result.ok)throw new Error(result.error);message('Modelo descargado. Pulsa «Probar y usar» para terminar.');}
 catch(error){message(error.message);}finally{busy(false);$('cancel-pull').hidden=true;$('pull-progress').hidden=true;}
};
$('cancel-pull').onclick=()=>bridge.setupCancel();
$('setup-form').onsubmit=async event=>{
 event.preventDefault();if(mode()==='api'&&!service()){message('Elige un proveedor de IA.');return;}busy(true);message('Probando el modelo. Puede tardar mientras se carga por primera vez…');
 try{const result=await bridge.setupFinish(input());if(!result.ok)throw new Error(result.error);}
 catch(error){message(error.message);}finally{busy(false);}
};
Promise.all([bridge.getSettings(),bridge.getProviderCatalog()]).then(([config,entries])=>{
 saved=config;catalog=entries;
 for(const entry of catalog){const option=new Option(entry.name+(entry.plan==='pro'?' · Pro':' · Free'),entry.id);option.disabled=entry.locked===true;$('service').add(option);}
 $('setup-host').value=config.host;$('setup-model').value=config.fresh?'':config.model;
 $('setup-learning').checked=config.fresh?false:config.learning;
 const local=(config.provider||'ollama')==='ollama'&&/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(:|\/|$)/.test(config.host);
 if(!local){
  document.querySelector('input[value=api]').checked=true;
  const selected=catalog.find(item=>item.host&&item.host.replace(/\/$/,'')===config.host.replace(/\/$/,'')&&item.provider===config.provider);
  $('service').value=selected?.id||((config.provider||'ollama')==='ollama'?'ollama-remote':'custom');
  $('provider').value=config.provider||'ollama';
 }
 if(config.hasKey)$('setup-key').placeholder='Ya hay una clave guardada para este servidor. Vacío la conserva.';
 render();
}).catch(error=>message(error.message));
