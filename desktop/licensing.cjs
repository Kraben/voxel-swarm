'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {public_key:publicKey}=require('../commercial/license-public-key.json');
function verifyLicense(token,key=publicKey,now=Math.floor(Date.now()/1000)){
 try{
  if(typeof token!=='string'||token.length>8192||!key)return {plan:'free',reason:'missing'};
  const parts=token.split('.');if(parts.length!==2||parts.some(p=>!/^[-_A-Za-z0-9]+$/.test(p)))throw Error();
  if(!crypto.verify(null,Buffer.from(parts[0]),key,Buffer.from(parts[1],'base64url')))throw Error();
  const claims=JSON.parse(Buffer.from(parts[0],'base64url').toString('utf8'));
  if(claims.v!==1||claims.product!=='voxel-swarm'||claims.plan!=='pro'||typeof claims.id!=='string'||claims.id.length>100||!Number.isSafeInteger(claims.iat)||!Number.isSafeInteger(claims.exp)||claims.iat>now+300||claims.exp<=now||claims.exp<=claims.iat)throw Error();
  return {plan:'pro',expiresAt:claims.exp,id:claims.id};
 }catch{return {plan:'free',reason:'invalid_or_expired'};}
}
function readLicense(file){try{return verifyLicense(JSON.parse(fs.readFileSync(file,'utf8')).token);}catch{return {plan:'free',reason:'missing'};}}
function freeProvider(config){
 try{const u=new URL(config.host);if(u.username||u.password||u.search||u.hash)return false;
  if(config.provider==='ollama')return ['http:','https:'].includes(u.protocol)&&['127.0.0.1','localhost','[::1]'].includes(u.hostname)&&u.pathname==='/';
  return config.provider==='openai'&&u.protocol==='https:'&&u.hostname==='generativelanguage.googleapis.com'&&!u.port&&u.pathname.replace(/\/$/,'')==='/v1beta/openai';
 }catch{return false;}
}
function assertProvider(config,license){if(!freeProvider(config)&&license?.plan!=='pro')throw new Error('Este proveedor requiere Vóxeles Pro. Free incluye Ollama local y Gemini. Cambia de proveedor o activa tu licencia en Ajustes.');return config;}
module.exports={verifyLicense,readLicense,freeProvider,assertProvider};
