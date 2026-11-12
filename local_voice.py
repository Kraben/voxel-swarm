"""Offline whisper.cpp transcription and explicit, verified model installation."""
from pathlib import Path
import hashlib
import io
import os
import subprocess
import sys
import threading
from uuid import uuid4
import wave
import httpx

MODEL_NAME = 'Whisper base multilingüe'
MODEL_SIZE = 147951465
MODEL_SHA256 = '60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe'
MODEL_URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/80da2d8bfee42b0e836fc3a9890373e5defc00a6/ggml-base.bin'
_guard = threading.RLock()
_transcription = threading.Lock()
_state = {'state': 'idle', 'received': 0, 'total': MODEL_SIZE, 'error': ''}
_cancel = threading.Event()
_verified = None

def binary_path():
    override = os.getenv('GHOST_WHISPER_CLI')
    if override:
        return Path(override)
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return root / 'voice' / ('whisper-cli.exe' if os.name == 'nt' else 'whisper-cli') if getattr(sys, 'frozen', False) else root / 'desktop' / 'voice-runtime' / ('whisper-cli.exe' if os.name == 'nt' else 'whisper-cli')

def model_path():
    root = Path(os.getenv('GHOST_VOICE_MODEL_DIR', str(Path(os.getenv('GHOST_DATA_DIR', str(Path(__file__).parent / 'data'))) / 'voice')))
    return root / 'ggml-base.bin'

def model_ready():
    global _verified
    target = model_path()
    try:
        stat = target.stat()
        signature = (str(target), stat.st_size, stat.st_mtime_ns, stat.st_ino)
        if stat.st_size != MODEL_SIZE:
            return False
        with _guard:
            if _verified != signature:
                with target.open('rb') as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != MODEL_SHA256:
                        return False
                _verified = signature
        return True
    except OSError:
        return False

def status():
    runtime = binary_path().is_file() and os.access(binary_path(), os.X_OK)
    ready = model_ready()
    with _guard:
        return {'mode': 'local', 'provider': 'Whisper local', 'supported': runtime, 'ready': runtime and ready, 'format': 'wav', 'model': MODEL_NAME, 'model_bytes': MODEL_SIZE, 'download': dict(_state)}

def _download():
    target = model_path()
    partial = target.with_name('.download-' + uuid4().hex + '.part')
    try:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        digest = hashlib.sha256()
        received = 0
        # Fixed public URL; no user URLs, API keys, or microphone audio are sent.
        with httpx.stream('GET', MODEL_URL, timeout=httpx.Timeout(30, connect=15), follow_redirects=True) as response:
            response.raise_for_status()
            with partial.open('xb') as output:
                os.chmod(partial, 0o600)
                for chunk in response.iter_bytes(256 * 1024):
                    if _cancel.is_set():
                        raise InterruptedError()
                    received += len(chunk)
                    if received > MODEL_SIZE:
                        raise ValueError('El modelo descargado tiene un tamaño inesperado.')
                    digest.update(chunk)
                    output.write(chunk)
                    with _guard:
                        _state['received'] = received
        if _cancel.is_set():
            raise InterruptedError()
        if received != MODEL_SIZE or digest.hexdigest() != MODEL_SHA256:
            raise ValueError('Falló la verificación del modelo. Vuelve a descargarlo.')
        with _guard:
            if _cancel.is_set():
                raise InterruptedError()
            os.replace(partial, target)
            _state.update(state='ready', error='')
    except InterruptedError:
        with _guard:
            _state.update(state='cancelled', error='Descarga cancelada. Puedes volver a iniciarla.')
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else 'No pude descargar el modelo. Revisa la conexión y el espacio disponible e inténtalo de nuevo.'
        with _guard:
            _state.update(state='error', error=message)
    finally:
        partial.unlink(missing_ok=True)

def start_download():
    with _guard:
        if not status()['supported']:
            raise ValueError('Falta el motor de voz local en esta instalación. Usa el paquete de escritorio completo.')
        if model_ready() or _state['state'] == 'downloading':
            return status()
        _cancel.clear()
        _state.update(state='downloading', received=0, error='')
        threading.Thread(target=_download, name='local-voice-model', daemon=True).start()
        return status()

def cancel_download():
    with _guard:
        if _state['state'] == 'downloading':
            _cancel.set()
    return status()

def transcribe(audio, mime):
    if mime != 'audio/wav':
        raise ValueError('La voz local requiere audio WAV. Reinicia el chat para actualizar la captura.')
    if not status()['ready']:
        raise ValueError('Descarga el modelo de voz local desde el chat antes de conversar.')
    try:
        with wave.open(io.BytesIO(audio), 'rb') as source:
            if source.getnchannels() != 1 or source.getframerate() != 16000 or source.getsampwidth() != 2 or not 0 < source.getnframes() <= 968000:
                raise ValueError('Usa audio mono PCM de 16 kHz y hasta 60 segundos.')
            samples = source.readframes(source.getnframes())
            if len(samples) != source.getnframes() * 2:
                raise ValueError('Grabación incompleta.')
        canonical = io.BytesIO()
        with wave.open(canonical, 'wb') as output:
            output.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            output.writeframes(samples)
    except (wave.Error, EOFError):
        raise ValueError('Grabación WAV inválida.') from None
    if not _transcription.acquire(blocking=False):
        raise ValueError('Ya hay una transcripción local en curso. Espera antes de intentarlo de nuevo.')
    try:
        # stdin/stdout only: no recording files, shell, network, or API fallback.
        # A virtual output prefix enables stdout callbacks for stdin input in v1.9.5;
        # no output-file format is enabled, so no transcript file is created.
        result = subprocess.run([str(binary_path()), '-m', str(model_path()), '-f', '-', '-of', 'voxel-transcript', '-l', 'es', '-t', '4', '-nt', '-np', '-ng'], input=canonical.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False, shell=False)
        if result.returncode != 0:
            raise ValueError('El motor local no pudo transcribir. Reinicia la app y comprueba el modelo de voz.')
        text = result.stdout.decode('utf-8', errors='replace').strip()
        if not text or text in ('[BLANK_AUDIO]', '[Silence]', '(silencio)'):
            raise ValueError('No detecté una frase. Acerca el micrófono y vuelve a intentarlo.')
        return text[:6000]
    except subprocess.TimeoutExpired:
        raise ValueError('La transcripción local tardó demasiado. Prueba con una frase más corta.') from None
    except OSError:
        raise ValueError('No pude iniciar el motor de voz local. Revisa la instalación de la app.') from None
    finally:
        _transcription.release()
