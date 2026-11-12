const {test}=require('node:test');const assert=require('node:assert/strict');const {EventEmitter}=require('node:events');const {createSpeech}=require('./speech.cjs');
test('la voz nativa usa stdin, se puede detener y no convierte texto en comandos',async()=>{
 const calls=[];
 const speaker=createSpeech((binary,args,options)=>{
  const child=new EventEmitter();child.stdin=new EventEmitter();child.stdin.end=text=>{child.text=text;};child.kill=()=>child.emit('close',null);
  calls.push({binary,args,options,child});return child;
 });
 const playing=speaker.speak('Hola; $(comando) --file=privado');
 assert.equal(calls[0].binary,'/usr/bin/say');assert.deepEqual(calls[0].args,[]);assert.equal(calls[0].options.shell,false);
 assert.equal(calls[0].child.text,'Hola; $(comando) --file=privado');calls[0].child.emit('close',0);assert.equal((await playing).ok,true);
 const stopped=speaker.speak('Otra respuesta');speaker.stop();assert.equal((await stopped).cancelled,true);
 assert.equal((await speaker.speak('')).ok,false);
});
