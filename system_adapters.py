"""Adaptadores del sistema operativo para Enjambre de Vóxeles.

Aísla las funciones dependientes del sistema operativo:
- Catálogo y lanzamiento seguro de aplicaciones autorizadas.
- Búsqueda de archivos y rutas estándar.
- Síntesis de voz del sistema y diagnóstico de entorno.
"""
from pathlib import Path
import configparser
import json
import os
import platform
import plistlib
import re
import shlex
import shutil
import subprocess
import sys
import unicodedata

SPANISH_NAMES = {
    'calculator': 'Calculadora',
    'calc': 'Calculadora',
    'notes': 'Notas',
    'notepad': 'Bloc de Notas',
    'calendar': 'Calendario',
    'reminders': 'Recordatorios',
    'system settings': 'Configuración del Sistema',
    'system preferences': 'Preferencias del Sistema',
    'settings': 'Configuración',
    'music': 'Música',
    'photos': 'Fotos',
    'preview': 'Vista Previa',
    'contacts': 'Contactos',
    'messages': 'Mensajes',
    'maps': 'Mapas',
    'clock': 'Reloj',
    'voice memos': 'Notas de Voz',
    'app store': 'App Store',
    'terminal': 'Terminal',
    'files': 'Archivos',
    'file manager': 'Archivos',
    'files explorer': 'Explorador de Archivos',
    'explorer': 'Explorador de Archivos',
    'browser': 'Navegador Web',
    'web browser': 'Navegador Web',
    'text editor': 'Editor de Texto',
    'paint': 'Paint',
}

ALIASES = {
    'vscode': 'visual studio code',
    'code': 'visual studio code',
    'studio code': 'visual studio code',
    'arduino': 'arduino ide',
    'cura': 'ultimaker cura',
    'apple tv': 'tv',
    'appletv': 'tv',
    'chrome': 'google chrome',
    'configuracion': 'system settings',
    'ajustes': 'system settings',
    'bloc de notas': 'notepad',
    'bloc notas': 'notepad',
    'editor de texto': 'text editor',
    'explorador': 'explorer',
    'explorador de archivos': 'explorer',
    'simbolo del sistema': 'cmd',
    'consola': 'terminal',
}


def normalize(value):
    text = ''.join(c for c in unicodedata.normalize('NFKD', str(value)).casefold() if not unicodedata.combining(c))
    return ' '.join(text.strip(' \t\r\n.!?¡¿\"\'').split())


class BaseAdapter:
    def installed_apps(self, roots=None):
        raise NotImplementedError

    def launch_app(self, app):
        raise NotImplementedError

    def close_app(self, app):
        raise NotImplementedError

    def default_search_roots(self):
        home = Path.home()
        candidates = [home / p for p in ('Desktop', 'Downloads', 'Documents', 'Music', 'Pictures', 'Movies')]
        return [p for p in candidates if p.is_dir() and not p.is_symlink()]

    def desktop_path(self):
        configured = os.getenv('GHOST_DESKTOP_ROOT')
        if configured:
            return Path(configured).expanduser()
        return Path.home() / 'Desktop'

    def system_speech_command(self):
        return None


