'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('voxelWake',Object.freeze({
 phase:value=>ipcRenderer.send('voxel:wake-phase',value),
 command:text=>ipcRenderer.send('voxel:wake-text',text),
 error:text=>ipcRenderer.send('voxel:wake-error',text),
 mute:()=>ipcRenderer.send('voxel:wake-mute')
}));
