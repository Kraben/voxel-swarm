const {test}=require('node:test');const assert=require('node:assert/strict');const {bubbleBounds}=require('./bubble-policy.cjs');
test('burbuja junto al avatar, con espacio para la pantalla y para revisar planes',()=>{
 const area={x:0,y:0,width:1440,height:900};
 const resized=bubbleBounds({x:1100,y:90,width:280,height:330},area,false,{width:540,height:470});assert.equal(resized.width,540);assert.equal(resized.height,470);
 const expanded=bubbleBounds({x:1100,y:90,width:280,height:330},area,true,{width:540,height:470});assert.equal(expanded.width,540);assert.equal(expanded.height,660);
 let b=bubbleBounds({x:1100,y:90,width:280,height:330},area);
 assert.equal(b.side,'left');assert.equal(b.width,410);assert.equal(b.height,390);assert.ok(b.x+b.width<1100);
 b=bubbleBounds({x:10,y:90,width:280,height:330},area,true);
 assert.equal(b.side,'right');assert.equal(b.width,480);assert.equal(b.height,660);assert.ok(b.x>280);
 for(const screen of [{x:-1280,y:0,width:1280,height:720},{x:0,y:0,width:360,height:600}]){
  b=bubbleBounds({x:screen.x+20,y:screen.height-200,width:280,height:330},screen,true);
  assert.ok(b.x>=screen.x);assert.ok(b.y>=screen.y);assert.ok(b.x+b.width<=screen.x+screen.width);assert.ok(b.y+b.height<=screen.y+screen.height);
 }
});