class DarwinAdapter(BaseAdapter):
    def default_roots(self):
        return (
            Path('/Applications'),
            Path('/System/Applications'),
            Path.home() / 'Applications',
            Path('/System/Library/CoreServices/Applications'),
        )

    def installed_apps(self, roots=None):
        rows = []
        seen = set()
        roots = self.default_roots() if roots is None else roots
        candidates = []
        for root in roots:
            for pattern in ('*.app', '*/*.app'):
                try:
                    candidates.extend(sorted(Path(root).glob(pattern)))
                except OSError:
                    continue
        if roots == self.default_roots():
            candidates.append(Path('/System/Library/CoreServices/Finder.app'))

        for bundle in candidates:
            try:
                if not bundle.is_dir():
                    continue
                target = bundle.resolve(strict=True)
                if str(target) in seen:
                    continue
                with (target / 'Contents' / 'Info.plist').open('rb') as stream:
                    info = plistlib.load(stream)
                executable = info.get('CFBundleExecutable')
                if (
                    not isinstance(executable, str)
                    or not executable
                    or '/' in executable
                    or '\\' in executable
                    or not (target / 'Contents' / 'MacOS' / executable).is_file()
                ):
                    continue
                stem = bundle.stem
                display = info.get('CFBundleDisplayName') or info.get('CFBundleName') or stem
                if not isinstance(display, str):
                    display = stem
                display = SPANISH_NAMES.get(normalize(stem), display)
                if any(ord(c) < 32 for c in display):
                    display = stem
                aliases = {normalize(stem), normalize(display)}
                if isinstance(info.get('CFBundleName'), str):
                    aliases.add(normalize(info['CFBundleName']))
                aliases.update(k for k, v in ALIASES.items() if normalize(v) in aliases)
                seen.add(str(target))
                rows.append({
                    'id': str(target),
                    'name': display,
                    'command': stem,
                    'aliases': sorted(aliases),
                    'path': str(bundle),
                    'platform': 'darwin',
                })
            except (OSError, ValueError, TypeError, plistlib.InvalidFileException):
                continue
        return sorted(rows, key=lambda row: (normalize(row['name']), row['id']))

    CLOSE_SCRIPT = """on run argv
set appPath to item 1 of argv
if application appPath is not running then return "NOT_RUNNING"
tell application appPath to quit
delay 0.5
if application appPath is running then return "STILL_RUNNING"
return "CLOSED"
end run"""

    def close_app(self, app):
        try:
            result = subprocess.run(
                ['/usr/bin/osascript', '-', '--', app['id']],
                input=self.CLOSE_SCRIPT,
                capture_output=True,
                text=True,
                timeout=15,
                shell=False
            )
        except subprocess.TimeoutExpired:
            return f"{app['name']} no confirmó el cierre. Revisa si tiene un aviso de cambios sin guardar. No forcé el cierre."
        except OSError:
            return 'No pude solicitar el cierre de esa app.'
        if result.returncode:
            if '-1743' in result.stderr:
                return 'macOS no permitió solicitar el cierre. Revisa el permiso de Automatización en Privacidad y seguridad.'
            return 'La app no confirmó el cierre; puede haberlo cancelado o estar esperando que guardes cambios. No forcé el cierre.'
        status = result.stdout.strip()
        if status == 'NOT_RUNNING':
            return f"{app['name']} ya estaba cerrada."
        if status == 'CLOSED':
            return f"He cerrado {app['name']}."
        return f"Solicité cerrar {app['name']}. Sigue abierta; revisa sus avisos para guardar cambios. No forcé el cierre."

    def launch_app(self, app):
        subprocess.run(['/usr/bin/open', '-a', app['id']], check=True, timeout=10, shell=False)

    def system_speech_command(self):
        return ['/usr/bin/say']


