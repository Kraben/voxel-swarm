const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {verifyMacBundle}=require('./verify-macos-bundle.cjs');
test('metadatos de macOS separan marca visible y ejecutables internos', {skip:process.platform!=='darwin'},()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'voxel-bundle-test-'));
 function bundle(folder,name,executable,create=true){
  const app=path.join(root,folder);fs.mkdirSync(path.join(app,'Contents','MacOS'),{recursive:true});
  fs.writeFileSync(path.join(app,'Contents','Info.plist'),'<?xml version="1.0"?><plist version="1.0"><dict><key>CFBundleName</key><string>'+name+'</string><key>CFBundleDisplayName</key><string>Enjambre de Vóxeles</string><key>CFBundleExecutable</key><string>'+executable+'</string></dict></plist>');
  if(create)fs.writeFileSync(path.join(app,'Contents','MacOS',executable),'fixture');return app;
 }
 try{
  assert.ok(verifyMacBundle(bundle('Good.app','Enjambre de Voxeles','VoxelSwarm')));
  assert.throws(()=>verifyMacBundle(bundle('Accent.app','Enjambre de Vóxeles','VoxelSwarm')),/ASCII/);
  assert.throws(()=>verifyMacBundle(bundle('AccentExe.app','VoxelSwarm','Vóxeles')),/ASCII/);
  assert.throws(()=>verifyMacBundle(bundle('Missing.app','VoxelSwarm','Missing',false)),/archivo/);
  const broken=bundle('Helper.app','VoxelSwarm','VoxelSwarm');
  bundle('Helper.app/Contents/Frameworks/Helper.app','Vóxeles Helper','Helper');
  assert.throws(()=>verifyMacBundle(broken),/ASCII/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
