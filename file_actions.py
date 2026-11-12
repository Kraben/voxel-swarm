"""Búsqueda local limitada por nombre; nunca abre ni lee el contenido."""
import os
from pathlib import Path
import re
import time
from collections import deque
from desktop_actions import normalized

PROMPT='Para buscar ese archivo, dime una pista del nombre o una extensión, por ejemplo «informe» o «.pdf». Solo revisaré nombres en las carpetas autorizadas; no leeré su contenido.'
MAX_ENTRIES_PER_ROOT=3500
SECONDS_PER_ROOT=0.65
MAX_RESULTS_PER_ROOT=5
SKIP={'.git','node_modules','Library','.venv','venv','__pycache__'}

def extension(text):
    clean=normalized(text).strip(' ¿?')
    match=re.search(r'\bextensi(?:on|ones)\s*[:=]?\s*\.?([a-z0-9]{1,10})\b',clean)
    if not match:match=re.search(r'(?:^|\s)\.([a-z0-9]{1,10})(?=$|[\s?,;])',clean)
    return '.'+match.group(1) if match else None

def intent(text, turns=()):
    clean=normalized(text)
    if re.search(r'\b(?:no|nunca)\b.{0,25}\b(?:busc|encuentr|localiz)',clean):return None
    match=re.search(r'\b(?:busca(?:r)?|encuentra|encontrar|localiza(?:r)?)\s+(?:(?:el|un|mi)\s+)?archivo(?:s)?\b(.*)',text,re.I)
    if match:
        ext=extension(text)
        if ext:return ext
        tail=match.group(1).strip(' :¿?')
        tail=re.sub(r'^(?:llamado|con (?:el )?nombre|que se llama)\s+', '',tail,flags=re.I)
        # Una solicitud sin pista debe pedir aclaración, no buscar palabras genéricas.
        if not tail or re.match(r'^(?:en |de |en mi|no |pero |y |lo |para )',normalized(tail)):tail=''
        return tail
    if re.search(r'\b(?:lista(?:r|me|rme)?|muestra(?:me)?)\b',clean) and 'archivo' in clean and extension(text):return extension(text)
    if turns and turns[-1][1]==PROMPT:
        if extension(text):return extension(text)
        return re.sub(r'^(?:se llama|creo que se llama|el nombre es|busca)\s+', '',text.strip(),flags=re.I)
    return None

def roots():
    configured=os.getenv('GHOST_SEARCH_ROOT')
    candidates=[Path(configured).expanduser()] if configured else [Path.home()/p for p in ('Desktop','Downloads','Documents','Music','Pictures','Movies')]
    return [p for p in candidates if p.is_dir() and not p.is_symlink()]

def search(term, *, capture=None):
    term=term.strip(' \t\"\'¿?')
    if not term or len(term)>120 or any(c in term for c in '\n\r\0/\\'):
        return 'Dime solo una parte del nombre o una extensión, hasta 120 caracteres, sin rutas.'
    ext=extension(term)
    needle=normalized(ext or term)
    found=[];denied=0;limited=[];reviewed=[]
    bases=roots()
    for base in bases:
        stack=deque([base]);count=0;hits=0;deadline=time.monotonic()+SECONDS_PER_ROOT
        reviewed.append(str(base))
        while stack:
            if count>=MAX_ENTRIES_PER_ROOT or time.monotonic()>=deadline or hits>=MAX_RESULTS_PER_ROOT:
                limited.append(base.name);break
            directory=stack.popleft()
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        count+=1
                        if count>=MAX_ENTRIES_PER_ROOT or time.monotonic()>=deadline:
                            limited.append(base.name);break
                        if entry.name.startswith('.') or entry.name in SKIP or entry.is_symlink():continue
                        if entry.is_dir(follow_symlinks=False):
                            if not entry.name.endswith(('.app','.photoslibrary')):stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            matches=normalized(Path(entry.name).suffix)==needle if ext else needle in normalized(entry.name)
                            if matches:
                                found.append(entry.path);hits+=1
                                if hits>=MAX_RESULTS_PER_ROOT:limited.append(base.name);break
            except (PermissionError,OSError):denied+=1
            if base.name in limited:break
    if capture is not None:capture.extend(found)
    if not bases:return 'No pude acceder a las carpetas autorizadas. Revisa los permisos de Ghost en Ajustes del Sistema.'
    message=('Encontré estos archivos por nombre:\n\n'+'\n'.join(sorted(found)) if found else 'No encontré coincidencias por nombre en la búsqueda realizada.')
    message+='\n\nCarpetas revisadas (búsqueda rápida): '+', '.join(reviewed)+'. No abrí ni modifiqué archivos; estos resultados no se enviaron al modelo de IA.'
    if limited:message+=' Alcancé el límite de tiempo, recorrido o resultados en: '+', '.join(limited)+'. Puede haber más coincidencias; prueba una pista más específica.'
    if denied:message+=' Algunas carpetas no pudieron leerse por permisos o errores de acceso.'
    return message