class WindowsAdapter(BaseAdapter):
    BUILTIN_APPS = [
        {
            'name': 'Calculadora',
            'command': 'calc',
            'aliases': ['calc', 'calculadora', 'calculator'],
            'path': 'calc.exe',
        },
        {
            'name': 'Bloc de Notas',
            'command': 'notepad',
            'aliases': ['notepad', 'bloc de notas', 'notas', 'notes', 'editor de texto'],
            'path': 'notepad.exe',
        },
        {
            'name': 'Paint',
            'command': 'mspaint',
            'aliases': ['paint', 'mspaint', 'dibujo'],
            'path': 'mspaint.exe',
        },
        {
            'name': 'Explorador de Archivos',
            'command': 'explorer',
            'aliases': ['explorer', 'explorador', 'explorador de archivos', 'archivos', 'file explorer'],
            'path': 'explorer.exe',
        },
        {
            'name': 'Configuración de Windows',
            'command': 'settings',
            'aliases': ['configuracion', 'ajustes', 'settings', 'system settings', 'preferencias'],
            'path': 'ms-settings:',
        },
        {
            'name': 'Terminal de Windows',
            'command': 'terminal',
            'aliases': ['terminal', 'wt', 'consola', 'powershell', 'cmd', 'linea de comandos'],
            'path': 'wt.exe',
        },
        {
            'name': 'Microsoft Edge',
            'command': 'msedge',
            'aliases': ['edge', 'msedge', 'microsoft edge', 'navegador', 'browser'],
            'path': 'msedge.exe',
        },
    ]

    def default_roots(self):
        roots = []
        program_data = os.getenv('ProgramData', r'C:\ProgramData')
        app_data = os.getenv('APPDATA')
        if program_data:
            roots.append(Path(program_data) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')
        if app_data:
            roots.append(Path(app_data) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')
        return [r for r in roots if r.is_dir()]

    def installed_apps(self, roots=None):
        rows = []
        seen = set()

        # Add well-known builtin apps first
        for b in self.BUILTIN_APPS:
            stem = b['command']
            display = b['name']
            aliases = set(b['aliases'])
            aliases.add(normalize(stem))
            aliases.add(normalize(display))
            aliases.update(k for k, v in ALIASES.items() if normalize(v) in aliases)
            seen.add(b['path'].lower())
            rows.append({
                'id': b['path'],
                'name': display,
                'command': stem,
                'aliases': sorted(aliases),
                'path': b['path'],
                'platform': 'win32',
            })

        roots = self.default_roots() if roots is None else roots
        for root in roots:
            try:
                for path in Path(root).rglob('*'):
                    if not path.is_file():
                        continue
                    if path.suffix.lower() not in ('.lnk', '.exe'):
                        continue
                    stem = path.stem
                    target_str = str(path.resolve()) if path.exists() else str(path)
                    target_key = target_str.lower()
                    if target_key in seen:
                        continue

                    # Filter out uninstallers and internal tools
                    low_stem = stem.lower()
                    if any(term in low_stem for term in ('uninstall', 'desinstalar', 'setup', 'helper', 'crash')):
                        continue

                    display = SPANISH_NAMES.get(normalize(stem), stem)
                    aliases = {normalize(stem), normalize(display)}
                    aliases.update(k for k, v in ALIASES.items() if normalize(v) in aliases)
                    seen.add(target_key)
                    rows.append({
                        'id': target_str,
                        'name': display,
                        'command': stem,
                        'aliases': sorted(aliases),
                        'path': target_str,
                        'platform': 'win32',
                    })
            except OSError:
                continue

        # Also check App Paths in Registry if on Windows
        if sys.platform == 'win32':
            try:
                import winreg
                for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        with winreg.OpenKey(hkey, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths') as key:
                            count = winreg.QueryInfoKey(key)[0]
                            for i in range(count):
                                try:
                                    sub_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, sub_name) as sub_key:
                                        target_path = winreg.QueryValue(sub_key, '')
                                        if target_path and os.path.isfile(target_path):
                                            p = Path(target_path)
                                            target_key = str(p.resolve()).lower()
                                            if target_key not in seen:
                                                stem = p.stem
                                                display = SPANISH_NAMES.get(normalize(stem), stem)
                                                aliases = {normalize(stem), normalize(display)}
                                                aliases.update(k for k, v in ALIASES.items() if normalize(v) in aliases)
                                                seen.add(target_key)
                                                rows.append({
                                                    'id': str(p.resolve()),
                                                    'name': display,
                                                    'command': stem,
                                                    'aliases': sorted(aliases),
                                                    'path': str(p.resolve()),
                                                    'platform': 'win32',
                                                })
                                except OSError:
                                    continue
                    except OSError:
                        continue
            except ImportError:
                pass

        return sorted(rows, key=lambda row: (normalize(row['name']), row['id']))

    def launch_app(self, app):
        target = app['id']
        # If it's a URI scheme like ms-settings:
        if target.startswith('ms-settings:'):
            if sys.platform == 'win32':
                os.startfile(target)
            else:
                subprocess.run(['cmd.exe', '/c', 'start', '', target], check=True, timeout=10)
            return

        # If it's an exe or lnk path
        if sys.platform == 'win32':
            try:
                os.startfile(target)
            except AttributeError:
                subprocess.Popen([target], shell=False)
        else:
            # Fallback or testing
            subprocess.run(['cmd.exe', '/c', 'start', '', target], check=True, timeout=10)

    def close_app(self, app):
        proc_name = app.get('command') or Path(app.get('path', app['id'])).stem
        if proc_name.lower().endswith('.exe'):
            proc_name = proc_name[:-4]

        safe_proc = proc_name.replace("'", "''")
        script = f"$p = Get-Process -Name '{safe_proc}' -ErrorAction SilentlyContinue; if (-not $p) {{ Write-Output 'NOT_RUNNING'; exit 0 }}; foreach ($item in $p) {{ try {{ $item.CloseMainWindow() | Out-Null }} catch {{}} }}; Start-Sleep -Milliseconds 800; $r = Get-Process -Name '{safe_proc}' -ErrorAction SilentlyContinue; if (-not $r) {{ Write-Output 'CLOSED' }} else {{ Write-Output 'STILL_RUNNING' }}"
        try:
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script],
                capture_output=True,
                text=True,
                timeout=15,
                shell=False
            )
        except subprocess.TimeoutExpired:
            return f"{app['name']} no confirmó el cierre. Revisa si tiene un aviso de cambios sin guardar. No forcé el cierre."
        except OSError:
            return 'No pude solicitar el cierre de esa app.'

        if result.returncode != 0:
            return 'La app no confirmó el cierre; puede haberlo cancelado o estar esperando que guardes cambios. No forcé el cierre.'

        status = result.stdout.strip()
        if status == 'NOT_RUNNING':
            return f"{app['name']} ya estaba cerrada."
        if status == 'CLOSED':
            return f"He cerrado {app['name']}."
        return f"Solicité cerrar {app['name']}. Sigue abierta; revisa sus avisos para guardar cambios. No forcé el cierre."

    def default_search_roots(self):
        home = Path.home()
        candidates = [home / p for p in ('Desktop', 'Downloads', 'Documents', 'Music', 'Pictures', 'Videos')]
        return [p for p in candidates if p.is_dir() and not p.is_symlink()]

    def system_speech_command(self):
        # PowerShell SAPI synthesizer reads from stdin
        script = "$in=[Console]::In.ReadToEnd();Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak($in)"
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script]


