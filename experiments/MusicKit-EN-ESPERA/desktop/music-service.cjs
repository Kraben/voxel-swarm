'use strict';
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {spawn}=require('node:child_process');
const {randomBytes,randomUUID,timingSafeEqual}=require('node:crypto');
const {createInterface}=require('node:readline');
const commands=new Set(['play','pause','resume','next','previous']);
const message='Falta instalar el componente MusicKit firmado. Consulta MUSIC_KIT.md y compílalo con tu equipo de Apple Developer.';
function validCommand(value){return value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(k=>['action','query'].includes(k))&&commands.has(value.action)&&(value.query===undefined||(typeof value.query==='string'&&value.query.length<=120&&!/[\x00-\x1f\x7f]/.test(value.query)))&&(value.action!=='play'||!!value.query?.trim());}
function createMusicService({runtime,enabled,spawnProcess=spawn,platform=process.platform}){
 let server,child,reader,pending,endpoint,token,generation=0;
 function available(){return platform==='darwin'&&fs.existsSync(path.join(runtime,'VoxelMusic.app','Contents','MacOS','VoxelMusic'));}
 function fail(error){if(pending){clearTimeout(pending.timer);pending.resolve({ok:false,message:error});pending=null;}}
 function stopPlayer(){generation++;fail('El reproductor de MusicKit se ha detenido.');reader?.close();reader=null;const old=child;child=null;old?.kill();}
 function startPlayer(){
  if(child)return;
  if(!available())throw new Error(message);
  const owned=spawnProcess(path.join(runtime,'VoxelMusic.app','Contents','MacOS','VoxelMusic'),[],{stdio:['pipe','pipe','ignore'],shell:false});child=owned;
  owned.on('error',()=>{if(child===owned){fail('No pude iniciar el componente MusicKit. Revisa la firma de Apple.');stopPlayer();}});
  owned.on('exit',()=>{if(child===owned){fail('MusicKit se cerró. Revisa la firma, permisos y App ID.');stopPlayer();}});
  owned.stdin.on('error',()=>{if(child===owned)stopPlayer();});
  reader=createInterface({input:owned.stdout});
  reader.on('line',line=>{
   if(child!==owned||line.length>16384)return;
   let result;try{result=JSON.parse(line);}catch{return;}
   if(pending&&pending.id===result.id){clearTimeout(pending.timer);const resolve=pending.resolve;pending=null;resolve(result);}
  });
 }
 async function request(action,query){
  if(!['status','authorize','disconnect',...commands].includes(action))return {ok:false,message:'Control no válido.'};
  if(commands.has(action)&&!enabled())return {ok:false,message:'Activa Apple Music y las acciones locales en Ajustes.'};
  if(pending)return {ok:false,message:'MusicKit está ocupado. Espera a que termine la acción actual.'};
  try{startPlayer();}catch(error){return {ok:false,available:false,message:error.message};}
  return new Promise(resolve=>{
   const id=randomUUID();const epoch=generation;
   pending={id,resolve,timer:setTimeout(()=>{
    if(epoch===generation){fail('MusicKit tardó demasiado. Revisa si hay una autorización pendiente e inténtalo otra vez.');stopPlayer();}
   },action==='authorize'?90000:25000)};
   child.stdin.write(JSON.stringify({id,action,...(query===undefined?{}:{query})})+'\n');
  });
 }
 async function start(){
  if(server)return {endpoint,token};
  token=randomBytes(48).toString('hex');
  server=http.createServer((req,res)=>{
   const reply=(status,value)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
   const supplied=req.headers.authorization||'',expected='Bearer '+token;
   if(req.method!=='POST'||req.url!=='/music'||req.headers.origin||Buffer.byteLength(supplied)!==Buffer.byteLength(expected)||!timingSafeEqual(Buffer.from(supplied),Buffer.from(expected))){reply(403,{ok:false,message:'Acceso no autorizado.'});req.resume();return;}
   const chunks=[];let size=0,aborted=false;
   req.on('data',data=>{size+=data.length;if(size>2048){aborted=true;req.destroy();}else chunks.push(data);});
   req.on('end',async()=>{
    if(aborted)return;
    let value;try{value=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{reply(400,{ok:false,message:'Comando no válido.'});return;}
    if(!validCommand(value)){reply(400,{ok:false,message:'Comando no válido.'});return;}
    reply(200,await request(value.action,value.query));
   });
  });
  server.requestTimeout=5000;server.headersTimeout=5000;
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  endpoint='http://127.0.0.1:'+server.address().port+'/music';return {endpoint,token};
 }
 async function dispose(){stopPlayer();const owned=server;server=null;if(owned)await new Promise(resolve=>{owned.close(resolve);owned.closeAllConnections();});}
 return {start,request,available,stopPlayer,dispose};
}
module.exports={createMusicService,validCommand};
