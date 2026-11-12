'use strict';
const $ = id => document.getElementById(id);
window.voxelDesktop?.onSkin(skin=>{
  if(['cyan','azul','violeta','verde','ambar'].includes(skin)) document.documentElement.dataset.skin=skin;
});
if (window.voxelDesktop?.platform) {
  const names = {darwin:'macOS',win32:'WINDOWS',linux:'LINUX'};
  const edition = document.querySelector('.edition');
  if (edition) edition.textContent = 'COMPAÑERO DE ESCRITORIO / ' + (names[window.voxelDesktop.platform] || 'DESKTOP');
}
let speechGeneration=0,speechFinish,speaking=false,transcribing=false,openingMic=false;
let capabilities={},recordStream=false,manualMic,manualStop,voiceConversation;
let localVoiceTimer,localVoiceRequest=false,wakeInfo={enabled:false},wakeTurn,lastVoiceBlock;
let autoVoice=false;
let backend = '', token = '', busy = false, voice = false, stateTimer, controller, activeText = '';
const boot = new URLSearchParams(location.hash.slice(1));
if (boot.has('access')) { token = boot.get('access'); history.replaceState(null, '', location.pathname); }
let session = boot.get('session');
if (!session) { try { session = localStorage.getItem('ghost-session'); } catch {} }
if (!session || !/^[a-f0-9-]{36}$/i.test(session)) session = crypto.randomUUID();
function saveSession() {
  try { localStorage.setItem('ghost-session', session); } catch {}
  window.webkit?.messageHandlers?.ghostSession?.postMessage(session);
  window.voxelDesktop?.saveSession(session);
}
saveSession();
function notice(text = '') { $('notice').hidden = !text; $('notice').textContent = text; }
function setState(state) {
  window.voxelDesktop?.publishState(state);
  clearTimeout(stateTimer);
  const stage = $('stage');
  if (stage) stage.dataset.state = state;
  const names = {idle:'En reposo', pensando:'Procesando señal', hablando:'Transmitiendo'};
  if ($('state-label')) $('state-label').textContent = names[state];
  stage?.setAttribute('aria-label', 'Núcleo: ' + names[state]);
  document.querySelectorAll('[data-preview]').forEach(b => b.classList.toggle('active', b.dataset.preview === state));
}
let bubbleExpanded=false,bubbleRestTimer,bubbleHasResponse=false,bubbleHovered=false;
function setBubbleExpanded(value){
 if(!document.body.classList.contains('bubble-chat'))return;
 bubbleExpanded=value;document.body.classList.toggle('bubble-expanded',value);
 if($('bubble-expand')){$('bubble-expand').textContent=value?'↙':'↗';$('bubble-expand').setAttribute('aria-expanded',String(value));$('bubble-expand').setAttribute('aria-label',value?'Volver a burbuja compacta':'Ver conversación completa');$('bubble-expand').title=value?'Volver a burbuja compacta':'Ver conversación completa';}
 clearTimeout(bubbleRestTimer);window.voxelDesktop?.expandChat(value);
 $('messages').scrollTop=$('messages').scrollHeight;
}
function scheduleBubbleRest(){
 clearTimeout(bubbleRestTimer);
 if(!window.voxelDesktop?.closeChat||!bubbleHasResponse||bubbleExpanded||bubbleHovered||voiceConversation?.running||voice||busy||recordStream||openingMic||transcribing||$('message').value.trim()||document.querySelector('dialog[open]')||document.querySelector('.action-card button:not(:disabled)'))return;
 bubbleRestTimer=setTimeout(()=>{if(!busy&&!recordStream&&!transcribing&&!openingMic&&!$('message').value.trim()&&!document.querySelector('dialog[open]'))window.voxelDesktop.closeChat();},18000);
}
if($('bubble-expand'))$('bubble-expand').onclick=()=>{setBubbleExpanded(!bubbleExpanded);scheduleBubbleRest();};
if($('bubble-close'))$('bubble-close').onclick=()=>{stopVoiceMode();if(window.voxelDesktop?.closeChat)window.voxelDesktop.closeChat();else notice('En la app, este botón deja solo el avatar.');};
if(document.body.classList.contains('bubble-chat')){
 window.voxelDesktop?.onChatAnchor(side=>{if(['left','right'].includes(side))document.body.dataset.anchor=side;});
 document.body.addEventListener('pointerenter',()=>{bubbleHovered=true;clearTimeout(bubbleRestTimer);});
 document.body.addEventListener('pointerleave',()=>{bubbleHovered=false;scheduleBubbleRest();});
 $('message').addEventListener('input',()=>{clearTimeout(bubbleRestTimer);});
}
function append(text, role, error = false) {
  $('messages').querySelector('.welcome')?.remove();
  const article = document.createElement('article'); article.className = 'message ' + (role === 'ghost' ? 'assistant' : role) + (error ? ' error' : '');
  const label = document.createElement('div'); label.className = 'message-label'; label.textContent = role === 'user' ? 'TÚ / GUARDIÁN' : '✧ NÚCLEO';
  const body = document.createElement('div'); body.className = 'message-body'; body.textContent = text;
  article.append(label, body);
  if (error) {
    const actions = document.createElement('div'); actions.className = 'message-actions';
    const retry = document.createElement('button'); retry.textContent = 'Volver a intentar'; retry.onclick = () => { if (!busy) send(activeText); };
    actions.append(retry); article.append(actions);
  }
  document.querySelectorAll('.bubble-latest,.bubble-latest-sources').forEach(node=>node.classList.remove('bubble-latest','bubble-latest-sources'));article.classList.add('bubble-latest');
  $('messages').append(article); $('messages').scrollTop = $('messages').scrollHeight;
  return article;
}
async function api(path, options = {}, timeout = 210000) {
  const abort = new AbortController();
  if (options.method === 'POST') controller = abort;
  const externalAbort=()=>abort.abort();
  options.signal?.addEventListener('abort',externalAbort,{once:true});
  if(options.signal?.aborted)abort.abort();
  const timer = setTimeout(() => abort.abort(), timeout);
  try {
    const res = await fetch(backend + path, {...options, signal:abort.signal, headers:{...(options.body ? {'Content-Type':'application/json'} : {}), ...(token ? {Authorization:'Bearer ' + token} : {})}});
    let data;
    try { data = await res.json(); } catch { throw new Error('El servidor devolvió una respuesta no válida. Revisa la dirección de Núcleo.'); }
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'La solicitud no es válida. Revisa el mensaje y la configuración.');
    return data;
  } catch (e) {
    if(options.signal?.aborted)throw options.signal.reason||e;
    if (e.name === 'AbortError') throw new Error('Se agotó el tiempo de espera. El servidor puede seguir trabajando; espera antes de reintentar.');
    if (e instanceof TypeError) throw new Error('No hay enlace con Núcleo. Comprueba que el servidor esté encendido y revisa Conexión.');
    throw e;
  } finally { clearTimeout(timer);options.signal?.removeEventListener('abort',externalAbort); }
}
async function status() {
  $('connection-label').textContent = 'Comprobando enlace';
  try {
    const data = await api('/api/status', {}, 8000); capabilities=data;updateLocalVoice(data.voz);
    $('connection-dot').classList.toggle('online', data.conectado);
    $('connection-label').textContent = data.conectado ? (data.proveedor === 'openai' ? 'API configurada' : 'Enlace establecido') : 'Ollama sin conexión';
    const previous = $('model').value;
    $('model').replaceChildren(new Option('Modelo del servidor · ' + data.modelo, ''));
    for (const model of data.modelos) $('model').add(new Option(model, model));
    if (data.modelos.includes(previous)) $('model').value = previous;
    $('model-caption').textContent = (data.proveedor === 'openai' ? 'API / ' : 'OLLAMA / ') + ($('model').value || data.modelo);
    $('server-info').textContent = 'Servidor: ' + (data.servidor_ollama || 'configurado') + ' · Skills ' + (data.skills ? 'apps autorizadas · archivos con confirmación' : 'bloqueadas') + ' · Aprendizaje ' + (data.aprendizaje ? 'activo' : 'apagado') + ' · Herramientas: ' + ({native:'selección del modelo',compatibility:'comandos directos',unverified:'se comprobarán al conversar'}[data.herramientas?.mode]||'comandos directos');
    if (!data.conectado) notice('Ollama no responde. Puedes revisar la memoria; para conversar, inicia Ollama y carga tu modelo.'); else notice();
  } catch (e) {
    $('connection-dot').classList.remove('online'); $('connection-label').textContent = 'Sin enlace';
    $('server-info').textContent = e.message; notice(e.message);
  }
}
function cancelSpeech(){
 speechGeneration++;window.voxelDesktop?.stopSpeech();
 if('speechSynthesis' in window)speechSynthesis.cancel();
 speechFinish?.(false);speaking=false;publishVoiceBlock();
}
function speak(text,forceVoice=false) {
 cancelSpeech();
 const generation=++speechGeneration;setState('hablando');
 if(!voice&&!forceVoice){stateTimer=setTimeout(()=>setState('idle'),Math.min(14000,Math.max(1800,text.length*28)));return Promise.resolve(true);}
 speaking=true;publishVoiceBlock();
 return new Promise(resolve=>{
  let finished=false;
  const finish=ok=>{
   if(finished)return;finished=true;clearTimeout(watchdog);
   if(speechFinish===finish)speechFinish=null;
   if(generation===speechGeneration){speaking=false;setState('idle');publishVoiceBlock();}
   resolve(ok);
  };
  const failed=()=>{if(generation===speechGeneration)notice('No pude reproducir la voz. Revisa la salida de audio y vuelve a activar la conversación.');finish(false);};
  const watchdog=setTimeout(()=>{window.voxelDesktop?.stopSpeech();if('speechSynthesis' in window)speechSynthesis.cancel();failed();},120000);
  speechFinish=finish;
  try{
   if(window.voxelDesktop?.platform==='darwin'&&window.voxelDesktop.speakNative){
    window.voxelDesktop.speakNative(text.slice(0,6000)).then(result=>{
     if(generation!==speechGeneration){finish(false);return;}
     if(result.ok)finish(true);else if(result.cancelled)finish(false);else failed();
    },failed);
   }else if('speechSynthesis' in window){
    const utterance=new SpeechSynthesisUtterance(text);utterance.lang='es-MX';utterance.rate=.96;
    utterance.onend=()=>finish(true);utterance.onerror=failed;speechSynthesis.speak(utterance);
   }else failed();
  }catch{failed();}
 });
}
function confirmSkill(text) {
  setBubbleExpanded(true);
  $('skill-text').textContent = text; $('skill-confirm').showModal();
  return new Promise(resolve => {
    function finish(value) { $('skill-confirm').close(); resolve(value); }
    $('skill-accept').onclick = () => finish(true);
    $('skill-cancel').onclick = () => finish(false);
    $('skill-confirm').oncancel = () => resolve(false);
  });
}
async function send(text,{spoken=false,signal}={}) {
  if(signal?.aborted)return false;
  if(recordStream||transcribing||openingMic){notice('Termina el dictado antes de enviar otro mensaje.');return false;}
  if (busy || !text.trim()) return false;
  busy = true; window.voxelDesktop?.publishBusy(true); activeText = text; $('send').disabled = true; $('new-chat').disabled = true;
  $('message').value = ''; notice();
  cancelSpeech();
  append(text, 'user'); setState('pensando');
  const loading = document.createElement('div'); loading.className = 'loading'; loading.textContent = '✧ Procesando mensaje y comprobando si necesita fuentes…'; $('messages').append(loading);
  try {
    const payload = {texto:text, session_id:session, modelo:$('model').value || null};
    let data = await api('/chat', {method:'POST',body:JSON.stringify(payload)});
    if(signal?.aborted)return false;
    if (data.requiere_confirmacion) {
      setState('idle');
      window.voxelDesktop?.publishBusy(false);
      if (!await confirmSkill(data.respuesta||text)) { append('Acción cancelada. No ejecuté la skill.', 'ghost'); return; }
      if(signal?.aborted)return false;
      window.voxelDesktop?.publishBusy(true);
      setState('pensando'); data = await api('/chat', {method:'POST',body:JSON.stringify({...payload,confirmar_skill:true,...(data.tool_request_id?{tool_request_id:data.tool_request_id}:{})})});
    }
    if(signal?.aborted)return false;
    const responseArticle=append(data.respuesta, 'ghost');
    if(data.busqueda){const marker=document.createElement('div');marker.className='search-indicator';marker.textContent=data.busqueda.automatic?'Internet · búsqueda automática':'Internet · búsqueda solicitada';responseArticle.prepend(marker);}
    if(data.herramienta){const marker=document.createElement('div');marker.className='search-indicator';marker.textContent='Herramienta de Núcleo · '+({core_find_files:'Buscar archivos',core_search_web:'Buscar en internet',core_group_results:'Reunir archivos',core_undo_group:'Restaurar archivos',core_desktop_plan:'Organizar Escritorio',core_open_app:'Abrir aplicación'}[data.herramienta.name]||'Acción local');responseArticle.prepend(marker);}
    bubbleHasResponse=true;
    const playback=speak(data.respuesta,spoken);
    if(spoken)setVoiceStatus('replying');
    if(data.accion?.count)appendAction(data.accion);
    if(data.fuentes?.length)appendSources(data.fuentes);
    if (data.advertencia) notice(data.advertencia);
    if(spoken)return await playback;
    return true;
  } catch (e) { if(!signal?.aborted)append(e.message, 'ghost', true);setState('idle');return false; }
  finally { loading.remove(); busy = false; window.voxelDesktop?.publishBusy(false); $('send').disabled = false; $('new-chat').disabled = false; $('message').focus();scheduleBubbleRest(); }
}
$('chat-form').onsubmit = e => { e.preventDefault(); send($('message').value.trim()); };
$('message').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send($('message').value.trim()); } };
document.querySelectorAll('[data-prompt]').forEach(b => b.onclick = () => send(b.dataset.prompt));
document.querySelectorAll('[data-preview]').forEach(b => b.onclick = () => { if (!busy) { setState(b.dataset.preview); stateTimer = setTimeout(() => setState('idle'), 5000); } });
$('voice').onclick = () => {
  if (!('speechSynthesis' in window)&&!window.voxelDesktop?.speakNative) { notice('La lectura en voz alta no está disponible en este navegador.'); return; }
  if(voiceConversation?.running){stopVoiceMode();return;}
  voice = !voice; $('voice').textContent = voice ? '◖ Voz encendida' : '◖ Voz apagada'; $('voice').setAttribute('aria-pressed', String(voice));
  if (!voice) { cancelSpeech(); setState('idle'); }
};
if ($('motion')) $('motion').onclick = () => { const paused = $('stage').classList.toggle('paused'); $('motion').textContent = paused ? 'Reanudar movimiento' : 'Pausar movimiento'; $('motion').setAttribute('aria-pressed', String(paused)); };
$('settings-open').onclick = () => { stopVoiceMode(); $('backend').value = backend; $('token').value = token; $('settings').showModal(); };
$('save-settings').onclick = async () => {
  const value = $('backend').value.trim().replace(/\/$/, '');
  if (value) {
    let url; try { url = new URL(value); } catch { $('server-info').textContent = 'Introduce una URL completa con http:// o https://.'; return; }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) { $('server-info').textContent = 'Usa solo el origen del servidor, sin rutas, parámetros ni credenciales.'; return; }
    if (url.protocol !== 'https:' && !['localhost','127.0.0.1','[::1]'].includes(url.hostname)) { $('server-info').textContent = 'Los servidores remotos requieren HTTPS.'; return; }
  }
  backend = value; token = $('token').value; $('save-settings').disabled = true;
  await status(); await restore(); $('save-settings').disabled = false;
};
$('model').onchange = () => { stopVoiceMode(); $('model-caption').textContent = 'OLLAMA / ' + ($('model').value || 'PREDETERMINADO'); };
$('memory-open').onclick = async () => {
  stopVoiceMode();manualMic?.abort();
  setBubbleExpanded(true);
  $('memory-content').textContent = 'Leyendo registros…'; $('memory').showModal();
  try {
    const data = await api('/api/memory', {}, 10000); $('memory-content').replaceChildren();
    for (const [key, title] of [['usuario','SOBRE TI'],['ghost','SOBRE EL NÚCLEO']]) {
      const h = document.createElement('h3'); h.textContent = title; $('memory-content').append(h);
      const p = document.createElement('p'); p.textContent = data[key].map((r,i) => `${i+1}. [${r.categoria}] ${r.dato}`).join('\n') || 'Aún no hay recuerdos.'; $('memory-content').append(p);
    }
  } catch (e) { $('memory-content').textContent = e.message; }
};
const welcome = $('messages').innerHTML;
$('new-chat').onclick = () => { if (busy||transcribing||openingMic) return; bubbleHasResponse=false;clearTimeout(bubbleRestTimer); stopVoiceMode();manualMic?.abort(); session = crypto.randomUUID(); saveSession(); $('messages').innerHTML = welcome; document.querySelectorAll('[data-prompt]').forEach(b => b.onclick = () => send(b.dataset.prompt)); setState('idle'); notice('Nueva conversación. Tu memoria personal sigue guardada.'); cancelSpeech(); };
async function restore() {
  try {
    const data = await api('/api/history/' + session, {}, 10000);
    if (data.turnos.length) { $('messages').replaceChildren(); data.turnos.forEach(t => { append(t.usuario,'user'); append(t.ghost,'ghost'); }); }
  } catch {}
}
const initialLoad=Promise.allSettled([status(),restore()]);