class LinuxAdapter(BaseAdapter):
    DEFAULT_XDG_DIRS = [
        Path('/usr/share/applications'),
        Path('/usr/local/share/applications'),
        Path.home() / '.local' / 'share' / 'applications',
        Path('/var/lib/snapd/desktop/applications'),
        Path('/var/lib/flatpak/exports/share/applications'),
        Path.home() / '.local' / 'share' / 'flatpak' / 'exports' / 'share' / 'applications',
    ]

    def default_roots(self):
        data_dirs = os.getenv('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
        roots = []
        for d in data_dirs:
            if d.strip():
                roots.append(Path(d.strip()) / 'applications')
        data_home = os.getenv('XDG_DATA_HOME')
        if data_home:
            roots.append(Path(data_home) / 'applications')
        else:
            roots.append(Path.home() / '.local' / 'share' / 'applications')
        for extra in (
            Path('/var/lib/snapd/desktop/applications'),
            Path('/var/lib/flatpak/exports/share/applications'),
            Path.home() / '.local' / 'share' / 'flatpak' / 'exports' / 'share' / 'applications',
        ):
            if extra not in roots:
                roots.append(extra)
        return [r for r in roots if r.is_dir()]

    def installed_apps(self, roots=None):
        rows = []
        seen = set()
        roots = self.default_roots() if roots is None else roots

        for root in roots:
            try:
                for entry in sorted(Path(root).glob('*.desktop')):
                    if not entry.is_file():
                        continue
                    try:
                        resolved = entry.resolve(strict=True)
                    except OSError:
                        continue
                    if str(resolved) in seen:
                        continue

                    cp = configparser.RawConfigParser(interpolation=None)
                    try:
                        cp.read(str(resolved), encoding='utf-8')
                    except Exception:
                        continue

                    if not cp.has_section('Desktop Entry'):
                        continue
                    section = cp['Desktop Entry']

                    # Skip NoDisplay or Hidden
                    if section.getboolean('NoDisplay', fallback=False) or section.getboolean('Hidden', fallback=False):
                        continue
                    if section.get('Type', 'Application') != 'Application':
                        continue

                    raw_exec = section.get('Exec', '').strip()
                    if not raw_exec:
                        continue

                    # Sanitize command from Exec line (strip %u, %f, %F, %U, %k, %i, etc.)
                    parts = shlex.split(raw_exec)
                    clean_parts = [p for p in parts if not re.match(r'^%[a-zA-Z]$', p)]
                    if not clean_parts:
                        continue
                    executable_path = clean_parts[0]

                    # Display name: prefer localized Spanish name if present
                    raw_name = section.get('Name', '')
                    display = section.get('Name[es]', raw_name or entry.stem)
                    stem = entry.stem
                    display = SPANISH_NAMES.get(normalize(stem), display)
                    if any(ord(c) < 32 for c in display):
                        display = stem

                    aliases = {normalize(stem), normalize(display)}
                    if raw_name:
                        aliases.add(normalize(raw_name))
                    # Map standard stem names or generic names
                    generic = section.get('GenericName', '')
                    if generic:
                        aliases.add(normalize(generic))
                    aliases.update(k for k, v in ALIASES.items() if normalize(v) in aliases)

                    seen.add(str(resolved))
                    rows.append({
                        'id': str(resolved),
                        'name': display,
                        'command': stem,
                        'aliases': sorted(aliases),
                        'path': str(resolved),
                        'executable': executable_path,
                        'platform': 'linux',
                    })
            except OSError:
                continue

        return sorted(rows, key=lambda row: (normalize(row['name']), row['id']))

    def launch_app(self, app):
        desktop_file = app['id']
        desktop_id = Path(desktop_file).name

        # Prefer standard desktop-file launchers
        if shutil.which('gtk-launch'):
            subprocess.run(['gtk-launch', desktop_id], check=True, timeout=10, shell=False)
            return
        if shutil.which('gio'):
            subprocess.run(['gio', 'launch', desktop_file], check=True, timeout=10, shell=False)
            return

        # Fallback to sanitized executable from the catalog entry
        executable = app.get('executable')
        if executable:
            resolved_bin = shutil.which(executable) or executable
            subprocess.Popen([resolved_bin], shell=False)
            return

        raise RuntimeError('No pude encontrar gtk-launch o gio para abrir la aplicación en Linux.')

    def close_app(self, app):
        executable = app.get('executable') or app.get('command') or Path(app['id']).stem
        proc_name = Path(executable).name

        def _is_running():
            if shutil.which('pgrep'):
                res = subprocess.run(['pgrep', '-x', proc_name], capture_output=True, shell=False)
                return res.returncode == 0
            if shutil.which('pidof'):
                res = subprocess.run(['pidof', proc_name], capture_output=True, shell=False)
                return res.returncode == 0
            return None

        running = _is_running()
        if running is False:
            return f"{app['name']} ya estaba cerrada."

        closed_attempt = False
        if shutil.which('wmctrl'):
            try:
                subprocess.run(['wmctrl', '-c', app['name']], capture_output=True, timeout=5, shell=False)
                closed_attempt = True
            except (subprocess.TimeoutExpired, OSError):
                pass

        if not closed_attempt and shutil.which('pkill'):
            try:
                subprocess.run(['pkill', '-15', '-x', proc_name], capture_output=True, timeout=5, shell=False)
                closed_attempt = True
            except (subprocess.TimeoutExpired, OSError):
                pass

        if not closed_attempt:
            return f"El entorno de escritorio no permite solicitar el cierre normal de {app['name']}."

        still = _is_running()
        if still is False:
            return f"He cerrado {app['name']}."
        return f"Solicité cerrar {app['name']}. Sigue abierta; revisa sus avisos para guardar cambios. No forcé el cierre."

    def system_speech_command(self):
        for cmd in ('spd-say', 'espeak-ng', 'espeak'):
            if shutil.which(cmd):
                return [cmd]
        return None


_ADAPTERS = {
    'darwin': DarwinAdapter(),
    'win32': WindowsAdapter(),
    'linux': LinuxAdapter(),
}


def get_adapter(platform_name=None):
    target = platform_name or sys.platform
    if target.startswith('linux'):
        target = 'linux'
    elif target.startswith('win'):
        target = 'win32'
    return _ADAPTERS.get(target, _ADAPTERS['darwin'])
