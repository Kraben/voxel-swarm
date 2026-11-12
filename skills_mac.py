"""Skills locales: abrir y cerrar apps, y buscar archivos en macOS, Windows y Linux."""
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import app_catalog
import file_actions
import system_adapters


def obtener_apps_instaladas():
    return {row['command'].lower(): row['id'] for row in app_catalog.installed_apps()}


def es_apertura_app(texto):
    return texto.lower().strip().startswith(('abre ', 'abrir '))


def es_cierre_app(texto):
    return texto.lower().strip().startswith(('cierra ', 'cerrar '))


def es_accion_app(texto):
    return es_apertura_app(texto) or es_cierre_app(texto)


CLOSE_SCRIPT = """on run argv
set appPath to item 1 of argv
if application appPath is not running then return "NOT_RUNNING"
tell application appPath to quit
delay 0.3
if application appPath is running then return "STILL_RUNNING"
return "CLOSED"
end run"""


def cierre_pedido(texto, nombre):
    text = app_catalog.normalize(texto)
    if re.search(r'\b(?:no|nunca|sin)\b.{0,35}\b(?:cierr\w*|cerr\w*|close|quit)\b', text):
        return False
    if re.search(r'\b(?:que|cuales|cual)\b.{0,50}\b(?:apps?|aplicaciones|programas)\b', text):
        return False
    if not re.search(r'\b(?:cierra|cerrar|cerrarme|cierras|cerrarias|close|quit)\b', text):
        return False
    app, error = app_catalog.resolve_app(nombre)
    return not error and any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text) for alias in app['aliases'])


def apertura_pedida(texto, nombre):
    """For model-selected tools, require the current user to name a launch request."""
    text = app_catalog.normalize(texto)
    if re.search(r'\b(?:no|nunca|sin)\b.{0,35}\b(?:abr\w*|inici\w*|lanz\w*|open|launch)\b', text):
        return False
    if re.search(r'\b(?:que|cuales|cual)\b.{0,50}\b(?:apps?|aplicaciones|programas)\b', text):
        return False
    if not re.search(r'\b(?:abre|abrir|abrirme|abririas|abres|abr[ae]s?|inicia|iniciar|iniciarme|lanza|lanzar|open|launch)\b', text):
        return False
    app, error = app_catalog.resolve_app(nombre)
    if error:
        return False
    return any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text) for alias in app['aliases'])


def normalizar_comando_voz(texto):
    """Repair a joined speech token only when it names an already permitted app."""
    value = texto.strip()
    if value.lower().startswith('abre') and len(value) > 4 and value[4].isalnum():
        app, error = app_catalog.resolve_app(value[4:])
        if app:
            return 'abre ' + app['name']
    return value


def es_skill(texto):
    t = texto.lower().strip()
    return t.startswith(('abre ', 'abrir ', 'cierra ', 'cerrar ', 'busca el archivo ', 'encuentra el archivo '))


def ejecutar_skill(texto: str, *, autorizado=False):
    if not es_skill(texto):
        return None
    if (not autorizado and not es_accion_app(texto)) or os.getenv('GHOST_ENABLE_SKILLS', '0') != '1' or os.getenv('GHOST_PUBLIC', '0') == '1':
        return 'Las skills de macOS están bloqueadas. Activa las acciones locales en Skills y permisos. Las apps deben estar en tu lista permitida.'
    if platform.system() not in ('Darwin', 'Windows', 'Linux'):
        return 'Las skills requieren macOS, Windows o Linux.'
    t = texto.lower().strip()
    if es_accion_app(texto):
        objetivo = t.split(' ', 1)[1]
        for prefijo in ('la app ', 'el programa ', 'la aplicación ', 'la ', 'el '):
            objetivo = objetivo.removeprefix(prefijo)
        app, error = app_catalog.resolve_app(objetivo)
        if error:
            return error
        if es_cierre_app(texto):
            if platform.system() == 'Darwin':
                try:
                    result = subprocess.run(['/usr/bin/osascript', '-', '--', app['id']], input=CLOSE_SCRIPT, capture_output=True, text=True, timeout=15, shell=False)
                except subprocess.TimeoutExpired:
                    return f"{app['name']} no confirmó el cierre. Revisa si tiene un aviso de cambios sin guardar. No forcé el cierre."
                except OSError:
                    return 'No pude solicitar el cierre de esa app.'
                if result.returncode:
                    if '-1743' in result.stderr:
                        return 'macOS no permitió solicitar el cierre. Revisa el permiso de Automatización en Privacidad y seguridad.'
                    return 'La app no confirmó el cierre; puede haberlo cancelado o estar esperando que guardes cambios. No forcé el cierre.'
                if result.stdout.strip() == 'NOT_RUNNING':
                    return f"{app['name']} ya estaba cerrada."
                if result.stdout.strip() == 'CLOSED':
                    return f"He cerrado {app['name']}."
                return f"Solicité cerrar {app['name']}. Sigue abierta; revisa sus avisos para guardar cambios. No forcé el cierre."
            else:
                return system_adapters.get_adapter().close_app(app)

        # Apertura de aplicación
        if platform.system() == 'Darwin':
            subprocess.run(['/usr/bin/open', '-a', app['id']], check=True, timeout=10, shell=False)
        else:
            system_adapters.get_adapter().launch_app(app)
        return f"He abierto {app['name']}."

    termino = texto.strip().split('archivo ', 1)[-1].strip()
    if not termino or len(termino) > 120 or termino.startswith('-') or any(c in termino for c in '\n\r\0'):
        return 'Indica un nombre de archivo válido (hasta 120 caracteres).'
    if platform.system() == 'Darwin' and shutil.which('mdfind'):
        raiz = Path(os.getenv('GHOST_SEARCH_ROOT', '~/Documents')).expanduser().resolve()
        resultado = subprocess.run(['/usr/bin/mdfind', '-onlyin', str(raiz), '-name', termino], capture_output=True, text=True, check=True, timeout=10)
        rutas = []
        for linea in resultado.stdout.splitlines():
            ruta = Path(linea).resolve()
            if ruta.is_relative_to(raiz):
                rutas.append(str(ruta.relative_to(raiz)))
        return 'Archivos en la carpeta autorizada:\n' + '\n'.join(rutas[:3]) if rutas else 'No encontré archivos con ese nombre.'
    else:
        return file_actions.search(termino)
