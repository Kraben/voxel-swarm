"""Organización local con plan, confirmación y deshacer. Nunca ejecuta shell."""
from pathlib import Path
import json
import os
import re
import stat
import tempfile
import time
import unicodedata
from uuid import UUID, uuid4

CATEGORIES = {
 'Imagenes': {'.png','.jpg','.jpeg','.gif','.webp','.svg','.heic','.tiff'},
 'Documentos': {'.pdf','.doc','.docx','.txt','.md','.csv','.xlsx','.xls','.pptx','.odt','.rtf'},
 'Comprimidos': {'.zip','.gz','.tar','.7z','.rar','.bz2','.xz'},
 'Audio_video': {'.mp3','.wav','.m4a','.ogg','.mp4','.mov','.webm','.mkv'},
 'Codigo_config': {'.py','.js','.ts','.html','.css','.json','.yaml','.yml','.toml','.cfg','.conf','.ino','.sh'},
}

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))

def intent(text):
    text=normalized(text)
    if re.search(r'\b(?:no|nunca)\s+(?:organices|ordenes|organizar|ordenar|muevas|restaures)\b',text):return None
    if 'escritorio' not in text and 'desktop' not in text:return None
    if re.search(r'\b(deshacer|revierte|revertir|restaura|restaurar)\b',text):return 'undo'
    if re.search(r'\b(organiza|organizar|organices|ordena|ordenar|ordenes|organizacion)\b',text):return 'organize'
    return None

def fingerprint(info):return [info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns]
def regular(info):return stat.S_ISREG(info.st_mode)
def valid_name(name):return bool(name) and name not in ('.','..') and '/' not in name and '\\' not in name and '\0' not in name

