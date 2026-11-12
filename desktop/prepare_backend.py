"""Ejecutar en cada SO destino (macOS, Windows, Linux) con Python y requerimientos instalados."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
from uuid import uuid4

here = Path(__file__).resolve().parent
if (here.parent / 'backend_entry.py').is_file():
    root = here.parent
    desktop = here
elif (here / 'backend_entry.py').is_file():
    root = here
    desktop = here
else:
    root = here.parent
    desktop = here
    if not (root / 'backend_entry.py').is_file():
        raise SystemExit(
            f"ERROR: No se encontró 'backend_entry.py' en '{root}' ni en '{here}'.\n"
            "Asegúrate de haber copiado todo el proyecto (backend_entry.py, servidor.py, static/, commercial/, etc.) y no únicamente la carpeta desktop."
        )

voice_runtime = desktop / 'voice-runtime'
if not voice_runtime.is_dir() and (root / 'voice-runtime').is_dir():
    voice_runtime = root / 'voice-runtime'

# Detect platform-specific binary names
if sys.platform == 'win32':
    voice_cli_name = 'whisper-cli.exe'
    vosk_lib_name = 'libvosk.dll'
    backend_exe_name = 'VoxelBackend.exe'
elif sys.platform == 'darwin':
    voice_cli_name = 'whisper-cli'
    vosk_lib_name = 'libvosk.dylib'
    backend_exe_name = 'VoxelBackend'
else:  # Linux / other
    voice_cli_name = 'whisper-cli'
    vosk_lib_name = 'libvosk.so'
    backend_exe_name = 'VoxelBackend'

voice_cli = voice_runtime / voice_cli_name
vosk_lib = voice_runtime / vosk_lib_name

if not vosk_lib.is_file() or not (voice_runtime / 'wake-model' / 'am' / 'final.mdl').is_file():
    raise SystemExit(f'Falta el detector de Oye Vox ({vosk_lib_name}): ejecuta desktop/prepare_wake.py primero.')
if not voice_cli.is_file():
    raise SystemExit(f'Falta {voice_cli_name}: ejecuta desktop/prepare_voice.py primero.')

os.environ['PYINSTALLER_CONFIG_DIR'] = str(root / 'work' / 'pyinstaller-cache')

pyinstaller_cmd = [
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--name', 'VoxelBackend',
    '--distpath', str(root / 'work' / 'desktop-backend'),
    '--workpath', str(root / 'work' / 'desktop-pyinstaller'),
    '--specpath', str(root / 'work'),
    '--add-binary', str(vosk_lib) + os.pathsep + 'voice',
]

# On Windows, bundle auxiliary DLLs if present (Vosk and Whisper/GGML)
if sys.platform == 'win32':
    for dll_path in sorted(voice_runtime.glob('*.dll')):
        if dll_path.name != 'libvosk.dll':
            pyinstaller_cmd.extend(['--add-binary', str(dll_path) + os.pathsep + 'voice'])

pyinstaller_cmd.extend([
    '--add-data', str(voice_runtime / 'wake-model') + os.pathsep + 'voice/wake-model',
    '--add-data', str(voice_runtime / 'LICENSE-vosk.txt') + os.pathsep + 'voice',
    '--add-data', str(voice_runtime / 'NOTICE-wake.txt') + os.pathsep + 'voice',
    '--add-binary', str(voice_cli) + os.pathsep + 'voice',
    '--add-data', str(voice_runtime / 'LICENSE-whisper.cpp.txt') + os.pathsep + 'voice',
    '--add-data', str(voice_runtime / 'LICENSE-whisper-model.txt') + os.pathsep + 'voice',
    '--add-data', str(voice_runtime / 'LICENSE-miniaudio.txt') + os.pathsep + 'voice',
    '--add-data', str(voice_runtime / 'BUILD.txt') + os.pathsep + 'voice',
    '--add-data', str(root / 'commercial' / 'license-public-key.json') + os.pathsep + 'commercial',
    '--add-data', str(root / 'index.html') + os.pathsep + '.',
    '--add-data', str(root / 'static') + os.pathsep + 'static',
    '--paths', str(root),
    '--hidden-import', 'cerebro_ghost',
    '--hidden-import', 'skills_mac',
    '--hidden-import', 'system_adapters',
    '--hidden-import', 'licensing',
    '--collect-all', 'ddgs',
    '--collect-all', 'uvicorn',
    '--collect-all', 'cryptography',
    str(root / 'backend_entry.py')
])

subprocess.run(pyinstaller_cmd, cwd=root, check=True)

# Reemplaza el directorio completo evitando colisiones de inodos o bloqueos de firma
staging = desktop / ('backend-staging-' + uuid4().hex)
shutil.copytree(root / 'work' / 'desktop-backend' / 'VoxelBackend', staging)
target = desktop / 'backend'
retired = desktop / ('backend-retired-' + uuid4().hex)
if target.exists():
    target.rename(retired)
staging.rename(target)
if retired.exists():
    shutil.rmtree(retired)

print('Motor de escritorio preparado para', sys.platform)
