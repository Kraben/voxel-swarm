'use strict';
const fs=require('node:fs');const path=require('node:path');const {execFileSync}=require('node:child_process');
function read(bundle,key){return execFileSync('/usr/libexec/PlistBuddy',['-c','Print :'+key,path.join(bundle,'Contents','Info.plist')],{encoding:'utf8'}).trim();}
function verifyMacBundle(bundle){
 const validate=dir=>{
  const executable=read(dir,'CFBundleExecutable'),name=read(dir,'CFBundleName');
  if(!/^[\x20-\x7e]+$/.test(executable)||!/^[\x20-\x7e]+$/.test(name))throw new Error('El nombre interno del ejecutable y del bundle debe usar ASCII. Usa CFBundleDisplayName para la marca con acentos.');
  if(executable.includes('/')||executable.includes('\\')||!fs.existsSync(path.join(dir,'Contents','MacOS',executable)))throw new Error('CFBundleExecutable no corresponde a un archivo del paquete.');
 };
 validate(bundle);
 const frameworks=path.join(bundle,'Contents','Frameworks');
 if(fs.existsSync(frameworks))for(const item of fs.readdirSync(frameworks))if(item.endsWith('.app'))validate(path.join(frameworks,item));
 return true;
}
module.exports={verifyMacBundle};
if(require.main===module){verifyMacBundle(process.argv[2]);process.stdout.write('Paquete macOS verificado: ejecutables y helpers consistentes.\n');}
