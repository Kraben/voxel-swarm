const {test}=require('node:test');const assert=require('node:assert/strict');
const catalog=require('./provider-catalog.json');const {prepared,listModels,testModel}=require('./ai-setup.cjs');
test('los proveedores conocidos construyen las rutas compatibles sin reutilizar otra clave',async()=>{
 for(const entry of catalog.filter(item=>item.host)){
  const config=prepared({...entry,model:'fixture-model',apiKey:'fixture-key'}, {host:'https://previous.invalid/v1',provider:'openai',apiKey:'previous-key'});
  let call;
  const fetcher=async(url,options)=>{call={url,options};return {ok:true,json:async()=>({data:[{id:'fixture-model'}],choices:[{message:{content:'listo'}}]})};};
  assert.deepEqual(await listModels(config,fetcher),['fixture-model']);assert.equal(call.url,entry.host+'/models');
  assert.equal(await testModel(config,fetcher),true);assert.equal(call.url,entry.host+'/chat/completions');
  assert.equal(call.options.headers.Authorization,'Bearer fixture-key');
  assert.equal(prepared({...entry,model:'fixture-model'},{host:'https://previous.invalid/v1',apiKey:'previous-key'}).apiKey,'');
  if(entry.id==='gemini')assert.equal(call.options.headers['x-goog-api-client'],'ghost-overlay/0.3.2');
 }
});
