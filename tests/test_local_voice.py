"""Local speech tests: temporary files only, no microphone, paid API or real download."""
import base64
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import wave
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_voice
import voice_actions

def wav(seconds=.5, channels=1, rate=16000):
    buf=io.BytesIO()
    with wave.open(buf,'wb') as out:
        out.setparams((channels,2,rate,0,'NONE','not compressed'))
        out.writeframes(b'\x01\x01'*int(seconds*rate)*channels)
    return buf.getvalue()

class LocalVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.binary=self.root/'whisper-cli';self.binary.write_bytes(b'fixture executable');self.binary.chmod(0o700)
        self.env=patch.dict(os.environ,{'GHOST_VOICE_MODEL_DIR':str(self.root),'GHOST_WHISPER_CLI':str(self.binary),'GHOST_PROVIDER':'ollama'})
        self.env.start();self.addCleanup(self.env.stop)
        self.state=patch.dict(local_voice._state,{'state':'idle','received':0,'total':7,'error':''},clear=True);self.state.start();self.addCleanup(self.state.stop)
        local_voice._cancel.clear()
    def test_local_route_never_calls_cloud_even_if_local_engine_fails(self):
        with patch.object(local_voice,'transcribe',return_value='Hola local') as transcribe,patch.object(voice_actions.httpx,'post') as cloud:
            result=voice_actions.transcribe(base64.b64encode(wav()).decode(),'audio/wav')
            self.assertEqual(result,'Hola local');cloud.assert_not_called();transcribe.assert_called_once()
        with patch.object(local_voice,'transcribe',side_effect=ValueError('No model')),patch.object(voice_actions.httpx,'post') as cloud:
            with self.assertRaises(ValueError):voice_actions.transcribe(base64.b64encode(wav()).decode(),'audio/wav')
            cloud.assert_not_called()
    def test_audio_goes_to_stdin_and_never_to_shell_or_recording_file(self):
        with patch.object(local_voice,'status',return_value={'ready':True}),patch.object(local_voice.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'Hola local\n',b'')) as run:
            self.assertEqual(local_voice.transcribe(wav(),'audio/wav'),'Hola local')
            args=run.call_args.args[0];kw=run.call_args.kwargs
            self.assertIn('-ng',args);self.assertEqual(args[args.index('-f')+1],'-');self.assertFalse(kw['shell']);self.assertEqual(kw['input'][:4],b'RIFF')
            self.assertEqual(list(self.root.iterdir()),[self.binary])
    def test_invalid_audio_and_missing_model_do_not_launch_inference(self):
        with patch.object(local_voice,'status',return_value={'ready':True}),patch.object(local_voice.subprocess,'run') as run:
            for audio,mime in [(b'invalid','audio/wav'),(wav(channels=2),'audio/wav'),(wav(rate=8000),'audio/wav'),(wav(seconds=61),'audio/wav'),(wav(),'audio/webm')]:
                with self.subTest(mime=mime,length=len(audio)):
                    with self.assertRaises(ValueError):local_voice.transcribe(audio,mime)
            run.assert_not_called()
        with patch.object(local_voice,'status',return_value={'ready':False}):
            with self.assertRaisesRegex(ValueError,'Descarga'):local_voice.transcribe(wav(),'audio/wav')
    def test_model_cache_requires_exact_size_and_hash(self):
        model=b'model fixture';target=local_voice.model_path()
        with patch.object(local_voice,'MODEL_SIZE',len(model)),patch.object(local_voice,'MODEL_SHA256',hashlib.sha256(model).hexdigest()):
            self.assertFalse(local_voice.model_ready());target.write_bytes(b'x'*len(model));self.assertFalse(local_voice.model_ready())
            target.write_bytes(model);self.assertTrue(local_voice.model_ready())
    def test_verified_download_is_atomic_and_cancel_or_bad_hash_never_installs(self):
        model=b'model fixture'
        for outcome in ['ok','corrupt','cancel']:
            target=local_voice.model_path();target.unlink(missing_ok=True);local_voice._cancel.clear()
            response=MagicMock();response.__enter__.return_value=response
            def chunks(_size):
                yield model[:3]
                if outcome=='cancel':local_voice._cancel.set()
                yield model[3:]
            response.iter_bytes.side_effect=chunks
            with patch.object(local_voice.httpx,'stream',return_value=response) as download,patch.object(local_voice,'MODEL_SIZE',len(model)),patch.object(local_voice,'MODEL_SHA256',hashlib.sha256(model).hexdigest() if outcome!='corrupt' else 'bad'):
                local_voice._download()
                self.assertEqual(target.exists(),outcome=='ok');self.assertFalse(list(self.root.glob('*.part')))
                self.assertEqual(download.call_args.args,('GET',local_voice.MODEL_URL))
                self.assertEqual(local_voice._state['state'],{'ok':'ready','corrupt':'error','cancel':'cancelled'}[outcome])
    def test_timeout_and_busy_return_bounded_errors(self):
        with patch.object(local_voice,'status',return_value={'ready':True}),patch.object(local_voice.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixture',120)):
            with self.assertRaisesRegex(ValueError,'demasiado'):local_voice.transcribe(wav(),'audio/wav')
        local_voice._transcription.acquire()
        try:
            with patch.object(local_voice,'status',return_value={'ready':True}):
                with self.assertRaisesRegex(ValueError,'en curso'):local_voice.transcribe(wav(),'audio/wav')
        finally:local_voice._transcription.release()
