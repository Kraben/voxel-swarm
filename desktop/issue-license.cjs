'use strict';
// Owner-only tool: not packaged. Keep the private key outside the project/ZIP.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const args=process.argv.slice(2),get=name=>args[args.indexOf(name)+1];
if(!args.includes('--private-key'))throw Error('Indica --private-key con una ruta fuera de ghost-ai. Nunca compartas esa clave.');
const file=path.resolve(get('--private-key')),root=path.resolve(__dirname,'..');
if(file===root||file.startsWith(root+path.sep))throw Error('Guarda la clave privada fuera del proyecto.');
if(args.includes('--init')){
 const existing=JSON.parse(fs.readFileSync(path.join(root,'commercial/license-public-key.json'),'utf8'));
 if(existing.public_key)throw Error('Ya existe un emisor público. No se regenerará para evitar invalidar licencias.');
 if(fs.existsSync(file))throw Error('Ya existe la clave; no se reemplazará.');
 const keys=crypto.generateKeyPairSync('ed25519');
 fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,keys.privateKey.export({type:'pkcs8',format:'pem'}),{mode:0o600,flag:'wx'});
 fs.writeFileSync(path.join(root,'commercial/license-public-key.json'),JSON.stringify({public_key:keys.publicKey.export({type:'spki',format:'pem'})},null,2)+'\n');
 process.stdout.write('Emisor preparado. Solo la clave pública se incluye en la app.\n');
}else{
 const days=Number(get('--days'));const output=args.includes('--output')?path.resolve(get('--output')):null;
 if(!Number.isInteger(days)||days<1||days>3660||!output)throw Error('Indica --days (1–3660) y --output fuera del proyecto.');
 if(output.startsWith(root+path.sep)||output===file)throw Error('La salida debe estar fuera del proyecto y no sobrescribir la clave.');
 const now=Math.floor(Date.now()/1000),claims={v:1,product:'voxel-swarm',plan:'pro',id:crypto.randomUUID(),iat:now,exp:now+days*86400};
 const payload=Buffer.from(JSON.stringify(claims)).toString('base64url');
 const signature=crypto.sign(null,Buffer.from(payload),fs.readFileSync(file)).toString('base64url');
 fs.writeFileSync(output,payload+'.'+signature,{mode:0o600,flag:'wx'});process.stdout.write('Activación firmada generada; no registra ni comprueba un pago.\n');
}
