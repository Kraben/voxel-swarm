"""Agrupar solo resultados locales recientes, con vista previa, confirmación y deshacer."""
import json,os,re,stat,tempfile,time
from pathlib import Path
from uuid import UUID,uuid4
from datetime import datetime
from desktop_actions import normalized,fingerprint,regular

FLAGS=os.O_RDONLY|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_NOFOLLOW',0)

def intent(text):
    t=normalized(text)
    if re.search(r'\b(?:no|nunca)\b.{0,25}\b(?:muev|mov|organiz|agrup|reun)',t):return None
    if re.search(r'\b(?:deshacer|revierte|revertir|restaura)\b',t) and re.search(r'agrup|archivos encontrados|esos archivos',t):return 'undo'
    if re.search(r'\b(?:organizar|organiza|poner|pon|mover|mueve|reunir|reune|agrupar|agrupa)\b',t) and 'carpeta' in t and re.search(r'\b(?:archivos|resultados)\b',t):return 'group'
    return None

def open_dir(path):
    p=Path(path)
    if not p.is_absolute() or '..' in p.parts:raise ValueError('Ruta local inválida.')
    if p.is_symlink():raise ValueError('Enlace no permitido.')
    return os.open(str(p),FLAGS)

def directory_id(fd):
    info=os.fstat(fd);return [info.st_dev,info.st_ino]

