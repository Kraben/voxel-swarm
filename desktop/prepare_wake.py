"""Prepare the pinned Vosk runtime and Spanish wake model for macOS, Windows and Linux.

No Python Vosk/cffi package is installed: the backend uses ctypes against its C API.
Run before prepare_backend.py. The end-user app already includes these resources.
Supports target OS selection (--platform=darwin|win32|linux) or all platforms (--all).
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

here = Path(__file__).resolve().parent
root = here.parent if (here.parent / 'backend_entry.py').is_file() else here
desktop = here
runtime = desktop / 'voice-runtime'
work = root / 'work' / 'wake-build'
work.mkdir(parents=True, exist_ok=True)
runtime.mkdir(exist_ok=True)

MODEL_URL = 'https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip'
MODEL_SHA256 = '09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f'

PLATFORM_WHEELS = {
    'darwin': {
        'file': 'vosk-mac.whl',
        'url': 'https://files.pythonhosted.org/packages/44/19/5e8299237bc2005c3d155d3b48adba6fd6484465ad5c970302fc1d37947d/vosk-0.3.44-py3-none-macosx_10_6_universal2.whl',
        'sha256': '029d0b3d6a5cff874c575b8a5814a4cccfb37608cff52e846c02a8c67a882801',
        'binaries': [('vosk/libvosk.dyld', 'libvosk.dylib')],
    },
    'win32': {
        'file': 'vosk-win.whl',
        'url': 'https://files.pythonhosted.org/packages/73/11/4c967c41f482bb081d1b8c1e578ed5f28ae17939422de313ceb42d2523a4/vosk-0.3.44-py3-none-win_amd64.whl',
        'sha256': '45b1b1136a5cba6066c51da9f852dca7a855744db4ab72b23750c681d36f3202',
        'binaries': [
            ('vosk/libvosk.dll', 'libvosk.dll'),
            ('vosk/libgcc_s_seh-1.dll', 'libgcc_s_seh-1.dll'),
            ('vosk/libstdc++-6.dll', 'libstdc++-6.dll'),
            ('vosk/libwinpthread-1.dll', 'libwinpthread-1.dll'),
        ],
    },
    'linux': {
        'file': 'vosk-linux.whl',
        'url': 'https://files.pythonhosted.org/packages/26/c7/ed8a6ee755e18708770335a6d38b1e86f4838cdeaa85e92748a4e7431816/vosk-0.3.44-py3-none-manylinux_2_12_x86_64.manylinux2010_x86_64.whl',
        'sha256': '2652ef213c4c7807dc40af1e7aa578dcccfc4dc4192822a26bc45a9591bcbf76',
        'binaries': [('vosk/libvosk.so', 'libvosk.so')],
    },
}


def download_and_verify(url, filename, expected_digest):
    target = work / filename
    if not target.exists():
        req = urllib.request.Request(url, headers={'User-Agent': 'VoxelSwarmBuild/0.7.1'})
        with urllib.request.urlopen(req) as resp, target.open('wb') as out:
            shutil.copyfileobj(resp, out)
    with target.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected_digest:
            target.unlink(missing_ok=True)
            raise SystemExit(f'Falló la verificación SHA256 de {filename}: esperado {expected_digest}, obtenido {actual}')
    return target


def extract_binaries(wheel_path, mappings):
    with zipfile.ZipFile(wheel_path) as archive:
        for archive_name, target_name in mappings:
            dest = runtime / target_name
            temp_dest = runtime / (target_name + '.new')
            with archive.open(archive_name) as source, temp_dest.open('wb') as target:
                shutil.copyfileobj(source, target)
            temp_dest.replace(dest)
            print(f'Instalado binario Vosk: {target_name}')


def extract_model(model_zip):
    prefix = 'vosk-model-small-es-0.42/'
    with zipfile.ZipFile(model_zip) as archive:
        for member in archive.infolist():
            if member.is_dir() or not member.filename.startswith(prefix):
                continue
            relative = Path(member.filename[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts:
                raise SystemExit('Ruta no válida en el modelo.')
            target = runtime / 'wake-model' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
    print('Modelo de español extraído en desktop/voice-runtime/wake-model')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['darwin', 'win32', 'linux'], default=None)
    parser.add_argument('--all', action='store_true', default=False)
    args = parser.parse_args()

    targets = list(PLATFORM_WHEELS.keys()) if args.all else [args.platform or (sys.platform if sys.platform in PLATFORM_WHEELS else 'linux')]

    for plat in targets:
        spec = PLATFORM_WHEELS[plat]
        print(f'Descargando Vosk para {plat}...')
        wheel_path = download_and_verify(spec['url'], spec['file'], spec['sha256'])
        extract_binaries(wheel_path, spec['binaries'])

    # Spanish model
    print('Descargando modelo de español...')
    model_path = download_and_verify(MODEL_URL, 'spanish.zip', MODEL_SHA256)
    extract_model(model_path)

    if not (runtime / 'LICENSE-vosk.txt').is_file():
        raise SystemExit('Conserva LICENSE-vosk.txt y NOTICE-wake.txt incluidos en el proyecto.')

    print(f'Motor Vosk y modelo de español preparados para: {", ".join(targets)}')


if __name__ == '__main__':
    main()
