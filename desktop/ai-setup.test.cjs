const {test}=require('node:test');const assert=require('node:assert/strict');const http=require('node:http');
const {prepared,listModels,testModel,pullModel}=require('./ai-setup.cjs');
test('primer inicio: listar, probar API, descargar, errores y cancelar sin tocar modelos reales',async()=>{
 const received=[];
 const server=http.createServer(async(req,res)=>{
  let body='';for await(const part of req)body+=part;
  const input=body?JSON.parse(body):{};received.push({path:req.url,input,auth:req.headers.authorization});res.setHeader('Content-Type','application/json');
  if(req.url==='/api/tags')return res.end(JSON.stringify({models:[{name:'fixture:small'}]}));
  if(req.url==='/api/chat')return res.end(JSON.stringify({message:{content:'listo'}}));
  if(req.url==='/v1/models')return res.end(JSON.stringify({data:[{id:'api-fixture'}]}));
  if(req.url==='/v1/chat/completions')return res.end(JSON.stringify({choices:[{message:{content:'listo'}}]}));
  if(req.url==='/api/pull'){
   if(input.model==='unknown'){res.statusCode=404;return res.end('{}');}
   if(input.model==='cancel'){res.write('{"status":"pulling"}\n');return;}
   if(input.model==='error')return res.end('{"error":"fixture internal error"}\n');
   res.write('{"status":"pulling","total":100,"completed":5');
   res.write('0}\n');
   return res.end(input.model==='truncated'?'':'{"status":"success"}');
  }
  res.statusCode=404;res.end('{}');
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const host='http://127.0.0.1:'+server.address().port;
 const config=prepared({host,model:'fixture:small',skills:false});
 try{
  assert.deepEqual(await listModels(config),['fixture:small']);
  assert.equal(await testModel(config),true);
  const api=prepared({...config,provider:'openai',host:host+'/v1',model:'api-fixture',apiKey:'fixture-key'});
  assert.deepEqual(await listModels(api),['api-fixture']);assert.equal(await testModel(api),true);
  assert.equal(received.find(x=>x.path==='/v1/chat/completions').auth,'Bearer fixture-key');
  assert.deepEqual(received.find(x=>x.path==='/api/chat').input.messages,[{role:'user',content:'Responde únicamente: listo.'}]);
  const updates=[];await pullModel(config,p=>updates.push(p),new AbortController().signal);
  assert.equal(updates[0].percent,50);assert.equal(updates.at(-1).status,'success');
  await assert.rejects(pullModel({...config,model:'unknown'},()=>{},new AbortController().signal),/HTTP 404/);
  await assert.rejects(pullModel({...config,model:'truncated'},()=>{},new AbortController().signal),/interrumpió/);
  await assert.rejects(pullModel({...config,model:'error'},()=>{},new AbortController().signal),/no pudo completar/);
  await assert.rejects(pullModel({...config,host:'https://remote.example'},()=>{},new AbortController().signal),/local/);
  const cancel=new AbortController();
  const pulling=pullModel({...config,model:'cancel'},()=>cancel.abort(),cancel.signal);
  await assert.rejects(pulling,error=>error.name==='AbortError');
 }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