function appendSources(sources){
 const block=document.createElement('div');block.className='source-links bubble-latest-sources';
 for(const source of sources){
  try{const url=new URL(source.url);if(!['https:','http:'].includes(url.protocol))continue;
   const link=document.createElement('a');link.textContent=source.title+' — '+url.hostname;link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';block.append(link);
   if(window.voxelDesktop?.openSource)link.onclick=event=>{event.preventDefault();window.voxelDesktop.openSource(url.href);};
  }catch{}
 }
 $('messages').append(block);$('messages').scrollTop=$('messages').scrollHeight;
}
function appendAction(plan){
 setBubbleExpanded(true);
 const card=document.createElement('section');card.className='action-card';
 const isGroup=plan.kind==='group'||plan.kind==='group_undo',isUndo=plan.kind==='undo'||plan.kind==='group_undo';
 const h=document.createElement('h3');h.textContent=isUndo?'Vista previa: restaurar archivos':isGroup?'Vista previa: reunir archivos encontrados':'Vista previa: organizar el Escritorio';
 const p=document.createElement('p');p.textContent=plan.count+' archivos. '+(isGroup?'Solo se incluyen los resultados recientes. Destino: '+plan.destination+'. ':'')+(plan.layout==='desktop'?'Las carpetas por tipo quedan directamente en el Escritorio y se reutilizan si ya existen. ':'')+'Solo se mueven archivos sueltos; no se borran ni sobrescriben. Carpetas, archivos ocultos y enlaces se omiten. Revisa la lista antes de confirmar.';
 const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Ver todos los movimientos';
 const list=document.createElement('ul');for(const row of plan.items){const item=document.createElement('li');item.textContent=row.from+' → '+row.to;list.append(item);}details.append(summary,list);
 const accept=document.createElement('button'),cancel=document.createElement('button');accept.textContent=isUndo?'Confirmar restauración':'Confirmar movimientos';cancel.textContent='Cancelar';
 cancel.onclick=()=>{accept.disabled=cancel.disabled=true;p.textContent='Cancelado. No ejecuté este plan.';};
 accept.onclick=async()=>{
  if(busy)return;busy=true;$('send').disabled=true;$('new-chat').disabled=true;accept.disabled=cancel.disabled=true;window.voxelDesktop?.publishBusy(true);setState('pensando');
  try{const data=await api('/api/actions/execute',{method:'POST',body:JSON.stringify({plan_id:plan.id,session_id:session,confirmar:true})});append(data.respuesta,'ghost');if(data.resultado?.failed?.length)append('No se movieron estos archivos:\n'+data.resultado.failed.join('\n'),'ghost');p.textContent='Plan ejecutado. El resultado se muestra en la conversación.';}
  catch(error){append(error.message,'ghost',true);p.textContent='No se pudo completar el plan. Pide una vista previa nueva.';}
  finally{busy=false;$('send').disabled=false;$('new-chat').disabled=false;setState('idle');window.voxelDesktop?.publishBusy(false);}
 };
 card.append(h,p,details,accept,cancel);$('messages').append(card);$('messages').scrollTop=$('messages').scrollHeight;
}
if($('speaker-test'))$('speaker-test').onclick=()=>{
 if(recordStream){notice('Detén la grabación antes de probar las bocinas.');return;}
 if(!('speechSynthesis' in window)&&!window.voxelDesktop?.speakNative){notice('No hay síntesis de voz disponible en este sistema.');return;}
 speak('Núcleo en línea. Prueba de salida de audio.',true);
};
function setVoiceStatus(state){
 const button=$('conversation-voice'),status=$('voice-status');
 document.body.classList.toggle('voice-conversation',state!=='off');
 const labels={off:'Voz continua apagada',listening:'Escuchando… termina con una pausa',transcribing:'Transcribiendo tu frase…',thinking:'Preparando respuesta…',replying:'Hablando · micrófono en pausa',paused:'En pausa · termina de escribir o revisa la acción',stopping:'Cerrando micrófono…'};
 if(status){status.textContent=labels[state]||labels.off;status.dataset.state=state;}
 if(button){button.textContent=state==='off'?'Conversar por voz':'■ Terminar voz';button.setAttribute('aria-pressed',String(state!=='off'));button.disabled=state==='stopping';}
 if($('microphone'))$('microphone').disabled=state!=='off';
 if($('auto-voice'))$('auto-voice').disabled=state!=='off';
 if(state==='off'&&!busy&&!speaking)setState('idle');
 publishVoiceBlock();
 if(state==='inactive')notice('Conversación por voz terminada tras dos minutos sin actividad.');
}
function stopVoiceMode(){
 voiceConversation?.stop();cancelSpeech();
}
function voiceAvailable(){
 if(!capabilities.microfono){notice('Activa el micrófono en Ajustes de IA.');return false;}
 if(!capabilities.voz?.supported){notice('No hay un motor de transcripción disponible. Revisa la instalación o el proveedor.');return false;}
 if(capabilities.voz.mode==='local'&&!capabilities.voz.ready){notice('Pulsa Descargar voz local para preparar Whisper antes de conversar.');return false;}
 if(!window.VoxelVoiceCapture||!window.VoxelVoiceSession){notice('No se pudo cargar el modo de voz. Reinicia la app.');return false;}
 return true;
}
async function captureAudio(signal,automatic){
 openingMic=true;publishVoiceBlock();
 let leased=false;
 try{
  if(window.voxelDesktop?.acquireMicrophone){leased=await window.voxelDesktop.acquireMicrophone();if(!leased)throw Error('Activa el micrófono en Ajustes de IA.');}
  if(signal.aborted)throw signal.reason;
  return await window.VoxelVoiceCapture.captureTurn({signal,automatic,pcm:capabilities.voz?.mode==='local',onListening:stop=>{
   openingMic=false;recordStream=true;manualStop=stop;
   $('microphone').textContent=voiceConversation?.active?'Micrófono activo':'■ Detener';
   $('microphone').classList.add('microphone-recording');
  }});
 }finally{
  openingMic=false;recordStream=false;manualStop=null;
  $('microphone').textContent='Micrófono';$('microphone').classList.remove('microphone-recording');
  if(leased)await window.voxelDesktop.releaseMicrophone();publishVoiceBlock();
 }
}
async function transcribeAudio(blob,signal){
 if(blob.size>5000000)throw new Error('El audio supera el límite. Graba un mensaje más corto.');
 if(!blob.size)throw new Error('La grabación quedó vacía. Revisa el micrófono.');
 transcribing=true;setState('pensando');
 try{
  const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(blob);});
  if(signal.aborted)throw signal.reason;
  const data=await api('/api/voice/transcribe',{method:'POST',signal,body:JSON.stringify({audio:encoded,mime:blob.type,consent:true})});
  return String(data.texto||'').trim();
 }finally{transcribing=false;setState('idle');publishVoiceBlock();}
}
const voiceReady=()=>!busy&&!speaking&&!$('message').value.trim()&&!document.querySelector('dialog[open]')&&!document.querySelector('.action-card button:not(:disabled)');
if(window.VoxelVoiceSession)voiceConversation=window.VoxelVoiceSession.createConversation({
 capture:signal=>captureAudio(signal,true),
 transcribe:transcribeAudio,
 ready:voiceReady,
 respond:async(text,signal)=>{
  if(signal.aborted)return false;
  if(!voiceReady()){
   $('message').value=[$('message').value,text].filter(Boolean).join('\n');
   notice('Guardé la transcripción en el borrador. Revísala antes de enviarla.');return false;
  }
  return await send(text,{spoken:true,signal});
 },
 onState:setVoiceStatus,
 onError:error=>{setState('idle');notice(error.message||'Se detuvo la conversación. Revisa el micrófono y la conexión.');}
});
if($('conversation-voice'))$('conversation-voice').onclick=()=>{
 if(voiceConversation?.running){stopVoiceMode();return;}
 if(manualMic||openingMic||transcribing||busy){notice('Termina el turno actual antes de activar la conversación.');return;}
 if(!voiceAvailable())return;
 if(!('speechSynthesis' in window)&&!window.voxelDesktop?.speakNative){notice('No hay salida de voz disponible. Revisa las voces del sistema.');return;}
 if(!voiceReady()){notice('Termina de escribir o revisa la acción pendiente antes de conversar.');return;}
 const confirmed=window.confirm((capabilities.voz.mode==='local'?'Esta sesión transcribirá las frases en este Mac con Whisper. El audio no se enviará a servicios externos; el texto irá a tu servidor de Ollama configurado. El micrófono se cierra mientras responde. Pulsa «Terminar voz» para detenerlo. Las acciones de archivos siguen requiriendo confirmación. ¿Activar conversación por voz?':'Durante esta sesión se escuchará por turnos. Cada frase se enviará a '+capabilities.voz.provider+' para transcribirla y al modelo configurado para responder; puede generar cargos. El micrófono se cierra mientras responde. Pulsa «Terminar voz» para detenerlo. Las acciones de archivos siguen requiriendo confirmación. ¿Activar conversación por voz?'));
 if(!confirmed)return;
 clearTimeout(bubbleRestTimer);cancelSpeech();notice();voiceConversation.start();
};
if($('auto-voice'))$('auto-voice').onclick=()=>{
 if(recordStream||openingMic||transcribing||voiceConversation?.running){notice('Termina la grabación antes de cambiar el modo.');return;}
 autoVoice=!autoVoice;$('auto-voice').textContent='Enviar al pausar: '+(autoVoice?'sí':'no');$('auto-voice').setAttribute('aria-pressed',String(autoVoice));
 notice(autoVoice?'Dictado de una frase: pulsa Micrófono y termina con una pausa. Para varios turnos usa Conversar por voz.':'El dictado esperará que pulses Detener y después Enviar.');
};
if($('microphone'))$('microphone').onclick=async()=>{
 if(voiceConversation?.running)return;
 if(manualStop){manualStop();return;}
 if(openingMic||transcribing){notice('Espera a que termine el acceso o la transcripción.');return;}
 if(busy){notice('Espera a que termine la respuesta.');return;}
 if(!voiceAvailable())return;
 const automatic=autoVoice,recordingSession=session,initialDraft=$('message').value;
 if(!window.confirm(capabilities.voz.mode==='local'?'Se grabará hasta 60 segundos para transcribirlos en este Mac con Whisper. El audio no se enviará a servicios externos. '+(automatic?'La frase se enviará a tu Ollama configurado tras una pausa.':'Podrás revisar el texto antes de enviarlo.')+' ¿Continuar?':'Se grabará hasta 60 segundos y se enviará el audio a '+capabilities.voz.provider+' para transcribirlo. Puede generar un cargo. '+(automatic?'La frase se enviará automáticamente tras una pausa.':'Podrás revisar el texto antes de enviarlo.')+' ¿Continuar?'))return;
 const current=new AbortController();manualMic=current;
 try{
  cancelSpeech();notice('Escuchando… '+(automatic?'Termina con una pausa de 1,6 segundos.':'Pulsa Detener cuando termines.'));
  const blob=await captureAudio(current.signal,automatic);
  if(current.signal.aborted||recordingSession!==session)return;
  if(!blob){notice('No detecté una frase. No envié audio.');return;}
  notice('Transcribiendo con '+capabilities.voz.provider+'…');
  const text=await transcribeAudio(blob,current.signal);
  if(current.signal.aborted||recordingSession!==session)return;
  if(!text)throw new Error('No pude reconocer la frase.');
  if(automatic&&!initialDraft&&!$('message').value&&!busy)await send(text);
  else{$('message').value=[$('message').value,text].filter(Boolean).join('\n');notice('Transcripción lista. Revísala y pulsa Enviar.');$('message').focus();}
 }catch(error){if(!current.signal.aborted)notice(error.message||'No pude abrir el micrófono.');}
 finally{if(manualMic===current)manualMic=null;publishVoiceBlock();}
};
window.voxelDesktop?.onChatClosing?.(()=>{wakeTurn?.abort();stopVoiceMode();manualMic?.abort();});
window.addEventListener('beforeunload',()=>{clearTimeout(localVoiceTimer);clearTimeout(bubbleRestTimer);wakeTurn?.abort();stopVoiceMode();manualMic?.abort();});

