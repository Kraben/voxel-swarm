"""Construye la app del SO actual. Usar dentro de un entorno Python preparado."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
desktop=root/'desktop'
npm=shutil.which('npm')
if not npm: raise SystemExit('Instala Node.js LTS y npm antes de construir el overlay.')
os.environ['electron_config_cache']=str(root/'work'/'electron-cache')
os.environ['ELECTRON_BUILDER_CACHE']=str(root/'work'/'electron-builder-cache')
subprocess.run([sys.executable,str(desktop/'prepare_backend.py')],check=True)
for args in [['ci'],['run','setup-electron'],['run','pack','--','--config.electronDist=node_modules/electron/dist']]:
 subprocess.run([npm,*args],cwd=desktop,check=True)
print('App del sistema actual creada en',desktop/'release')
