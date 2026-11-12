'use strict';
// El valor de fábrica anterior solo revisaba Documentos. Conserva raíces personalizadas.
function searchRoot(value) {return !value || value==='~/Documents' ? '' : String(value);}
function appSelection(value) {
  if(value===undefined)return ['calculator','notes'];
  if(typeof value==='string')value=value.split(',').map(item=>item.trim()).filter(Boolean);
  if(!Array.isArray(value)||value.length>256||value.some(item=>typeof item!=='string'||!item.trim()||item.length>1024||/[\x00-\x1f\x7f]/.test(item)))throw new Error('La selección de aplicaciones no es válida (máximo 256).');
  const result=[...new Set(value.map(item=>item.trim()))];
  if(Buffer.byteLength(JSON.stringify(result),'utf8')>32000)throw new Error('La selección de aplicaciones es demasiado grande. Reduce la lista.');
  return result;
}
function validateConfig(input, previous = {}) {
  const provider = input.provider || previous.provider || 'ollama';
  if (!['ollama','openai'].includes(provider)) throw new Error('Proveedor no compatible.');
  const url = new URL(String(input.host || ''));
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || (provider==='ollama' && url.pathname !== '/') || url.search || url.hash) throw new Error('Usa el origen de Ollama, sin rutas ni credenciales.');
  if (url.protocol === 'http:' && !['localhost','127.0.0.1','[::1]'].includes(url.hostname)) throw new Error('Un servidor remoto requiere HTTPS o un túnel local.');
  const model = String(input.model || '').trim();
  const memoryModel = String(input.memoryModel || model).trim();
  if (![model,memoryModel].every(x => /^[\w.\-/:]{1,120}$/.test(x))) throw new Error('Indica nombres de modelo válidos.');
  const host=provider==='openai'?url.origin+url.pathname.replace(/\/$/,''):url.origin;
  const sameTarget=String(previous.host||'').replace(/\/$/,'')===host && (previous.provider||'ollama')===provider;
  return {provider,host,model,memoryModel,apiKey:input.clearKey ? '' : (String(input.apiKey || '') || (sameTarget ? previous.apiKey : '') || ''), learning:input.learning === true, webSearch:true, microphone:typeof input.microphone==='boolean'?input.microphone:previous.microphone===true, wakeWord:(typeof input.microphone==='boolean'?input.microphone:previous.microphone===true) && (typeof input.wakeWord==='boolean'?input.wakeWord:previous.wakeWord===true), skills:input.skills === true, allowedApps:appSelection(Object.hasOwn(input,'allowedApps')?input.allowedApps:previous.allowedApps), searchRoot:searchRoot(previous.searchRoot)};
}
function clampBounds(bounds, area, size) {
  return {x:Math.round(Math.max(area.x, Math.min(bounds.x ?? area.x + area.width-size, area.x+area.width-size))), y:Math.round(Math.max(area.y, Math.min(bounds.y ?? area.y+80,area.y+area.height-size-50)))};
}
function allowedURL(value, origin) {
  try { const u = new URL(value); return u.origin === origin && ['/static/compact-chat.html', '/static/overlay.html','/static/desktop-settings.html','/static/setup.html','/static/wake-listener.html'].includes(u.pathname); } catch { return false; }
}
function voxelHit(x,y,size) {
  // Núcleo circular de radio 46 por ciento y controles inferiores.
  if(y>=size+6 && y<=size+44 && x>=size*.12 && x<=size*.88)return true;
  return Math.hypot(x-size/2,y-size/2)<=size*.46;
}
module.exports = {appSelection,searchRoot,validateConfig,clampBounds,allowedURL,voxelHit};
