"""Build the pinned, static whisper.cpp CLI with only system runtime dependencies.

Run on the target OS/architecture before prepare_backend.py. macOS requires Xcode
Command Line Tools and CMake. This builds the engine, not the separately downloaded
Whisper model. No Python ML wheels or user-installed ffmpeg are needed by the app.
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

REVISION = 'd1be6fde11ac6e0407606b4e42fe72d34add8037'  # whisper.cpp v1.9.5
EXPECTED_SHA256 = '645445da884df6dbd52b30f82d7be7c01d1767c938714e477e786b88d529e9f4'
root = Path(__file__).resolve().parents[1]
work = root / 'work' / 'whisper-build'
work.mkdir(parents=True, exist_ok=True)
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
runtime = root / 'desktop' / 'voice-runtime'
runtime.mkdir(exist_ok=True)
compiled = build / 'bin' / name
if not compiled.exists():
    compiled = build / 'bin' / 'Release' / name
staging = runtime / (name + '.new')
shutil.copy2(compiled, staging)
os.replace(staging, runtime / name)
shutil.copy2(source / 'LICENSE', runtime / 'LICENSE-whisper.cpp.txt')
miniaudio=(source/'examples'/'miniaudio.h').read_text()
(runtime/'LICENSE-miniaudio.txt').write_text(miniaudio[miniaudio.rfind('This software is available as a choice'):])
print('Prepared local voice engine:', runtime / name)
