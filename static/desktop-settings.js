'use strict';
const field=id=>document.getElementById(id);
let selectedApps=new Set(),installedApps=[],appsLoaded=false,configLoaded=false,refreshing=false;
const normalizeApp=value=>String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
function updateAppsGate(){
 field('apps-gate-note').textContent=field('skills').checked?'Acciones locales activadas: las apps marcadas se podrán abrir o cerrar normalmente cuando lo pidas.':'Las acciones locales están apagadas. Puedes preparar la lista; activa la casilla de acciones del Mac para usarla.';
}
function appRows(){
 const rows=installedApps.map(app=>({...app,missing:false}));
 for(const id of selectedApps)if(!rows.some(app=>app.id===id))rows.push({id,name:id.split('/').pop().replace(/\.app$/i,''),path:id,missing:true});
 return rows;
}
function renderApps(){
 const query=normalizeApp(field('apps-search').value),list=field('apps-list');list.replaceChildren();
 const rows=appRows();let visible=0;
 for(const app of rows){
  if(query&&!normalizeApp([app.name,app.command||'',app.path,...(app.aliases||[])].join(' ')).includes(query))continue;
  const row=document.createElement('label');row.className='app-choice'+(app.missing?' app-missing':'');
  const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=selectedApps.has(app.id);checkbox.disabled=!configLoaded;
  checkbox.setAttribute('aria-label','Permitir abrir o cerrar '+app.name);
  checkbox.onchange=()=>{if(checkbox.checked)selectedApps.add(app.id);else selectedApps.delete(app.id);updateAppsCount(visible);};
  const text=document.createElement('span'),name=document.createElement('strong'),location=document.createElement('small');
  name.textContent=app.name+(app.missing?' · No encontrada':'');location.textContent=app.path;row.title=app.path;
  text.append(name,location);row.append(checkbox,text);list.append(row);visible++;
 }
 if(appsLoaded&&!visible){const empty=document.createElement('p');empty.textContent=query?'No hay aplicaciones que coincidan.':'No se encontraron apps en las carpetas habituales de macOS.';list.append(empty);}
 updateAppsCount(visible);
}
function updateAppsCount(visible){
 if(appsLoaded)field('apps-status').textContent=selectedApps.size+' autorizadas · '+visible+' visibles de '+appRows().length+'.';
}
async function refreshApps(){
 if(refreshing||!configLoaded)return;
 refreshing=true;field('apps-refresh').disabled=true;field('apps-status').textContent='Buscando aplicaciones instaladas…';
 try{
  const result=await window.voxelDesktop.listInstalledApps();
  if(!result.ok)throw new Error(result.error||'No pude leer las aplicaciones.');
  if(!result.supported)throw new Error('La selección de aplicaciones está disponible en macOS.');
  installedApps=result.apps;appsLoaded=true;
  // Migrate legacy names to the concrete app shown in the selector. Preserve
  // unavailable selections so refreshing never silently revokes permissions.
  for(const id of [...selectedApps]){
   if(id.startsWith('/'))continue;
   const match=installedApps.find(app=>app.aliases.includes(normalizeApp(id)));
   if(match){selectedApps.delete(id);selectedApps.add(match.id);}
  }
  renderApps();
 }catch(error){field('apps-status').textContent=error.message+(appsLoaded?' Se conserva tu selección actual.':' Puedes guardar los demás ajustes sin cambiar la lista anterior.');}
 finally{refreshing=false;field('apps-refresh').disabled=false;}
}
field('config-save').disabled=true;
window.voxelDesktop.getSettings().then(async config=>{
 field('host').value=config.host;field('chat-model').value=config.model;field('memory-model').value=config.memoryModel;
 field('microphone').checked=config.microphone;field('wake-word').checked=config.wakeWord===true;field('learning').checked=config.learning;field('skills').checked=config.skills;
 const previous=config.allowedApps===undefined?['calculator','notes']:typeof config.allowedApps==='string'?config.allowedApps.split(',').map(x=>x.trim()).filter(Boolean):config.allowedApps;
 selectedApps=new Set(previous);configLoaded=true;field('config-save').disabled=false;
 if(config.hasKey)field('api-key').placeholder='Ya hay una clave guardada. Vacío la conserva.';
 await refreshApps();
 updateAppsGate();
}).catch(()=>{field('config-error').textContent='No se pudo leer la configuración. Cierra y vuelve a abrir Ajustes.';});
field('skills').onchange=updateAppsGate;
field('wake-word').onchange=()=>{if(field('wake-word').checked)field('microphone').checked=true;};
field('microphone').onchange=()=>{if(!field('microphone').checked)field('wake-word').checked=false;};
field('apps-search').oninput=renderApps;
field('apps-refresh').onclick=refreshApps;
field('apps-clear').onclick=()=>{if(!appsLoaded)return;selectedApps.clear();renderApps();};
field('desktop-config').onsubmit=async event=>{
 event.preventDefault();if(!configLoaded)return;
 field('config-save').disabled=true;field('config-error').textContent='Reconectando…';
 try{
  const result=await window.voxelDesktop.saveSettings({host:field('host').value,model:field('chat-model').value,memoryModel:field('memory-model').value,apiKey:field('api-key').value,clearKey:field('clear-key').checked,learning:field('learning').checked,skills:field('skills').checked,webSearch:true,microphone:field('microphone').checked,wakeWord:field('wake-word').checked,...(appsLoaded?{allowedApps:[...selectedApps]}:{})});
  if(!result.ok)throw new Error(result.error);
 }catch(error){field('config-error').textContent=error.message;}
 finally{field('config-save').disabled=false;}
};

function showLicense(value){field('license-state').textContent=value.plan==='pro'?'Pro activo · Vence: '+new Date(value.expiresAt*1000).toLocaleDateString():'Plan Free · Ollama local y Gemini';}
window.voxelDesktop.licenseStatus().then(showLicense).catch(()=>{field('license-state').textContent='No pude consultar la licencia.';});
for(const action of ['activate','remove'])field('license-'+action).onclick=async()=>{
 field('license-activate').disabled=true;field('license-remove').disabled=true;
 try{const result=action==='activate'?await window.voxelDesktop.activateLicense(field('license-token').value):await window.voxelDesktop.removeLicense();if(!result.ok)throw Error(result.error);field('license-token').value='';showLicense(result);field('license-message').textContent=action==='activate'?'Pro activado. Vuelve a abrir la configuración del modelo para ver los proveedores.':'Activación retirada. Selecciona Ollama local o Gemini para seguir usando Free.';}catch(error){field('license-message').textContent=error.message;}
 finally{field('license-activate').disabled=false;field('license-remove').disabled=false;}
};
