const {test}=require('node:test');const assert=require('node:assert/strict');
const {validateConfig,clampBounds,allowedURL,voxelHit}=require('./policy.cjs');
test('configuración remota: HTTPS y sin credenciales en URL',()=>{
 const input={host:'http://127.0.0.1:11434',model:'ghost-heretic',learning:true,skills:false};
 assert.equal(validateConfig(input).host,'http://127.0.0.1:11434');
 assert.throws(()=>validateConfig({...input,host:'http://remote.example'}));
 assert.throws(()=>validateConfig({...input,host:'https://user:password@example.com'}));
 assert.throws(()=>validateConfig({...input,host:'https://example.com/api'}));
 assert.throws(()=>validateConfig({...input,model:';rm -rf /'}));
 assert.equal(validateConfig({...input,apiKey:''},{host:input.host,apiKey:'private'}).apiKey,'private');
 assert.equal(validateConfig({...input,host:'https://other.example'},{host:input.host,apiKey:'private'}).apiKey,'');
 assert.equal(validateConfig({...input,clearKey:true},{host:input.host,apiKey:'private'}).apiKey,'');
});
test('no navegar fuera del servicio privado',()=>{
 assert.ok(allowedURL('http://127.0.0.1:8000/static/overlay.html#access=x','http://127.0.0.1:8000'));
 assert.ok(!allowedURL('https://example.com/','http://127.0.0.1:8000'));
 assert.ok(!allowedURL('http://127.0.0.1:8000/static/desktop-settings.js','http://127.0.0.1:8000'));
});
test('posición recuperable tras desconectar un monitor',()=>{
 assert.deepEqual(clampBounds({x:8000,y:-2000},{x:0,y:0,width:1440,height:900},280),{x:1160,y:0});
 assert.deepEqual(clampBounds({x:-900,y:100},{x:-1440,y:0,width:1440,height:900},280),{x:-900,y:100});
});
test('el núcleo circular captura clics; esquinas y exterior se atraviesan',()=>{
 assert.ok(voxelHit(140,140,280));assert.ok(voxelHit(140,35,280));
 assert.ok(!voxelHit(0,0,280));assert.ok(!voxelHit(279,0,280));
 assert.ok(!voxelHit(-500,-500,280));
 assert.ok(voxelHit(140,310,280));
});

test('búsqueda rápida migra el valor antiguo y conserva carpetas personalizadas',()=>{
 const {searchRoot}=require('./policy.cjs');
 assert.equal(searchRoot('~/Documents'),'');assert.equal(searchRoot(''),'');
 assert.equal(searchRoot('/custom/folder'),'/custom/folder');
 assert.equal(validateConfig({host:'http://localhost:11434',model:'test'}, {searchRoot:'~/Documents'}).searchRoot,'');
 assert.equal(validateConfig({host:'http://localhost:11434',model:'test'}, {searchRoot:'/custom/folder'}).searchRoot,'/custom/folder');
});

test('selector de apps: conserva lista vacía, migra nombres y mantiene permisos al cambiar de proveedor',()=>{
 const {appSelection}=require('./policy.cjs');
 assert.deepEqual(appSelection('calculator,notes'),['calculator','notes']);assert.deepEqual(appSelection(''),[]);
 const base={host:'http://127.0.0.1:11434',model:'fixture',allowedApps:[]};
 const empty=validateConfig(base,{allowedApps:['calculator']});assert.deepEqual(empty.allowedApps,[]);
 assert.deepEqual(validateConfig({host:base.host,model:base.model},empty).allowedApps,[]);
 const picked=validateConfig({...base,allowedApps:['/Applications/Spotify.app','/Applications/Spotify.app','/Applications/App, Pro.app']});
 assert.deepEqual(picked.allowedApps,['/Applications/Spotify.app','/Applications/App, Pro.app']);
 assert.deepEqual(validateConfig({host:'https://api.example/v1',provider:'openai',model:'fixture'},picked).allowedApps,picked.allowedApps);
 assert.throws(()=>validateConfig({...base,allowedApps:{all:true}}),/selección/);
 assert.throws(()=>appSelection(['/Applications/Notes.app\ncommand']),/selección/);
 assert.throws(()=>appSelection(new Array(257).fill('/Applications/Test.app')),/256/);
});

test('Oye Vox requiere micrófono y conserva su selección al cambiar de modelo',()=>{
 const config=validateConfig({host:'http://127.0.0.1:11434',model:'fixture',microphone:true,wakeWord:true});assert.equal(config.wakeWord,true);
 assert.equal(validateConfig({host:config.host,model:'other'},config).wakeWord,true);
 assert.equal(validateConfig({...config,microphone:false},config).wakeWord,false);
 assert.equal(validateConfig({...config,wakeWord:false},config).wakeWord,false);
});
