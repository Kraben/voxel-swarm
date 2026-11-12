'use strict';
const {app,BrowserWindow,Menu,Tray,ipcMain,screen,globalShortcut,dialog,nativeImage,shell,powerMonitor} = require('electron');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const {randomBytes,randomUUID} = require('node:crypto');
const {searchRoot,validateConfig,clampBounds,allowedURL,voxelHit} = require('./policy.cjs');
const licenseAccess=require('./licensing.cjs');
const setupAI=require('./ai-setup.cjs');
const providerCatalog=require('./provider-catalog.json');
const speech=require('./speech.cjs').createSpeech();
const {bubbleBounds}=require('./bubble-policy.cjs');
let chatExpanded=false,chatCustomSize=null;
const {createWakeService}=require('./wake-service.cjs');
let speechEpoch=0,speechBusy=false,micLease=false,voiceInteraction=false,systemSleeping=false,systemLocked=false;
let wakeStatus={enabled:false,phase:'off',label:'Oye Vox apagado'};
const skins=['cyan','azul','violeta','verde','ambar'];
if(process.env.GHOST_APP_DATA){const data=path.join(process.env.GHOST_APP_DATA,'chromium');fs.mkdirSync(data,{recursive:true});app.setPath('userData',data);}
const defaults = {provider:'ollama',host:'http://127.0.0.1:11434',model:'ghost-heretic',memoryModel:'ghost-heretic',apiKey:'',learning:true,webSearch:true,microphone:false,wakeWord:false,skills:false,allowedApps:['calculator','notes'],searchRoot:''};
let config = {...defaults}, ui = {size:280,alwaysOnTop:true,ignoreMouse:false}, sessionID=randomUUID();
let setup,activePull,overlay,chat,settings,tray,engine,origin,access,logFd,hitTimer,closing=false,restarting=false,state='idle',support,chatBusy=false,closeChatAfterResponse=false;
const wakeService=createWakeService({
 BrowserWindow,
 preferences:()=>({...preferences(true),preload:path.join(__dirname,'wake-preload.cjs'),autoplayPolicy:'no-user-gesture-required'}),
 secureWindow,
 baseURL:()=>origin,accessToken:()=>access,
 enabled:()=>config.wakeWord&&config.microphone&&!closing,
 canListen:()=>!closing&&!restarting&&!settings&&!setup&&!chatBusy&&!speechBusy&&!micLease&&!voiceInteraction&&!systemSleeping&&!systemLocked,
 openChat,getChat:()=>chat,
 publish:value=>{wakeStatus=value;for(const win of [overlay,chat])if(win&&!win.isDestroyed())win.webContents.send('voxel:wake-status',value);if(tray)tray.setToolTip('Núcleo · '+value.label);}
});
function silenceWake(){config.wakeWord=false;saveJSON(path.join(support,'config.json'),config);wakeService.sync(0);fetch(origin+'/api/voice/local/release',{method:'POST',headers:{Authorization:'Bearer '+access,'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(10000)}).catch(()=>{});}
function toggleWake(){if(config.wakeWord)silenceWake();else openSettings();}
function publishSkin() {
  const skin=skins.includes(ui.skin)?ui.skin:'cyan';
  for(const win of [overlay,chat]) if(win&&!win.isDestroyed()) win.webContents.send('voxel:skin',skin);
}
function licenseFile(){return path.join(support,'license.json');}
function licenseStatus(){return licenseAccess.readLicense(licenseFile());}
function licensedConfig(value){return licenseAccess.assertProvider(value,licenseStatus());}
function readJSON(file,fallback) { try { return JSON.parse(fs.readFileSync(file,'utf8')); } catch { return fallback; } }
function saveJSON(file,value) { const tmp=file+'.tmp'; fs.writeFileSync(tmp,JSON.stringify(value,null,2),{mode:0o600}); fs.renameSync(tmp,file); }
function persistUI() { if (overlay && !overlay.isDestroyed()) Object.assign(ui,overlay.getBounds()); saveJSON(path.join(support,'overlay.json'),{...ui,sessionID}); }
async function freePort() { return new Promise((resolve,reject) => { const server=net.createServer(); server.once('error',reject); server.listen(0,'127.0.0.1',()=> { const port=server.address().port; server.close(()=>resolve(port)); }); }); }
async function startEngine() {
  const port=await freePort(); origin='http://127.0.0.1:'+port; access=randomBytes(48).toString('hex');
  const root=app.isPackaged ? process.resourcesPath : __dirname;
  const binary=path.join(root,'backend',process.platform==='win32' ? 'VoxelBackend.exe' : 'VoxelBackend');
  if (!fs.existsSync(binary)) throw new Error('Falta el motor. Ejecuta prepare_backend.py antes de iniciar o empaquetar.');
  logFd=fs.openSync(path.join(support,'overlay-server.log'),'a');
  engine=spawn(binary,[],{cwd:support,windowsHide:true,stdio:['ignore',logFd,logFd],env:{...process.env,
    GHOST_LICENSE_ENFORCE:'1',GHOST_LICENSE_FILE:licenseFile(),GHOST_DATA_DIR:path.join(support,'data'),GHOST_BIND:'127.0.0.1',GHOST_PORT:String(port),GHOST_PUBLIC:'0',GHOST_API_TOKEN:access,
    GHOST_ALLOWED_HOSTS:'127.0.0.1,localhost',GHOST_ALLOWED_ORIGINS:origin,OLLAMA_HOST:config.host,OLLAMA_API_KEY:config.apiKey,
    GHOST_PROVIDER:config.provider,GHOST_API_BASE:config.host,GHOST_API_KEY:config.apiKey,GHOST_MODEL:config.model,GHOST_MEMORY_MODEL:config.memoryModel,GHOST_LEARNING:config.learning?'1':'0',
    GHOST_ENABLE_SKILLS:process.platform==='darwin' && config.skills?'1':'0',GHOST_ALLOWED_APPS_JSON:JSON.stringify(config.allowedApps),GHOST_SEARCH_ROOT:searchRoot(config.searchRoot),GHOST_ENABLE_WEB:'1',GHOST_ENABLE_MIC:config.microphone?'1':'0',GHOST_WEB_SEARCH:'0'}});
  const owned=engine;
  let launchError;
  owned.once('error',error=> {launchError=error;});
  for (let attempt=0;attempt<120;attempt++) {
    if (launchError) throw launchError;
    if (owned.exitCode !== null) throw new Error('El motor no pudo iniciar. Revisa overlay-server.log.');
    try { const res=await fetch(origin+'/',{signal:AbortSignal.timeout(600)}); if (res.ok) return; } catch {}
    await new Promise(resolve=>setTimeout(resolve,150));
  }
  throw new Error('El motor tardó demasiado en iniciar. Revisa overlay-server.log.');
}
async function stopEngine() {
  wakeService.cancelDelivery();wakeService.pause();
  const owned=engine; engine=null;
  if (owned && owned.pid && owned.exitCode === null) {
    await new Promise(resolve=> {
      const timer=setTimeout(()=>{ owned.kill('SIGKILL'); },4000);
      owned.once('exit',()=>{clearTimeout(timer);resolve();});
      owned.kill();
    });
  }
  if (logFd !== undefined) {fs.closeSync(logFd);logFd=undefined;}
}
function address(route) { return ['/static/compact-chat.html','/static/wake-listener.html'].includes(route) ? origin+route+'#access='+access+'&session='+encodeURIComponent(sessionID) : origin+route; }
function secureWindow(win,route) {
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',(event,url)=>{if (!allowedURL(url,origin)) event.preventDefault();});
  win.webContents.on('will-attach-webview',event=>event.preventDefault());
  win.webContents.session.setPermissionRequestHandler((contents,permission,callback,details)=>{
    const audioOnly=details.mediaTypes?.length&&details.mediaTypes.every(type=>type==='audio');
    callback(!!(config.microphone&&((chat&&!chat.isDestroyed()&&contents===chat.webContents)||(config.wakeWord&&wakeService.window&&!wakeService.window.isDestroyed()&&contents===wakeService.window.webContents))&&permission==='media'&&audioOnly&&allowedURL(contents.getURL(),origin)));
  });
  win.webContents.session.setPermissionCheckHandler((contents,permission,requestingOrigin,details)=>{
    return !!(permission==='media'&&config.microphone&&((chat&&!chat.isDestroyed()&&contents===chat.webContents)||(config.wakeWord&&wakeService.window&&!wakeService.window.isDestroyed()&&contents===wakeService.window.webContents))&&permission==='media'&&details.mediaType!=='video'&&String(requestingOrigin).replace(/\/$/,'')===origin);
  });
  if(win===chat)wakeService.chatLoading();
  win.loadURL(address(route));
}
function preferences(animateInBackground=false) {return {preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true,backgroundThrottling:!animateInBackground};}
function positionChat(){
  if(!chat||chat.isDestroyed()||!overlay||overlay.isDestroyed())return;
  const anchor=overlay.getBounds(),area=screen.getDisplayMatching(anchor).workArea;
  const bounds=bubbleBounds(anchor,area,chatExpanded,chatCustomSize);
  chat.setBounds({x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height});
  chat.webContents.send('voxel:chat-anchor',bounds.side);
}
function openChat() {
  if (chat && !chat.isDestroyed()) {closeChatAfterResponse=false;positionChat();chat.show();chat.focus();return;}
  chatExpanded=false;wakeService.chatLoading();
  chat=new BrowserWindow({title:'Núcleo · Burbuja',width:410,height:390,minWidth:320,minHeight:300,frame:false,transparent:true,hasShadow:false,resizable:true,skipTaskbar:true,backgroundColor:'#00000000',show:false,webPreferences:preferences()});
  chat.setAlwaysOnTop(ui.alwaysOnTop,'floating');positionChat();
  chatBusy=false;closeChatAfterResponse=false;
  chat.webContents.on('did-finish-load',()=>{publishSkin();chat.webContents.send('voxel:wake-status',wakeStatus);});
  secureWindow(chat,'/static/compact-chat.html'); chat.once('ready-to-show',()=>{positionChat();chat.show();});
  chat.on('resized',()=>{if(!chatExpanded&&chat&&!chat.isDestroyed()){const bounds=chat.getBounds();chatCustomSize={width:bounds.width,height:bounds.height};}});
  chat.on('close',event=> {
    chat.webContents.send('voxel:chat-closing');
    if(!closing && chatBusy){event.preventDefault();closeChatAfterResponse=true;chat.hide();}
  });
  chat.on('closed',()=>{
    speech.stop();chat=null;chatBusy=false;micLease=false;voiceInteraction=false;closeChatAfterResponse=false;state='idle';wakeService.chatClosed();
    if(overlay&&!overlay.isDestroyed())overlay.webContents.send('voxel:state','idle');
  });
}
function openSetup() {
  wakeService.cancelDelivery();wakeService.pause();
  if(setup&&!setup.isDestroyed()){setup.show();setup.focus();return;}
  setup=new BrowserWindow({title:'Núcleo · Primer inicio',width:620,height:790,minWidth:520,minHeight:650,backgroundColor:'#000000',webPreferences:preferences()});
  secureWindow(setup,'/static/setup.html');
  setup.on('closed',()=>{activePull?.controller.abort();setup=null;wakeService.sync();});
}
function openSettings() {
  wakeService.cancelDelivery();wakeService.pause();
  if (settings && !settings.isDestroyed()) {settings.show();settings.focus();return;}
  settings=new BrowserWindow({title:'Núcleo · Ajustes',width:620,height:730,resizable:false,backgroundColor:'#000000',webPreferences:preferences()});
  secureWindow(settings,'/static/desktop-settings.html');
  settings.on('closed',()=>{settings=null;wakeService.sync();});
}
function applyOverlay() {
  overlay.setAlwaysOnTop(ui.alwaysOnTop,'floating');
  if(chat&&!chat.isDestroyed())chat.setAlwaysOnTop(ui.alwaysOnTop,'floating');
  overlay.setIgnoreMouseEvents(ui.ignoreMouse,{forward:true});
  if (process.platform!=='win32') overlay.setVisibleOnAllWorkspaces(true,{visibleOnFullScreen:true});
}
function restoreCore() {ui.ignoreMouse=false;overlay.show();applyOverlay();persistUI();}
function overlayMenu() {
  return Menu.buildFromTemplate([
    {label:'Abrir chat',click:openChat},
    {label:config.wakeWord?'Silenciar «Oye Vox»':'Activar «Oye Vox»…',click:toggleWake},
    ...(wakeStatus.phase==='error'?[{label:'Reintentar «Oye Vox»',click:()=>wakeService.retry()}]:[]),
    ...(wakeStatus.phase==='model'?[{label:'Preparar voz local…',click:openChat}]:[]),
    {label:wakeStatus.label,enabled:false},
    {label:'Configurar modelo / primer inicio…',click:openSetup},
    {label:'Ajustes de IA…',click:openSettings},
    {type:'separator'},
    {label:'Siempre encima',type:'checkbox',checked:ui.alwaysOnTop,click:item=>{ui.alwaysOnTop=item.checked;applyOverlay();persistUI();}},
    {label:'Ignorar clics (recuperar con ⌘/Ctrl+⇧+G)',type:'checkbox',checked:ui.ignoreMouse,click:item=>{ui.ignoreMouse=item.checked;applyOverlay();persistUI();}},
    {label:'Tamaño',submenu:[200,280,360].map(size=>({label:String(size)+' px',type:'radio',checked:ui.size===size,click:()=>{ui.size=size;overlay.setSize(size,size+50);persistUI();}}))},
    {label:'Colores del Núcleo',submenu:skins.map(name=>({label:({cyan:'Cyan',azul:'Azul',violeta:'Violeta',verde:'Verde',ambar:'Ámbar'})[name],type:'radio',checked:(ui.skin||'cyan')===name,click:()=>{ui.skin=name;publishSkin();persistUI();}}))},
    {label:'Animaciones',submenu:['idle','pensando','hablando'].map((value,index)=>({label:['Reposo','Pensando','Hablando'][index],click:()=> {state=value;overlay.webContents.send('voxel:state',value);}}))},
    {label:overlay?.isVisible()?'Ocultar Núcleo':'Mostrar Núcleo',click:()=>{if(overlay.isVisible())overlay.hide();else restoreCore();}},
    {label:'Recuperar posición',click:()=>{const area=screen.getPrimaryDisplay().workArea;overlay.setPosition(area.x+area.width-ui.size-30,area.y+80);restoreCore();}},
    {type:'separator'},
    {label:'Salir del Núcleo',click:()=>app.quit()}
  ]);
}
function createOverlay() {
  const area=screen.getDisplayMatching({x:ui.x||0,y:ui.y||0,width:ui.size,height:ui.size+50}).workArea;
  const position=clampBounds(ui,area,ui.size);
  overlay=new BrowserWindow({title:'Enjambre de Vóxeles',...position,width:ui.size,height:ui.size+50,transparent:true,frame:false,hasShadow:false,resizable:false,skipTaskbar:true,show:false,webPreferences:preferences(true)});
  applyOverlay();secureWindow(overlay,'/static/overlay.html');
  overlay.once('ready-to-show',()=>{overlay.showInactive();overlay.webContents.send('voxel:state',state);overlay.webContents.send('voxel:wake-status',wakeStatus);publishSkin();});
  overlay.on('moved',()=>{persistUI();positionChat();});
  overlay.on('resized',positionChat);
  // Consulta el puntero desde el proceso principal: permite atravesar el fondo
  // transparente también cuando el sistema no reenvía mousemove al renderer.
  let ignored=false;
  hitTimer=setInterval(()=>{
    if(!overlay||overlay.isDestroyed()||!overlay.isVisible())return;
    const cursor=screen.getCursorScreenPoint(),bounds=overlay.getBounds();
    const ignore=ui.ignoreMouse||!voxelHit(cursor.x-bounds.x,cursor.y-bounds.y,ui.size);
    if(ignore!==ignored){overlay.setIgnoreMouseEvents(ignore,{forward:true});ignored=ignore;}
  },50);
  overlay.on('close',event=>{if(!closing){event.preventDefault();overlay.hide();}});
}
function trusted(event,win) {return win && !win.isDestroyed() && event.sender===win.webContents && event.senderFrame===win.webContents.mainFrame && allowedURL(event.senderFrame.url,origin);}
ipcMain.handle('voxel:speak',async(event,text)=>{
 if(!trusted(event,chat)||process.platform!=='darwin')return {ok:false};
 const generation=++speechEpoch;speechBusy=true;wakeService.pause();
 try{return await speech.speak(text);}finally{if(generation===speechEpoch){speechBusy=false;wakeService.sync(500);}}
});
ipcMain.handle('voxel:stop-speech',event=>{if(trusted(event,chat))speech.stop();});
ipcMain.handle('voxel:microphone-acquire',event=>{if(!trusted(event,chat)||!config.microphone)return false;micLease=true;wakeService.pause();return true;});
ipcMain.handle('voxel:microphone-release',event=>{if(trusted(event,chat)){micLease=false;wakeService.sync(500);}});
ipcMain.on('voxel:voice-interaction',(event,value)=>{if(trusted(event,chat)&&typeof value==='boolean'){voiceInteraction=value;wakeService.sync(500);}});
ipcMain.on('voxel:chat-ready',event=>{if(trusted(event,chat)){wakeService.chatReady();chat.webContents.send('voxel:wake-status',wakeStatus);}});
ipcMain.on('voxel:wake-done',(event,id)=>{if(trusted(event,chat)&&typeof id==='string')wakeService.finish(id);});
ipcMain.handle('voxel:wake-toggle',event=>{if(trusted(event,chat)||trusted(event,overlay))toggleWake();});
ipcMain.handle('voxel:wake-refresh',event=>{if(trusted(event,chat))wakeService.retry();});
ipcMain.on('voxel:wake-phase',(event,value)=>{if(trusted(event,wakeService.window))wakeService.onPhase(value);});
ipcMain.on('voxel:wake-text',(event,text)=>{if(trusted(event,wakeService.window))wakeService.command(text);});
ipcMain.on('voxel:wake-error',(event,text)=>{if(trusted(event,wakeService.window))wakeService.fail(text);});
ipcMain.on('voxel:wake-mute',event=>{if(trusted(event,wakeService.window))silenceWake();});
ipcMain.handle('voxel:open-settings',event=>{if(trusted(event,chat))openSettings();});
ipcMain.handle('voxel:open-source',(event,value)=>{if(!trusted(event,chat))return;try{const url=new URL(value);if(['https:','http:'].includes(url.protocol)&&!url.username&&!url.password)shell.openExternal(url.href);}catch{}});
ipcMain.handle('voxel:close-chat',event=>{if(trusted(event,chat))chat.close();});
ipcMain.handle('voxel:expand-chat',(event,value)=>{if(trusted(event,chat)&&typeof value==='boolean'){chatExpanded=value;positionChat();}});
ipcMain.handle('voxel:chat',event=>{if(trusted(event,overlay)||trusted(event,chat))openChat();});
ipcMain.handle('voxel:menu',event=>{if(trusted(event,overlay))overlayMenu().popup({window:overlay});});
ipcMain.on('voxel:state',(event,value)=>{if(trusted(event,chat)&&['idle','pensando','hablando'].includes(value)){state=value;overlay.webContents.send('voxel:state',value);}});
ipcMain.on('voxel:busy',(event,value)=>{
  if(!trusted(event,chat)||typeof value!=='boolean')return;
  chatBusy=value;wakeService.sync(500);
  if(!value&&closeChatAfterResponse)chat.close();
});
ipcMain.on('voxel:session',(event,value)=>{if(trusted(event,chat)&&/^[a-f0-9-]{36}$/i.test(value)){sessionID=value;persistUI();}});
ipcMain.handle('voxel:list-apps',async event=>{
  if(!trusted(event,settings))return {ok:false,error:'Ventana no autorizada.'};
  try{
    const response=await fetch(origin+'/api/apps',{headers:{Authorization:'Bearer '+access},signal:AbortSignal.timeout(15000)});
    if(!response.ok)throw new Error('No pude leer las aplicaciones instaladas. Reintenta cuando el motor esté conectado.');
    const data=await response.json();
    return {ok:true,...data};
  }catch(error){return {ok:false,error:error.message};}
});
ipcMain.handle('voxel:license-status',event=>{if(trusted(event,settings)||trusted(event,setup))return licenseStatus();return {plan:'free'};});
ipcMain.handle('voxel:license-activate',(event,token)=>{
 if(!trusted(event,settings)||restarting||chatBusy||activePull)return {ok:false,error:'Espera a que termine la operación actual.'};
 const state=licenseAccess.verifyLicense(typeof token==='string'?token.trim():'');
 if(state.plan!=='pro')return {ok:false,error:'Licencia no válida, vencida o de otro producto. No se cambió tu activación.'};
 saveJSON(licenseFile(),{token:token.trim()});return {ok:true,...state};
});
ipcMain.handle('voxel:license-remove',event=>{
 if(!trusted(event,settings)||restarting||chatBusy||activePull)return {ok:false,error:'Espera a que termine la operación actual.'};
 fs.rmSync(licenseFile(),{force:true});return {ok:true,plan:'free'};
});
ipcMain.handle('voxel:get-settings',event=>{
  if(!trusted(event,settings)&&!trusted(event,setup))throw new Error('Ventana no autorizada');
  const {apiKey,...safe}=config;return {...safe,fresh:!fs.existsSync(path.join(support,'config.json')),hasKey:!!apiKey,platform:process.platform,license:licenseStatus()};
});
ipcMain.handle('voxel:provider-catalog',event=>{if(trusted(event,setup))return providerCatalog.map(entry=>({...entry,plan:entry.id==='gemini'?'free':'pro',locked:entry.id!=='gemini'&&licenseStatus().plan!=='pro'}));throw new Error('Ventana no autorizada.');});
ipcMain.handle('voxel:provider-help',(event,id)=>{if(trusted(event,setup)){const entry=providerCatalog.find(item=>item.id===id);if(entry?.help)shell.openExternal(entry.help);}});
ipcMain.handle('voxel:ollama-download',event=>{if(trusted(event,setup))shell.openExternal('https://ollama.com/download');});
ipcMain.handle('voxel:setup-list',async(event,input)=>{
  if(!trusted(event,setup))return {ok:false,error:'Ventana no autorizada.'};
  try{return {ok:true,models:await setupAI.listModels(licensedConfig(setupAI.prepared(input,config)))};}
  catch(error){return {ok:false,error:setupError(error)};}
});
function setupError(error){
  if(error.name==='TimeoutError')return 'El servidor tardó demasiado. Revisa la conexión y vuelve a intentar.';
  if(error.name==='AbortError')return 'Descarga cancelada. Puedes reintentarlo; Ollama puede conservar las partes descargadas.';
  if(error instanceof TypeError)return 'No pude conectar. Comprueba la dirección y que Ollama o tu servidor estén encendidos.';
  return error.message;
}
ipcMain.handle('voxel:setup-pull',async(event,input)=>{
  if(!trusted(event,setup)||activePull)return {ok:false,error:'Ya hay una descarga o la ventana no está autorizada.'};
  const owner=setup.webContents,controller=new AbortController();activePull={owner,controller};
  try{await setupAI.pullModel(licensedConfig(setupAI.prepared(input,config)),progress=>{if(!owner.isDestroyed())owner.send('voxel:pull-progress',progress);},controller.signal);return {ok:true};}
  catch(error){return {ok:false,error:setupError(error)};}
  finally{activePull=null;}
});
ipcMain.handle('voxel:setup-cancel',event=>{if(trusted(event,setup))activePull?.controller.abort();});
ipcMain.handle('voxel:setup-finish',async(event,input)=>{
  if(!trusted(event,setup)||restarting||activePull||chatBusy)return {ok:false,error:'Espera a que termine la operación actual.'};
  restarting=true;
  try{
    const selected=licensedConfig(setupAI.prepared(input,config));await setupAI.testModel(selected);
    if(selected.memoryModel!==selected.model)await setupAI.testModel({...selected,model:selected.memoryModel});
    config=selected;saveJSON(path.join(support,'config.json'),config);
    await stopEngine();await startEngine();
    saveJSON(path.join(support,'setup-complete.json'),{version:1,provider:config.provider});
    secureWindow(overlay,'/static/overlay.html');if(chat&&!chat.isDestroyed())secureWindow(chat,'/static/compact-chat.html');
    if(setup&&!setup.isDestroyed())setup.close();restarting=false;wakeService.retry();return {ok:true};
  }catch(error){restarting=false;return {ok:false,error:setupError(error)};}
});
ipcMain.handle('voxel:save-settings',async(event,input)=>{
  if(!trusted(event,settings)||restarting)return {ok:false,error:'Operación no disponible.'};
  try {
    config=licensedConfig(validateConfig(input,config));saveJSON(path.join(support,'config.json'),config);restarting=true;
    await stopEngine();await startEngine();
    secureWindow(overlay,'/static/overlay.html');if(chat&&!chat.isDestroyed())secureWindow(chat,'/static/compact-chat.html');
    if(settings&&!settings.isDestroyed())settings.close();restarting=false;wakeService.retry();return {ok:true};
  } catch(error) {restarting=false;return {ok:false,error:error.message};}
});
if(!app.requestSingleInstanceLock()){app.quit();}else{
  app.on('second-instance',()=>{if(overlay)restoreCore();});
  app.whenReady().then(async()=>{
    support=process.env.GHOST_APP_DATA || path.join(app.getPath('appData'),'Ghost AI');
    fs.mkdirSync(support,{recursive:true});
    config={...defaults,...readJSON(path.join(support,'config.json'),{})};config=validateConfig(config,config);
    const saved=readJSON(path.join(support,'overlay.json'),{});
    ui={...ui,...saved,size:[200,280,360].includes(saved.size)?saved.size:280,ignoreMouse:false};
    if(typeof saved.sessionID==='string'&&/^[a-f0-9-]{36}$/i.test(saved.sessionID))sessionID=saved.sessionID;
    try {
      await startEngine();createOverlay();
      const icon=nativeImage.createFromPath(path.join(__dirname,'tray.png')).resize({width:20,height:20});tray=new Tray(icon);tray.setToolTip('Núcleo · Abrir chat');
      tray.on('click',openChat);tray.on('right-click',()=>tray.popUpContextMenu(overlayMenu()));
      const shortcut=globalShortcut.register('CommandOrControl+Shift+G',restoreCore);
      Menu.setApplicationMenu(Menu.buildFromTemplate([
        ...(process.platform==='darwin'?[{label:'Enjambre de Vóxeles',submenu:[{role:'about'},{type:'separator'},{label:'Configurar modelo / primer inicio…',click:openSetup},
    {label:'Ajustes de IA…',click:openSettings},{label:'Mostrar Núcleo',click:restoreCore},{type:'separator'},{role:'quit'}]}]:[]),
        {label:'Enjambre de Vóxeles',submenu:[{label:'Abrir chat',click:openChat},{label:'Mostrar Núcleo',click:restoreCore},{label:'Configurar modelo / primer inicio…',click:openSetup},
    {label:'Ajustes de IA…',click:openSettings},{label:'Salir',click:()=>app.quit()}]},
        {role:'editMenu'}
      ]));
      if(!shortcut)dialog.showMessageBox({message:'No se pudo registrar el atajo de recuperación. Puedes recuperar Núcleo desde el icono de la barra de menú o bandeja.',type:'info'});
      if(!fs.existsSync(path.join(support,'setup-complete.json')))openSetup();
      wakeService.sync();
      powerMonitor?.on('suspend',()=>{systemSleeping=true;speech.stop();wakeService.pause();});
      powerMonitor?.on('resume',()=>{systemSleeping=false;wakeService.sync(1000);});
      powerMonitor?.on('lock-screen',()=>{systemLocked=true;speech.stop();wakeService.pause();});
      powerMonitor?.on('unlock-screen',()=>{systemLocked=false;wakeService.sync(1000);});
    } catch(error) {dialog.showErrorBox('No se pudo iniciar Núcleo',error.message);app.quit();}
  });
  app.on('activate',()=>{if(overlay)restoreCore();});
  app.on('window-all-closed',()=>{});
  app.on('before-quit',event=>{
    if(closing)return;event.preventDefault();closing=true;
    wakeService.dispose();speech.stop();activePull?.controller.abort();if(overlay&&!overlay.isDestroyed())persistUI();globalShortcut.unregisterAll();clearInterval(hitTimer);
    stopEngine().finally(()=>app.quit());
  });
}
