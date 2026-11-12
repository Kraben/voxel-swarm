const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
test('chat a demanda: libera la ventana y espera una respuesta en curso antes de cerrarla',async()=>{
 const handlers=new Map(),windows=[],fetches=[];
 class Window {
  constructor(options){this.options=options;this.events={};this.destroyed=false;this.visible=false;this.sent=[];this.webEvents={};this.webContents={mainFrame:{url:'http://127.0.0.1:9000/static/compact-chat.html'},setWindowOpenHandler(){},on:(name,callback)=>{this.webEvents[name]=callback;},send:(...args)=>this.sent.push(args),session:{setPermissionRequestHandler(){},setPermissionCheckHandler(){}}};windows.push(this);}
  on(name,callback){this.events[name]=callback;}
  once(name,callback){this.events[name]=callback;}
  loadURL(url){this.url=url;}
  isDestroyed(){return this.destroyed;}
  show(){this.visible=true;}
  focus(){}
  setAlwaysOnTop(){}
  setBounds(bounds){this.bounds=bounds;}
  hide(){this.visible=false;}
  close(){let prevented=false;this.events.close?.({preventDefault(){prevented=true;}});if(!prevented){this.destroyed=true;this.events.closed?.();}}
 }
 const electron={BrowserWindow:Window,app:{requestSingleInstanceLock:()=>false,quit(){}},ipcMain:{handle(name,fn){handlers.set(name,fn);},on(name,fn){handlers.set(name,fn);}}};
 const source=fs.readFileSync(path.join(__dirname,'main.cjs'),'utf8');
 const context={fetch:async(url,options)=>{fetches.push({url,options});return {ok:true,json:async()=>({supported:true,apps:[]})};},require:name=>name==='electron'?electron:name==='./policy.cjs'?require('./policy.cjs'):require(name),__dirname,process,URL,AbortSignal,console,setTimeout,clearTimeout,setInterval,clearInterval};
 vm.createContext(context);
 vm.runInContext(source+'\nglobalThis.harness={openChat,publishSkin,openSettings,prepareReconnect(data){support=data;access="fixture-access";overlay=new BrowserWindow({});startEngine=async()=>{};stopEngine=async()=>{};},setSkin(value){ui.skin=value;},setOrigin(value){origin=value;}};',context);
 context.harness.setOrigin('http://127.0.0.1:9000');
 context.harness.openChat();const first=windows[0];
 assert.equal(first.options.width,410);assert.equal(first.options.frame,false);assert.equal(first.options.transparent,true);assert.ok(first.url.includes('/static/compact-chat.html'));
 context.harness.setSkin('violeta');first.webEvents['did-finish-load']();
 assert.deepEqual(first.sent.findLast(row=>row[0]==='voxel:skin'),['voxel:skin','violeta']);
 context.harness.setSkin('ambar');context.harness.publishSkin();
 assert.deepEqual(first.sent.findLast(row=>row[0]==='voxel:skin'),['voxel:skin','ambar']);
 first.close();assert.ok(first.destroyed);
 context.harness.openChat();assert.equal(windows.length,2);const second=windows[1];
 second.webEvents['did-finish-load']();assert.deepEqual(second.sent.findLast(row=>row[0]==='voxel:skin'),['voxel:skin','ambar']);
 context.harness.setSkin('unknown');second.webEvents['did-finish-load']();assert.deepEqual(second.sent.findLast(row=>row[0]==='voxel:skin'),['voxel:skin','cyan']);
 const event={sender:second.webContents,senderFrame:second.webContents.mainFrame};
 handlers.get('voxel:busy')(event,true);handlers.get('voxel:close-chat')(event);
 assert.equal(second.destroyed,false);assert.equal(second.visible,false);
 handlers.get('voxel:busy')(event,false);assert.equal(second.destroyed,true);
 context.harness.openChat();assert.equal(windows.length,3);windows[2].close();
 const tmp=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'voxel-reconnect-'));
 try{
  context.harness.prepareReconnect(tmp);context.harness.openSettings();const settingWindow=windows.at(-1);
  const unauthorized=await handlers.get('voxel:list-apps')({sender:{},senderFrame:{}});assert.equal(unauthorized.ok,false);assert.equal(fetches.length,0);
  const listed=await handlers.get('voxel:list-apps')({sender:settingWindow.webContents,senderFrame:settingWindow.webContents.mainFrame});
  assert.equal(listed.ok,true);assert.equal(fetches[0].url,'http://127.0.0.1:9000/api/apps');assert.equal(fetches[0].options.headers.Authorization,'Bearer fixture-access');
  const result=await handlers.get('voxel:save-settings')({sender:settingWindow.webContents,senderFrame:settingWindow.webContents.mainFrame},{host:'http://127.0.0.1:11434',provider:'ollama',model:'fixture',microphone:true,allowedApps:[]});
  assert.equal(result.ok,true);assert.equal(settingWindow.destroyed,true);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(tmp,'config.json'),'utf8')).allowedApps,[]);
 }finally{fs.rmSync(tmp,{recursive:true,force:true});}
});