if($('tools-settings'))$('tools-settings').onclick=()=>{stopVoiceMode();manualMic?.abort();window.voxelDesktop?.openSettings();};

function updateLocalVoice(info){
 const panel=$('local-voice');if(!panel)return;
 const local=info?.mode==='local';panel.hidden=!local;if(!local){clearTimeout(localVoiceTimer);if(wakeInfo.enabled&&wakeInfo.model)updateLocalVoice(wakeInfo.model);return;}
 if(capabilities.voz?.mode==='local')capabilities.voz=info;
 const downloading=info.download?.state==='downloading';
 const progress=info.download?.received||0,total=info.model_bytes||147951465;
 $('local-voice-note').textContent=!info.supported?'Falta el motor de voz local en esta instalación.':info.ready?'Whisper local listo · audio procesado en este Mac':downloading?'Descargando voz local: '+Math.min(100,Math.floor(progress*100/total))+' %':info.download?.error||'Prepara Whisper una vez para conversar con Ollama sin enviar audio a una API.';
 $('local-voice-install').hidden=info.ready||downloading;
 $('local-voice-install').disabled=!info.supported||!capabilities.microfono||localVoiceRequest;
 $('local-voice-cancel').hidden=!downloading;
 if(!capabilities.microfono&&!info.ready)$('local-voice-note').textContent+=' Activa el micrófono en Skills y permisos.';
 clearTimeout(localVoiceTimer);if(downloading)localVoiceTimer=setTimeout(pollLocalVoice,1000);
 if(info.ready&&wakeInfo.enabled&&wakeInfo.phase==='model')window.voxelDesktop?.refreshWake?.();
}
async function pollLocalVoice(){
 try{const info=await api('/api/voice/local/status',{},8000);updateLocalVoice(info);}
 catch(error){$('local-voice-note').textContent=error.message+' Pulsa comprobar para reintentar.';$('local-voice-install').hidden=false;$('local-voice-install').disabled=false;$('local-voice-install').textContent='Comprobar voz local';$('local-voice-cancel').hidden=true;}
}
if($('local-voice-install'))$('local-voice-install').onclick=async()=>{
 if(localVoiceRequest)return;
 if(!window.confirm('Se descargará una sola vez Whisper base multilingüe (148 MB) desde Hugging Face. Después podrá reconocer tu voz sin conexión. La descarga no envía audio ni requiere API key. ¿Descargar?'))return;
 localVoiceRequest=true;$('local-voice-install').disabled=true;
 try{updateLocalVoice(await api('/api/voice/local/install',{method:'POST',body:JSON.stringify({consent:true})},15000));}
 catch(error){$('local-voice-note').textContent=error.message;}
 finally{localVoiceRequest=false;$('local-voice-install').disabled=false;}
};
if($('local-voice-cancel'))$('local-voice-cancel').onclick=async()=>{
 try{updateLocalVoice(await api('/api/voice/local/cancel',{method:'POST',body:'{}'},8000));}
 catch(error){$('local-voice-note').textContent=error.message;}
};

