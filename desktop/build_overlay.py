"""Construye la app del SO actual. Usar dentro de un entorno Python preparado."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

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
npm = shutil.which('npm') or shutil.which('npm.cmd')
if not npm:
    raise SystemExit('Instala Node.js LTS y npm antes de construir el overlay.')

os.environ['electron_config_cache'] = str(root / 'work' / 'electron-cache')
os.environ['ELECTRON_BUILDER_CACHE'] = str(root / 'work' / 'electron-builder-cache')

subprocess.run([sys.executable, str(desktop / 'prepare_backend.py')], check=True)

build_target = sys.argv[1] if len(sys.argv) > 1 else 'pack'
if build_target == 'dist':
    pack_args = ['run', 'dist']
else:
    pack_args = ['run', 'pack', '--', '--config.electronDist=node_modules/electron/dist']

steps = []
if not (desktop / 'node_modules').is_dir():
    steps.append(['ci'])
if not (desktop / 'node_modules' / 'electron' / 'dist').is_dir():
    steps.append(['run', 'setup-electron'])
steps.append(pack_args)

for args in steps:
    subprocess.run([npm, *args], cwd=desktop, check=True)

print('App del sistema actual creada en', desktop / 'release')

