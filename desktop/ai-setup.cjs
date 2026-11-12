'use strict';
const {validateConfig}=require('./policy.cjs');
function prepared(input,previous={}){return validateConfig(input,previous);}
function headers(config){return {'Content-Type':'application/json',...(new URL(config.host).hostname==='generativelanguage.googleapis.com'?{'x-goog-api-client':'ghost-overlay/0.3.2'}:{}),...(config.apiKey?{Authorization:'Bearer '+config.apiKey}:{})};}
async function request(config,route,body,fetcher=fetch){
 const response=await fetcher(config.host+route,{method:body?'POST':'GET',headers:headers(config),...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(90000),redirect:'error'});
 if(!response.ok)throw new Error('El servidor respondió HTTP '+response.status+'. Revisa URL, clave y modelo.');
 return response.json();
}
async function listModels(config,fetcher=fetch){
 const data=await request(config,config.provider==='openai'?'/models':'/api/tags',null,fetcher);
 const rows=config.provider==='openai'?data.data:data.models;
 if(!Array.isArray(rows))throw new Error('La respuesta no contiene una lista de modelos compatible.');
 return rows.map(m=>config.provider==='openai'?m.id:(m.name||m.model)).filter(x=>typeof x==='string').slice(0,500);
}
async function testModel(config,fetcher=fetch){
 const messages=[{role:'user',content:'Responde únicamente: listo.'}];
 const data=await request(config,config.provider==='openai'?'/chat/completions':'/api/chat',{model:config.model,messages,stream:false},fetcher);
 const text=config.provider==='openai'?data.choices?.[0]?.message?.content:data.message?.content;
 if(typeof text!=='string'||!text.trim())throw new Error('El modelo no devolvió texto. Revisa su compatibilidad para chat.');
 return true;
}
async function pullModel(config,onProgress,signal,fetcher=fetch){
 const url=new URL(config.host);
 if(config.provider!=='ollama'||!['localhost','127.0.0.1','[::1]'].includes(url.hostname))throw new Error('La descarga solo está permitida en Ollama local.');
 const response=await fetcher(config.host+'/api/pull',{method:'POST',headers:headers(config),body:JSON.stringify({model:config.model,stream:true}),signal:AbortSignal.any([signal,AbortSignal.timeout(7200000)]),redirect:'error'});
 if(!response.ok)throw new Error('No se pudo descargar el modelo (HTTP '+response.status+'). Comprueba el nombre y el espacio disponible.');
 let pending='',success=false;
 const decoder=new TextDecoder();
 function line(value){
  if(!value.trim())return;
  const row=JSON.parse(value);
  if(row.error)throw new Error('Ollama no pudo completar la descarga. Revisa el nombre del modelo, tu conexión y el espacio disponible.');
  const total=Number(row.total)||0,completed=Number(row.completed)||0;
  onProgress({status:String(row.status||'Descargando').slice(0,160),total,completed,percent:total?Math.max(0,Math.min(100,Math.round(completed/total*100))):null});
  if(row.status==='success')success=true;
 }
 for await(const chunk of response.body){
  pending+=decoder.decode(chunk,{stream:true});
  if(pending.length>1000000)throw new Error('La respuesta de descarga no es válida.');
  let end;while((end=pending.indexOf('\n'))>=0){line(pending.slice(0,end));pending=pending.slice(end+1);}
 }
 pending+=decoder.decode();line(pending);
 if(!success)throw new Error('La descarga se interrumpió antes de confirmar el modelo. Puedes reintentarlo.');
 return true;
}
module.exports={prepared,listModels,testModel,pullModel};
