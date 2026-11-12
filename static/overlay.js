'use strict';
const names={idle:'En reposo',pensando:'Pensando',hablando:'Hablando'};
const stage=document.getElementById('stage');
window.voxelDesktop?.onSkin(skin=>{if(['cyan','azul','violeta','verde','ambar'].includes(skin))stage.dataset.skin=skin;});
window.voxelDesktop?.onState(state=>{
  if(!Object.hasOwn(names,state))return;
  stage.dataset.state=state;stage.setAttribute('aria-label','Núcleo: '+names[state]);
  document.getElementById('overlay-state').textContent=names[state];
});
document.getElementById('open-chat').onclick=()=>window.voxelDesktop?.openChat();
document.getElementById('overlay-menu').onclick=()=>window.voxelDesktop?.openMenu();

window.voxelDesktop?.onWakeStatus(value=>{
 const button=document.getElementById('wake-toggle');document.body.classList.toggle('wake-enabled',value.enabled);
 button.textContent=value.enabled?'◉':'○';button.title=value.enabled?value.label+' · Clic para silenciar':'Activar Oye Vox desde Ajustes';button.setAttribute('aria-label',button.title);button.setAttribute('aria-pressed',String(value.enabled));
 button.dataset.phase=value.phase;
});
document.getElementById('wake-toggle').onclick=()=>window.voxelDesktop?.toggleWake();
