"""Build or install the pinned whisper.cpp CLI.

Run on the target OS/architecture before prepare_backend.py.
On Windows/Linux without CMake/C++ tools, can download prebuilt binaries directly.
"""
from pathlib import Path
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

REVISION = 'd1be6fde11ac6e0407606b4e42fe72d34add8037'  # whisper.cpp v1.9.5
EXPECTED_SHA256 = '645445da884df6dbd52b30f82d7be7c01d1767c938714e477e786b88d529e9f4'

WIN_PREBUILT_URL = 'https://github.com/ggml-org/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip'
WIN_PREBUILT_SHA256 = '6ba69e3482d7826214f90a6a9c84ca07782aec1e1d0c6a7c30c994fd5d816ccb'

here = Path(__file__).resolve().parent
root = here.parent if (here.parent / 'backend_entry.py').is_file() else here
desktop = here
work = root / 'work' / 'whisper-build'
work.mkdir(parents=True, exist_ok=True)
runtime = desktop / 'voice-runtime'
runtime.mkdir(exist_ok=True)


def download_win_prebuilt():
    target = work / 'whisper-win.zip'
    if not target.exists():
        print('Descargando binario oficial precompilado de whisper.cpp para Windows...')
        req = urllib.request.Request(WIN_PREBUILT_URL, headers={'User-Agent': 'VoxelSwarmBuild/0.7.3'})
        with urllib.request.urlopen(req) as resp, target.open('wb') as out:
            shutil.copyfileobj(resp, out)
    with target.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != WIN_PREBUILT_SHA256:
        target.unlink(missing_ok=True)
        raise SystemExit(f'Falló la verificación SHA256 de whisper-win.zip: {digest}')

    with zipfile.ZipFile(target) as z:
        for member in z.namelist():
            fn = Path(member).name
            if fn == 'whisper-cli.exe' or (fn.endswith('.dll') and ('whisper' in fn or 'ggml' in fn)):
                dest = runtime / fn
                with z.open(member) as src, dest.open('wb') as dst:
                    shutil.copyfileobj(src, dst)
                print(f'Instalado binario de voz: {fn}')
    print('Motor de voz local para Windows instalado en desktop/voice-runtime')


def build_from_source():
    archive = work / 'source.tar.gz'
    url = 'https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/' + REVISION
    if not archive.exists():
        urllib.request.urlretrieve(url, archive)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit('El archivo fuente no coincide con la revisión verificada. Borra source.tar.gz y vuelve a intentarlo.')
    print('Source SHA256:', digest)
    with tarfile.open(archive) as tar:
        tar.extractall(work, filter='data')
    source = work / ('whisper.cpp-' + REVISION)
    build = work / 'build'
    args = ['cmake', '-S', str(source), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=OFF', '-DGGML_METAL=OFF', '-DGGML_OPENMP=OFF', '-DWHISPER_BUILD_TESTS=OFF', '-DWHISPER_BUILD_SERVER=OFF', '-DGGML_NATIVE=OFF']
    if sys.platform == 'darwin':
        args += ['-DCMAKE_OSX_DEPLOYMENT_TARGET=12.0', '-DCMAKE_OSX_ARCHITECTURES=' + platform.machine()]
    subprocess.run(args, check=True)
    subprocess.run(['cmake', '--build', str(build), '--config', 'Release', '--target', 'whisper-cli', '-j', '4'], check=True)
    name = 'whisper-cli.exe' if os.name == 'nt' else 'whisper-cli'
    compiled = build / 'bin' / name
    if not compiled.exists():
        compiled = build / 'bin' / 'Release' / name
    staging = runtime / (name + '.new')
    shutil.copy2(compiled, staging)
    os.replace(staging, runtime / name)
    shutil.copy2(source / 'LICENSE', runtime / 'LICENSE-whisper.cpp.txt')
    miniaudio = (source / 'examples' / 'miniaudio.h').read_text()
    (runtime / 'LICENSE-miniaudio.txt').write_text(miniaudio[miniaudio.rfind('This software is available as a choice'):])
    print('Prepared local voice engine:', runtime / name)


def main():
    if sys.platform == 'win32' and not shutil.which('cmake'):
        download_win_prebuilt()
    else:
        try:
            build_from_source()
        except (subprocess.CalledProcessError, FileNotFoundError):
            if sys.platform == 'win32':
                print('CMake no disponible o falló la compilación; descargando precompilado...')
                download_win_prebuilt()
            else:
                raise


if __name__ == '__main__':
    main()