class GroupActions:
    def __init__(self,data):
        self.data=Path(data)/'agrupaciones';self.data.mkdir(parents=True,exist_ok=True,mode=0o700)
    def read(self,id):return json.loads((self.data/(str(UUID(id))+'.json')).read_text())
    def save(self,p):
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',dir=self.data,delete=False) as f:json.dump(p,f,ensure_ascii=False);name=f.name
        os.replace(name,self.data/(p['id']+'.json'))
    def remember(self,session,paths):
        rows=[]
        for path in paths[:30]:
            p=Path(path)
            try:
                fd=open_dir(p.parent)
                try:
                    info=os.stat(p.name,dir_fd=fd,follow_symlinks=False)
                    if regular(info):rows.append({'source':str(p),'parent_id':directory_id(fd),'fingerprint':fingerprint(info)})
                finally:os.close(fd)
            except OSError:continue
        self.save({'id':str(UUID(session)),'kind':'search','session':session,'created':time.time(),'items':rows})
    def public(self,p):
        undo=p['kind']=='group_undo'
        return {'id':p['id'],'kind':p['kind'],'count':len(p['items']),'destination':p['destination'],
         'items':[{'from':str(Path(p['destination'])/r['name']) if undo else r['source'],
                   'to':r['source'] if undo else str(Path(p['destination'])/r['name'])} for r in p['items']]}
    def plan(self,session,destination_root):
        try:previous=self.read(session)
        except FileNotFoundError:raise ValueError('Primero busca los archivos en esta conversación. Después podré preparar una carpeta con esos resultados.')
        if previous['kind']!='search' or time.time()-previous['created']>600:raise ValueError('La búsqueda venció. Vuelve a buscar los archivos para preparar un plan actualizado.')
        root=Path(destination_root).expanduser();fd=open_dir(root)
        try:root_id=directory_id(fd)
        finally:os.close(fd)
        folder='Nucleo_Archivos_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid4().hex[:6]
        rows=[];used=set()
        for original in previous['items']:
            source=Path(original['source']);fd=open_dir(source.parent)
            try:
                info=os.stat(source.name,dir_fd=fd,follow_symlinks=False)
                if directory_id(fd)!=original['parent_id'] or not regular(info) or fingerprint(info)!=original['fingerprint']:raise ValueError('Un resultado cambió. Repite la búsqueda antes de agrupar.')
            finally:os.close(fd)
            name=source.name;i=2
            while name.casefold() in used:name=f'{source.stem}_{i}{source.suffix}';i+=1
            used.add(name.casefold());rows.append({**original,'name':name,'state':'planned'})
        if not rows:raise ValueError('La última búsqueda no tiene archivos para agrupar. Haz una nueva búsqueda.')
        p={'id':str(uuid4()),'kind':'group','session':session,'created':time.time(),'status':'preview','root':str(root),'root_id':root_id,'folder':folder,'destination':str(root/folder),'items':rows}
        self.save(p);return self.public(p)
    def undo_plan(self,session):
        plans=[json.loads(p.read_text()) for p in self.data.glob('*.json')]
        plans=[p for p in plans if p['kind']=='group' and p['session']==session and p['status'] in ('done','partial','applying')]
        if not plans:raise ValueError('No hay una agrupación de esta conversación para deshacer.')
        previous=max(plans,key=lambda p:p['created'])
        for row in previous['items']:
            if row['state']=='planned':
                src=Path(row['source']);dst=Path(previous['destination'])/row['name']
                try:
                    fd=open_dir(dst.parent)
                    try:info=os.stat(dst.name,dir_fd=fd,follow_symlinks=False)
                    finally:os.close(fd)
                    if not src.exists() and regular(info) and fingerprint(info)==row['fingerprint']:row['state']='moved'
                except OSError:pass
        self.save(previous)
        rows=[dict(r) for r in previous['items'] if r['state']=='moved']
        if not rows:raise ValueError('No hay archivos pendientes para restaurar de esa agrupación.')
        p={**previous,'id':str(uuid4()),'kind':'group_undo','original':previous['id'],'created':time.time(),'status':'preview','items':rows}
        self.save(p);return self.public(p)
    def execute(self,id,session):
        p=self.read(id)
        if p['session']!=session or p['kind'] not in ('group','group_undo') or p['status']!='preview' or time.time()-p['created']>600:raise ValueError('Vista previa inválida o vencida.')
        rootfd=open_dir(p['root']);destfd=None
        undo=p['kind']=='group_undo';moved=0;errors=[]
        try:
            if directory_id(rootfd)!=p['root_id']:raise ValueError('La carpeta de destino cambió.')
            if not undo:os.mkdir(p['folder'],mode=0o700,dir_fd=rootfd)
            destfd=os.open(p['folder'],FLAGS,dir_fd=rootfd)
            p['status']='applying';self.save(p)
            for row in p['items']:
                fd=None
                try:
                    source=Path(row['source']);fd=open_dir(source.parent)
                    if directory_id(fd)!=row['parent_id']:raise ValueError('La carpeta original cambió.')
                    srcfd,dstfd=(destfd,fd) if undo else (fd,destfd)
                    srcname,dstname=(row['name'],source.name) if undo else (source.name,row['name'])
                    info=os.stat(srcname,dir_fd=srcfd,follow_symlinks=False)
                    if not regular(info) or fingerprint(info)!=row['fingerprint']:raise ValueError('El archivo cambió.')
                    # Enlace exclusivo: no sobrescribe destinos; otro volumen produce un fallo seguro.
                    os.link(srcname,dstname,src_dir_fd=srcfd,dst_dir_fd=dstfd,follow_symlinks=False)
                    if fingerprint(os.stat(srcname,dir_fd=srcfd,follow_symlinks=False))!=row['fingerprint']:
                        os.unlink(dstname,dir_fd=dstfd);raise ValueError('El archivo cambió durante el movimiento.')
                    try:os.unlink(srcname,dir_fd=srcfd)
                    except OSError:
                        os.unlink(dstname,dir_fd=dstfd);raise
                    row['state']='restored' if undo else 'moved';moved+=1
                except (OSError,ValueError):errors.append(row['source'])
                finally:
                    if fd is not None:os.close(fd)
                    self.save(p)
            p['status']='partial' if errors else 'done';self.save(p)
            if undo:
                previous=self.read(p['original']);restored={r['source'] for r in p['items'] if r['state']=='restored'}
                for r in previous['items']:
                    if r['source'] in restored:r['state']='restored'
                if not any(r['state']=='moved' for r in previous['items']):previous['status']='undone'
                self.save(previous)
            return {'moved':moved,'failed':errors,'undo':undo,'batch':p['destination'],'group':True}
        finally:
            if destfd is not None:os.close(destfd)
            os.close(rootfd)