class DesktopActions:
    def __init__(self,root,data):
        self.root=Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():raise ValueError('No encuentro la carpeta Escritorio.')
        self.data=Path(data)/'acciones';self.data.mkdir(parents=True,exist_ok=True,mode=0o700)
    def load(self,id):
        return json.loads((self.data/(str(UUID(id))+'.json')).read_text())
    def save(self,plan):
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',dir=self.data,delete=False) as out:
            json.dump(plan,out,ensure_ascii=False,indent=2);name=out.name
        os.replace(name,self.data/(plan['id']+'.json'))
    def destination(self,plan,row):
        base=Path() if plan.get('layout')=='desktop' else Path(plan['batch'])
        return base/row.get('folder',row['category'])/row.get('target_name',row['name'])
    def public(self,plan):
        undo=plan['kind']=='undo'
        return {'id':plan['id'],'kind':plan['kind'],'count':len(plan['items']),'ignored':plan.get('ignored',0),'layout':plan.get('layout','batch'),
          'items':[{'from':str(self.destination(plan,r)) if undo else r['name'],
                    'to':r['name'] if undo else str(self.destination(plan,r))} for r in plan['items']]}
    def plan(self,session):
        items=[];ignored=0;used=set()
        folders={normalized(p.name):p.name for p in self.root.iterdir() if p.is_dir() and not p.is_symlink()}
        for entry in sorted(self.root.iterdir(),key=lambda p:p.name.lower()):
            info=entry.lstat()
            if entry.name.startswith('.') or not regular(info) or len(items)>=1000:
                ignored+=1;continue
            category=next((name for name,extensions in CATEGORIES.items() if entry.suffix.lower() in extensions),'Otros')
            folder=folders.get(normalized(category),category)
            destination=self.root/folder
            folder_id=None
            if os.path.lexists(destination):
                destinfo=destination.lstat()
                if not stat.S_ISDIR(destinfo.st_mode):raise ValueError(f'No puedo usar «{folder}» como carpeta de destino. Hay un archivo o enlace con ese nombre. Renómbralo y solicita otro plan.')
                folder_id=[destinfo.st_dev,destinfo.st_ino]
            target=entry.name;index=2
            while os.path.lexists(destination/target) or (folder.casefold(),target.casefold()) in used:
                target=f'{entry.stem}_{index}{entry.suffix}';index+=1
            used.add((folder.casefold(),target.casefold()))
            items.append({'name':entry.name,'category':category,'folder':folder,'folder_id':folder_id,'target_name':target,'fingerprint':fingerprint(info),'state':'planned'})
        plan={'id':str(uuid4()),'kind':'organize','session':session,'created':time.time(),'status':'preview','root':str(self.root),
              'root_id':[self.root.stat().st_dev,self.root.stat().st_ino],
              'layout':'desktop','batch':'',
              'items':items,'ignored':ignored}
        self.save(plan);return self.public(plan)
    def undo_plan(self,session):
        candidates=[]
        for path in self.data.glob('*.json'):
            p=json.loads(path.read_text())
            if p['kind']=='organize' and p['session']==session and p['status'] in ('done','partial','applying') and p['root']==str(self.root):candidates.append(p)
        if not candidates:raise ValueError('No hay una organización de esta conversación para deshacer.')
        previous=max(candidates,key=lambda p:p['created'])
        for row in previous['items']:
            if not valid_name(row['name']) or not valid_name(row.get('target_name',row['name'])) or not valid_name(row.get('folder',row['category'])) or normalized(row.get('folder',row['category']))!=normalized(row['category']) or row['category'] not in {*CATEGORIES,'Otros'}:raise ValueError('Registro de acción inválido.')
            source=self.root/row['name'];destination=self.root/self.destination(previous,row)
            if row['state'] in ('linking','planned','failed') and not source.exists() and destination.exists():
                info=destination.lstat()
                if regular(info) and fingerprint(info)==row['fingerprint']:row['state']='moved'
            elif row['state']=='moved' and source.exists() and not destination.exists():
                info=source.lstat()
                if regular(info) and fingerprint(info)==row['fingerprint']:row['state']='restored'
        self.save(previous)
        rows=[dict(r) for r in previous['items'] if r['state']=='moved']
        if not rows:raise ValueError('No quedan archivos de esa organización para restaurar.')
        plan={**previous,'id':str(uuid4()),'kind':'undo','original':previous['id'],'created':time.time(),'status':'preview','items':rows}
        self.save(plan);return self.public(plan)
    def execute(self,id,session):
        plan=self.load(id)
        if plan['session']!=session or plan['root']!=str(self.root):raise ValueError('El plan no pertenece a esta conversación.')
        if plan['status']!='preview':raise ValueError('Este plan ya se utilizó. Solicita una vista previa nueva.')
        if time.time()-plan['created']>600:raise ValueError('La vista previa venció. Solicita un plan nuevo.')
        flags=os.O_RDONLY|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_NOFOLLOW',0)
        rootfd=os.open(self.root,flags);basefd=None
        try:
            current=os.fstat(rootfd)
            if [current.st_dev,current.st_ino]!=plan['root_id']:raise ValueError('La carpeta cambió. Solicita un plan nuevo.')
            # Ninguna ruta recibida por HTTP decide qué archivos se tocan.
            for row in plan['items']:
                if not valid_name(row['name']) or not valid_name(row.get('target_name',row['name'])) or not valid_name(row.get('folder',row['category'])) or normalized(row.get('folder',row['category']))!=normalized(row['category']) or row['category'] not in {*CATEGORIES,'Otros'}:raise ValueError('Plan inválido.')
            undo=plan['kind']=='undo'
            if not undo:
                for row in plan['items']:
                    info=os.stat(row['name'],dir_fd=rootfd,follow_symlinks=False)
                    if not regular(info) or fingerprint(info)!=row['fingerprint']:raise ValueError('Un archivo cambió desde la vista previa. Solicita un plan nuevo.')
                if plan.get('layout')!='desktop':os.mkdir(plan['batch'],mode=0o700,dir_fd=rootfd)
            basefd=os.dup(rootfd) if plan.get('layout')=='desktop' else os.open(plan['batch'],flags,dir_fd=rootfd)
            plan['status']='applying';self.save(plan)
            moved=0;errors=[]
            for row in plan['items']:
                categoryfd=None
                try:
                    if not undo:
                        try:os.mkdir(row.get('folder',row['category']),mode=0o700,dir_fd=basefd)
                        except FileExistsError:pass
                    categoryfd=os.open(row.get('folder',row['category']),flags,dir_fd=basefd)
                    folder_info=os.fstat(categoryfd)
                    if row.get('folder_id') and [folder_info.st_dev,folder_info.st_ino]!=row['folder_id']:raise ValueError('La carpeta de destino cambió.')
                    row['folder_id']=[folder_info.st_dev,folder_info.st_ino]
                    srcfd,dstfd=(categoryfd,rootfd) if undo else (rootfd,categoryfd)
                    srcname=row.get('target_name',row['name']) if undo else row['name']
                    dstname=row['name'] if undo else row.get('target_name',row['name'])
                    info=os.stat(srcname,dir_fd=srcfd,follow_symlinks=False)
                    if not regular(info) or fingerprint(info)!=row['fingerprint']:raise ValueError('El archivo cambió; no se movió.')
                    row['state']='linking';self.save(plan)
                    # Crear enlace sin sobrescritura y retirar solo la ruta original.
                    os.link(srcname,dstname,src_dir_fd=srcfd,dst_dir_fd=dstfd,follow_symlinks=False)
                    check=os.stat(srcname,dir_fd=srcfd,follow_symlinks=False)
                    if fingerprint(check)!=row['fingerprint']:
                        os.unlink(dstname,dir_fd=dstfd)
                        raise ValueError('El archivo cambió durante la operación.')
                    try:os.unlink(srcname,dir_fd=srcfd)
                    except OSError:
                        os.unlink(dstname,dir_fd=dstfd);raise
                    row['state']='restored' if undo else 'moved';moved+=1
                except Exception:
                    row['state']='failed';errors.append(row['name'])
                finally:
                    if categoryfd is not None:os.close(categoryfd)
                    self.save(plan)
            plan['status']='partial' if errors else 'done';self.save(plan)
            if undo:
                previous=self.load(plan['original'])
                restored={r['name'] for r in plan['items'] if r['state']=='restored'}
                for row in previous['items']:
                    if row['name'] in restored:row['state']='restored'
                if not any(r['state']=='moved' for r in previous['items']):previous['status']='undone'
                self.save(previous)
                # Compatibilidad con planes antiguos: retirar solo carpetas vacías
                # del lote Ghost, sin borrar contenido ni tocar carpetas ajenas.
                if plan.get('layout')!='desktop':
                    for category in {r['category'] for r in plan['items']}:
                        try:os.rmdir(category,dir_fd=basefd)
                        except OSError:pass
                    try:os.rmdir(plan['batch'],dir_fd=rootfd)
                    except OSError:pass
            return {'moved':moved,'failed':errors,'undo':undo,'batch':plan['batch']}
        finally:
            if basefd is not None:os.close(basefd)
            os.close(rootfd)
