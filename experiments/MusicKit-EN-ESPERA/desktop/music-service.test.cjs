'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');const {PassThrough,Writable}=require('node:stream');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createMusicService,validCommand}=require('./music-service.cjs');
test('MusicKit validates fixed commands and blocks arbitrary fields',()=>{
 assert.ok(validCommand({action:'play',query:'Rammstein'}));
 for(const value of [{action:'shell'},{action:'play',query:''},{action:'play',query:'x\n'},{action:'pause',script:'bad'},{action:'authorize'}])assert.ok(!validCommand(value));
});
test('MusicKit bridge rejects unauthenticated, browser-origin and invalid requests; execution uses private stdin',async()=>{
 const runtime=fs.mkdtempSync(path.join(os.tmpdir(),'vox-music-'));const binary=path.join(runtime,'VoxelMusic.app/Contents/MacOS/VoxelMusic');fs.mkdirSync(path.dirname(binary),{recursive:true});fs.writeFileSync(binary,'');
 let calls=[],enabled=true,owned;
 const service=createMusicService({runtime,platform:'darwin',enabled:()=>enabled,spawnProcess:(file,args,options)=>{
  assert.equal(file,binary);assert.deepEqual(args,[]);assert.equal(options.shell,false);
  owned=new EventEmitter();owned.stdout=new PassThrough();owned.kill=()=>{owned.emit('exit',0);};
  owned.stdin=new Writable({write(data,encoding,done){const request=JSON.parse(data);calls.push(request);queueMicrotask(()=>owned.stdout.write(JSON.stringify({id:request.id,ok:true,message:'Resultado de prueba'})+'\n'));done();}});return owned;
 }});
 try{
  const {endpoint,token}=await service.start();const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
  assert.equal((await fetch(endpoint,{method:'POST',body:'{}'})).status,403);
  assert.equal((await fetch(endpoint,{method:'POST',headers:{...headers,Origin:'https://example.org'},body:'{}'})).status,403);
  assert.equal((await fetch(endpoint,{method:'POST',headers,body:JSON.stringify({action:'authorize'})})).status,400);
  assert.equal(calls.length,0);
  const result=await fetch(endpoint,{method:'POST',headers,body:JSON.stringify({action:'play',query:'Rammstein'})});
  assert.equal((await result.json()).message,'Resultado de prueba');assert.equal(calls[0].query,'Rammstein');
  enabled=false;const denied=await service.request('next');assert.equal(denied.ok,false);assert.equal(calls.length,1);
  assert.equal((await service.request('disconnect')).ok,true);
 }finally{await service.dispose();fs.rmSync(runtime,{recursive:true,force:true});}
});
test('missing signed MusicKit does not claim playback or start another player',async()=>{
 const service=createMusicService({runtime:'/missing/voxel-musickit',enabled:()=>true,platform:'darwin',spawnProcess:()=>assert.fail('must not launch')});
 assert.equal((await service.request('play','Rammstein')).available,false);await service.dispose();
});
