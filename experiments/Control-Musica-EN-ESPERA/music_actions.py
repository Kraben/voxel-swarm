"""Fixed Apple Music automation. User text is passed as argv, never script code."""
import os,platform,re,subprocess
import app_catalog

SCRIPT = r'''on run argv
set operation to item 1 of argv
set query to item 2 of argv
tell application id "com.apple.Music"
if operation is "play" then
set matches to search library playlist 1 for query
if (count of matches) is 0 then return "NOT_FOUND"
play item 1 of matches
else if operation is "pause" then
pause
return "PAUSED"
else if operation is "resume" then
play
else if operation is "next" then
next track
else if operation is "previous" then
previous track
end if
if player state is playing then return "PLAYING: " & name of current track & " — " & artist of current track
return "NOT_PLAYING"
end tell
end run'''

def intent(text):
    t=text.strip().rstrip(' .!?¿¡')
    t=re.sub(r'^(?:oye vox[, ]+|por favor[, ]+)', '',t,flags=re.I)
    if re.search(r'\b(?:no|nunca)\b',t,re.I):return None
    for pattern,action in [(r'(?:pausa|pausar)(?: la (?:música|musica|canción|cancion))?','pause'),(r'(?:reanuda|reanudar|continúa|continua)(?: la (?:música|musica|canción|cancion))?','resume'),(r'(?:siguiente(?: canción| cancion| pista)?|cambia de canción|cambia de cancion|pasa (?:a )?la siguiente(?: canción| cancion)?)','next'),(r'(?:anterior(?: canción| cancion| pista)?|canción anterior|cancion anterior)','previous')]:
        if re.fullmatch(pattern,t,re.I):return {'action':action,'query':''}
    match=re.fullmatch(r'(?:reproduce|pon|ponme)\s+(.{1,120})',t,re.I)
    if match:return {'action':'play','query':match[1]}
    return None

def execute(command):
    action=command.get('action');query=command.get('query','')
    if action not in ('play','pause','resume','next','previous') or not isinstance(query,str) or len(query)>120 or any(c in query for c in '\n\r\0') or (action=='play' and not query.strip()):
        return 'Comando de Música no válido.'
    if os.getenv('GHOST_PUBLIC','0')=='1' or os.getenv('GHOST_ENABLE_SKILLS','0')!='1' or os.getenv('GHOST_ENABLE_MUSIC','0')!='1':
        return 'Activa Apple Music en Ajustes → Funciones especiales y las acciones del Mac para usar esta skill.'
    if platform.system()!='Darwin':return 'Esta integración de Música requiere macOS.'
    app,error=app_catalog.resolve_app('Music')
    if error:return 'Marca Música en las aplicaciones permitidas de Ajustes.'
    if app['id']!='/System/Applications/Music.app':return 'No pude verificar la aplicación Música de macOS.'
    try:
        result=subprocess.run(['/usr/bin/osascript','-','--',action,query],input=SCRIPT,text=True,capture_output=True,timeout=20,check=False,shell=False)
    except subprocess.TimeoutExpired:return 'Música no respondió a tiempo. Revisa si macOS está esperando el permiso de Automatización.'
    except OSError:return 'No pude iniciar el control de Música.'
    if result.returncode:
        if '-1743' in result.stderr:return 'macOS bloqueó el control de Música. Permite Automatización para Vóxeles en Ajustes del Sistema → Privacidad y seguridad.'
        return 'Música no pudo completar la acción. Revisa que haya una pista disponible y el permiso de Automatización.'
    value=result.stdout.strip()
    if value=='NOT_FOUND':return 'No encontré esa canción o artista en tu biblioteca de Música. Añádelo a tu biblioteca y vuelve a intentarlo. Esta versión no busca en todo el catálogo de Apple Music.'
    if value=='PAUSED':return 'Música en pausa.'
    if value.startswith('PLAYING: '):return 'Reproduciendo: '+value[9:]
    return 'Música no está reproduciendo ninguna pista. No puedo confirmar la reproducción.'
