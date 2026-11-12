const {test}=require('node:test');const assert=require('node:assert/strict');
const {wakePhrase,muteCommand,createSegmenter}=require('../static/wake-detection.js');
test('la frase de activación debe estar al principio y conserva el comando',()=>{
 assert.deepEqual(wakePhrase('Oye Vox, abre Calculadora.'),{command:'abre Calculadora.'});
 assert.deepEqual(wakePhrase('¡Oye, Vox!'),{command:''});
 assert.deepEqual(wakePhrase('Oye Box abre Safari'),{command:'abre Safari'});
 for(const text of ['abre Safari','Dijo oye Vox en un video','Oye voz','hoy vox','oye boxeo','Oye Voxeles'])assert.equal(wakePhrase(text),null,text);
 assert.equal(muteCommand('Deja de escuchar.'),true);assert.equal(muteCommand('silencia el micrófono'),true);assert.equal(muteCommand('abre notas'),false);
});
test('la segmentación descarta silencio y golpes, conserva preaudio y finaliza por pausa',()=>{
 const rate=16000,d=createSegmenter(rate),frame=value=>new Float32Array(1600).fill(value);
 for(let i=0;i<1200;i++)assert.equal(d.push(frame(.001)),null);
 d.push(frame(.08));for(let i=0;i<5;i++)assert.equal(d.push(frame(.001)),null);assert.equal(d.active,false);
 for(let i=0;i<5;i++)assert.equal(d.push(frame(.08)),null);
 let result;for(let i=0;i<9;i++)result=d.push(frame(.001));
 assert.ok(result);assert.ok(result.reduce((sum,x)=>sum+x.length,0)<rate*3);assert.equal(d.active,false);
});
test('voz sin pausa termina al límite y no acumula un búfer ilimitado',()=>{
 const d=createSegmenter(16000,{maxMs:2000});let result;
 for(let i=0;i<20;i++)result=d.push(new Float32Array(1600).fill(.08));
 assert.ok(result);assert.equal(result.reduce((n,row)=>n+row.length,0),32000);assert.equal(d.active,false);
});
