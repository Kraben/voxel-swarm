"""Prepare the pinned macOS universal Vosk runtime and Spanish wake model.

No Python Vosk/cffi package is installed: the backend uses ctypes against its C API.
Run before prepare_backend.py. The end-user app already includes these resources.
"""
from pathlib import Path
import hashlib
import shutil
import urllib.request
import zipfile
root=Path(__file__).resolve().parents[1]
work=root/'work'/'wake-build';work.mkdir(parents=True,exist_ok=True)
runtime=root/'desktop'/'voice-runtime';runtime.mkdir(exist_ok=True)
artifacts=[('vosk.whl','https://files.pythonhosted.org/packages/44/19/5e8299237bc2005c3d155d3b48adba6fd6484465ad5c970302fc1d37947d/vosk-0.3.44-py3-none-macosx_10_6_universal2.whl','029d0b3d6a5cff874c575b8a5814a4cccfb37608cff52e846c02a8c67a882801'),('spanish.zip','https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip','09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f')]
for name,url,digest in artifacts:
    target=work/name
    if not target.exists():urllib.request.urlretrieve(url,target)
    with target.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:raise SystemExit('Falló la verificación de '+name)
with zipfile.ZipFile(work/'vosk.whl') as archive:
    with archive.open('vosk/libvosk.dyld') as source,(runtime/'libvosk.dylib.new').open('wb') as target:shutil.copyfileobj(source,target)
(runtime/'libvosk.dylib.new').replace(runtime/'libvosk.dylib')
with zipfile.ZipFile(work/'spanish.zip') as archive:
    prefix='vosk-model-small-es-0.42/'
    for member in archive.infolist():
        if member.is_dir() or not member.filename.startswith(prefix):continue
        relative=Path(member.filename[len(prefix):])
        if relative.is_absolute() or '..' in relative.parts:raise SystemExit('Ruta no válida en el modelo.')
        target=runtime/'wake-model'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with archive.open(member) as source,target.open('wb') as output:shutil.copyfileobj(source,output)
if not (runtime/'LICENSE-vosk.txt').is_file():raise SystemExit('Conserva LICENSE-vosk.txt y NOTICE-wake.txt incluidos en el proyecto.')
print('Motor Vosk y modelo de español preparados.')
