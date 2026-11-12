"""Ejecutar en cada SO destino con Python y requirements-mac.txt instalados."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
from uuid import uuid4
root = Path(__file__).resolve().parents[1]
desktop = root / 'desktop'
voice_runtime=desktop/'voice-runtime'
voice_cli=voice_runtime/('whisper-cli.exe' if sys.platform=='win32' else 'whisper-cli')
if not (voice_runtime/'libvosk.dylib').is_file() or not (voice_runtime/'wake-model'/'am'/'final.mdl').is_file():raise SystemExit('Falta el detector de Oye Vox: ejecuta desktop/prepare_wake.py primero.')
if not voice_cli.is_file():raise SystemExit('Falta whisper-cli: ejecuta desktop/prepare_voice.py primero.')
os.environ['PYINSTALLER_CONFIG_DIR'] = str(root / 'work' / 'pyinstaller-cache')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','VoxelBackend',
 '--distpath',str(root/'work'/'desktop-backend'),'--workpath',str(root/'work'/'desktop-pyinstaller'),'--specpath',str(root/'work'),
 '--add-binary',str(voice_runtime/'libvosk.dylib')+os.pathsep+'voice','--add-data',str(voice_runtime/'wake-model')+os.pathsep+'voice/wake-model','--add-data',str(voice_runtime/'LICENSE-vosk.txt')+os.pathsep+'voice','--add-data',str(voice_runtime/'NOTICE-wake.txt')+os.pathsep+'voice',
 '--add-binary',str(voice_cli)+os.pathsep+'voice','--add-data',str(voice_runtime/'LICENSE-whisper.cpp.txt')+os.pathsep+'voice','--add-data',str(voice_runtime/'LICENSE-whisper-model.txt')+os.pathsep+'voice',
 '--add-data',str(voice_runtime/'LICENSE-miniaudio.txt')+os.pathsep+'voice','--add-data',str(voice_runtime/'BUILD.txt')+os.pathsep+'voice',
 '--add-data',str(root/'commercial'/'license-public-key.json')+os.pathsep+'commercial',
 '--add-data',str(root/'index.html')+os.pathsep+'.','--add-data',str(root/'static')+os.pathsep+'static',
 '--paths',str(root),'--hidden-import','cerebro_ghost','--hidden-import','skills_mac','--collect-all','ddgs','--collect-all','uvicorn',str(root/'backend_entry.py')],cwd=root,check=True)
# Sustituye el directorio completo: no sobrescribas ejecutables firmados en
# el mismo inode, porque macOS puede conservar la firma anterior en caché.
staging=desktop/('backend-staging-'+uuid4().hex)
shutil.copytree(root/'work'/'desktop-backend'/'VoxelBackend',staging)
target=desktop/'backend'
retired=desktop/('backend-retired-'+uuid4().hex)
if target.exists():target.rename(retired)
staging.rename(target)
if retired.exists():shutil.rmtree(retired)

print('Motor de escritorio preparado para',sys.platform)