function publishVoiceBlock(){
 if(!window.voxelDesktop?.publishVoiceInteraction)return;
 const blocked=!!(busy||speaking||transcribing||openingMic||manualMic||voiceConversation?.running||$('message').value.trim()||document.querySelector('dialog[open]')||document.querySelector('.action-card button:not(:disabled)'));
 if(blocked!==lastVoiceBlock){lastVoiceBlock=blocked;window.voxelDesktop.publishVoiceInteraction(blocked);}
}
$('message').addEventListener('input',publishVoiceBlock);
if(typeof MutationObserver!=='undefined')new MutationObserver(publishVoiceBlock).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['open','disabled']});
window.voxelDesktop?.onWakeStatus?.(value=>{
 wakeInfo=value;const panel=$('wake-standby');if(!panel)return;
 panel.hidden=!value.enabled;$('wake-caption').textContent=value.error||value.label;
 $('wake-retry').hidden=value.phase!=='error';
 if(value.enabled&&value.model)updateLocalVoice(value.model);
});
if($('wake-silence'))$('wake-silence').onclick=()=>window.voxelDesktop?.toggleWake?.();
if($('wake-retry'))$('wake-retry').onclick=()=>window.voxelDesktop?.refreshWake?.();
window.voxelDesktop?.onWakeCommand?.(async payload=>{
 if(!payload||typeof payload.id!=='string'||typeof payload.text!=='string'||payload.text.length>6000)return;
 try{
  if(!voiceReady()||manualMic||voiceConversation?.running){
   $('message').value=[$('message').value,payload.text].filter(Boolean).join('\n');
   notice('Escuché tu comando y lo dejé en el borrador. Revisa la acción pendiente o el texto antes de enviarlo.');return;
  }
  const turn=new AbortController();wakeTurn=turn;
  await send(payload.text,{spoken:true,signal:turn.signal});
 }finally{wakeTurn=null;publishVoiceBlock();window.voxelDesktop?.wakeDone?.(payload.id);}
});
initialLoad.then(()=>{publishVoiceBlock();window.voxelDesktop?.chatReady?.();});
