"""Local macOS application discovery. Only app bundles in standard locations."""
from pathlib import Path
import json
import os
import plistlib
import unicodedata
from xml.parsers.expat import ExpatError

SPANISH_NAMES = {'calculator':'Calculadora','notes':'Notas','calendar':'Calendario','reminders':'Recordatorios','system settings':'Configuración del Sistema','system preferences':'Preferencias del Sistema','music':'Música','photos':'Fotos','preview':'Vista Previa','contacts':'Contactos','messages':'Mensajes','maps':'Mapas','clock':'Reloj','voice memos':'Notas de Voz','app store':'App Store'}
ALIASES = {'vscode':'visual studio code','code':'visual studio code','studio code':'visual studio code','arduino':'arduino ide','cura':'ultimaker cura','apple tv':'tv','appletv':'tv','chrome':'google chrome','configuracion':'system settings','ajustes':'system settings'}

def normalize(value):
    text = ''.join(c for c in unicodedata.normalize('NFKD',str(value)).casefold() if not unicodedata.combining(c))
    return ' '.join(text.strip(' \t\r\n.!?¡¿\"\'').split())

def default_roots():
    return (Path('/Applications'),Path('/System/Applications'),Path.home()/'Applications',Path('/System/Library/CoreServices/Applications'))

def installed_apps(roots=None):
    rows = []
    seen = set()
    roots = default_roots() if roots is None else roots
    candidates = []
    for root in roots:
        for pattern in ('*.app','*/*.app'):
            try:candidates.extend(sorted(Path(root).glob(pattern)))
            except OSError:continue
    if roots == default_roots():
        candidates.append(Path('/System/Library/CoreServices/Finder.app'))
    for bundle in candidates:
        try:
            if not bundle.is_dir():continue
            target = bundle.resolve(strict=True)
            if str(target) in seen:continue
            with (target/'Contents'/'Info.plist').open('rb') as stream:
                info = plistlib.load(stream)
            executable = info.get('CFBundleExecutable')
            if not isinstance(executable,str) or not executable or '/' in executable or '\\' in executable or not (target/'Contents'/'MacOS'/executable).is_file():continue
            stem = bundle.stem
            display = info.get('CFBundleDisplayName') or info.get('CFBundleName') or stem
            if not isinstance(display,str):display=stem
            display = SPANISH_NAMES.get(normalize(stem),display)
            if any(ord(c)<32 for c in display):display=stem
            aliases = {normalize(stem),normalize(display)}
            if isinstance(info.get('CFBundleName'),str):aliases.add(normalize(info['CFBundleName']))
            aliases.update(k for k,v in ALIASES.items() if normalize(v) in aliases)
            seen.add(str(target))
            rows.append({'id':str(target),'name':display,'command':stem,'aliases':sorted(aliases),'path':str(bundle)})
        except (OSError,ValueError,TypeError,plistlib.InvalidFileException,ExpatError):continue
    return sorted(rows,key=lambda row:(normalize(row['name']),row['id']))

def allowed_ids():
    raw = os.getenv('GHOST_ALLOWED_APPS_JSON')
    if raw is None:
        return [item.strip() for item in os.getenv('GHOST_ALLOWED_APPS','calculator,notes').split(',') if item.strip()]
    try:
        data=json.loads(raw)
        if not isinstance(data,list) or len(data)>256 or any(not isinstance(item,str) or len(item)>1024 or any(ord(c)<32 for c in item) for item in data):return []
        return data
    except (ValueError,TypeError):return []

def permitted(app,selection=None):
    selection=allowed_ids() if selection is None else selection
    return any(item==app['id'] if item.startswith('/') else normalize(item) in app['aliases'] for item in selection)

def resolve_app(name,apps=None):
    apps=installed_apps() if apps is None else apps
    wanted=normalize(name)
    for suffix in (' por favor',' porfa'):
        if wanted.endswith(suffix):wanted=wanted[:-len(suffix)].strip(' ,')
    wanted=ALIASES.get(wanted,wanted)
    matches=[row for row in apps if wanted in row['aliases']]
    if not matches:return None,'No encontré esa aplicación instalada. Usa el nombre que aparece en Ajustes.'
    selected=[row for row in matches if permitted(row)]
    if not selected:return None,'Aplicación fuera de tu lista permitida. Márcala en Ajustes → Aplicaciones permitidas.'
    if len(selected)>1:return None,'Hay varias aplicaciones con ese nombre. Deja seleccionada solo la que quieres abrir en Ajustes.'
    return selected[0],None
