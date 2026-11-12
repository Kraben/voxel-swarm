const {test}=require('node:test');const assert=require('node:assert/strict');
const {createDetector}=require('../static/speech-end.js');
test('fin tras voz y pausa; no corta durante una pausa breve',()=>{
 const d=createDetector(0);let result;
 for(let t=100;t<=1000;t+=100)result=d.update(.08,t);
 assert.equal(result,'speaking');
 for(let t=1100;t<=2400;t+=100)result=d.update(.001,t);
 assert.equal(result,'speaking');
 assert.equal(d.update(.08,2500),'speaking');
 for(let t=2600;t<=4100;t+=100)result=d.update(.001,t);
 assert.equal(result,'finished');
});
test('silencio o golpe aislado no se envían como frase',()=>{
 const d=createDetector(0);let result;
 for(let t=100;t<=8000;t+=100)result=d.update(t===500?.08:.001,t);
 assert.equal(result,'empty');
});
