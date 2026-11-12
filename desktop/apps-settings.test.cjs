const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const NOTES={id:'/System/Applications/Notes.app',name:'Notas',command:'Notes',aliases:['notes','notas'],path:'/System/Applications/Notes.app'};
const SAFARI={id:'/Applications/Safari.app',name:'Safari',command:'Safari',aliases:['safari'],path:'/Applications/Safari.app'};
function fixture({allowedApps='notes',catalogError=false,settingsError=false}={}){
 const fields=new Map(),saved=[];let apps=[NOTES,SAFARI];
 class Element{
  constructor(){this.value='';this.checked=false;this.children=[];this.disabled=false;}
  append(...children){this.children.push(...children);}replaceChildren(...children){this.children=children;}setAttribute(name,value){this[name]=value;}
 }
 for(const match of fs.readFileSync(path.join(__dirname,'../static/desktop-settings.html'),'utf8').matchAll(/id="([^"]+)"/g))fields.set(match[1],new Element());
 const context={document:{getElementById:id=>fields.get(id),createElement:()=>new Element()},window:{voxelDesktop:{licenseStatus:async()=>({plan:'free'}),activateLicense:async()=>({ok:false,error:'No válida'}),removeLicense:async()=>({ok:true,plan:'free'}),getSettings:async()=>{if(settingsError)throw Error('unavailable');return {host:'http://127.0.0.1:11434',model:'fixture',memoryModel:'fixture',skills:true,microphone:true,platform:'darwin',allowedApps};},listInstalledApps:async()=>catalogError?{ok:false,error:'Sin motor'}:{ok:true,supported:true,apps},saveSettings:async input=>{saved.push(input);return {ok:true};}}}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/desktop-settings.js'),'utf8'),context);
 return {fields,saved,setApps:rows=>{apps=rows;},rows:()=>fields.get('apps-list').children,save:()=>fields.get('desktop-config').onsubmit({preventDefault(){}})};
}
test('ajustes: selección, filtro y guardado conservan las apps elegidas por nombre antiguo',async()=>{
 const f=fixture();await tick();const notes=f.rows().find(row=>row.children[1].children[0].textContent==='Notas');assert.equal(notes.children[0].checked,true);
 const safari=f.rows().find(row=>row.children[1].children[0].textContent==='Safari');safari.children[0].checked=true;safari.children[0].onchange();
 f.fields.get('apps-search').value='safari';f.fields.get('apps-search').oninput();assert.equal(f.rows().length,1);
 await f.save();assert.deepEqual(Array.from(f.saved[0].allowedApps).sort(),[NOTES.id,SAFARI.id].sort());
});
test('quitar toda la selección guarda un array vacío; no reactiva apps por defecto',async()=>{
 const f=fixture();await tick();f.fields.get('apps-clear').onclick();await f.save();assert.deepEqual(Array.from(f.saved[0].allowedApps),[]);
});
test('actualizar no olvida permisos de apps temporalmente ausentes y permite revocarlos',async()=>{
 const f=fixture({allowedApps:[NOTES.id]});await tick();f.setApps([SAFARI]);await f.fields.get('apps-refresh').onclick();
 const unavailable=f.rows().find(row=>row.className.includes('app-missing'));assert.equal(unavailable.children[0].checked,true);
 unavailable.children[0].checked=false;unavailable.children[0].onchange();await f.save();assert.deepEqual(Array.from(f.saved[0].allowedApps),[]);
});
test('si no hay catálogo, guardar los demás ajustes conserva los permisos anteriores',async()=>{
 const f=fixture({catalogError:true});await tick();await f.save();assert.equal(Object.hasOwn(f.saved[0],'allowedApps'),false);assert.match(f.fields.get('apps-status').textContent,/Sin motor/);
});
test('un error al leer configuración impide sobrescribirla con un formulario vacío',async()=>{
 const f=fixture({settingsError:true});await tick();await f.save();assert.equal(f.fields.get('config-save').disabled,true);assert.equal(f.saved.length,0);
});

test('activar Oye Vox habilita el micrófono y apagar el micrófono desactiva la escucha',async()=>{
 const f=fixture();await tick();f.fields.get('microphone').checked=false;f.fields.get('wake-word').checked=true;f.fields.get('wake-word').onchange();
 assert.equal(f.fields.get('microphone').checked,true);await f.save();assert.equal(f.saved[0].wakeWord,true);
 f.fields.get('microphone').checked=false;f.fields.get('microphone').onchange();assert.equal(f.fields.get('wake-word').checked,false);
});
