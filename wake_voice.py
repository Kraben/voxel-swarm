"""Local, restricted-vocabulary Spanish wake detection. No background transcripts."""
import ctypes as c
import io
import json
from pathlib import Path
import sys
import threading
import wave

_lock=threading.RLock()
_library=None
_model=None

def runtime_root():
    if getattr(sys,'frozen',False):return Path(sys._MEIPASS)/'voice'
    return Path(__file__).parent/'desktop'/'voice-runtime'

def library_name():
    if sys.platform == 'win32':
        return 'libvosk.dll'
    if sys.platform == 'darwin':
        return 'libvosk.dylib'
    return 'libvosk.so'

def available():
    root=runtime_root()
    lib=root/library_name()
    return lib.is_file() and (root/'wake-model'/'am'/'final.mdl').is_file()

def _load():
    global _library,_model
    if _library is None:
        root=runtime_root()
        lib_path=root/library_name()
        if sys.platform=='win32' and hasattr(os,'add_dll_directory') and root.is_dir():
            try:os.add_dll_directory(str(root))
            except OSError:pass
        lib=c.CDLL(str(lib_path))
        signatures=[('vosk_set_log_level',[c.c_int],None),('vosk_model_new',[c.c_char_p],c.c_void_p),('vosk_model_free',[c.c_void_p],None),('vosk_recognizer_new_grm',[c.c_void_p,c.c_float,c.c_char_p],c.c_void_p),('vosk_recognizer_new',[c.c_void_p,c.c_float],c.c_void_p),('vosk_recognizer_accept_waveform',[c.c_void_p,c.c_char_p,c.c_int],c.c_int),('vosk_recognizer_final_result',[c.c_void_p],c.c_char_p),('vosk_recognizer_set_words',[c.c_void_p,c.c_int],None),('vosk_recognizer_free',[c.c_void_p],None)]
        for name,arguments,result in signatures:
            function=getattr(lib,name);function.argtypes=arguments;function.restype=result
        lib.vosk_set_log_level(-1);_library=lib
    if _model is None:
        _model=_library.vosk_model_new(str(runtime_root()/'wake-model').encode())
        if not _model:raise ValueError('No pude cargar el detector de Oye Vox. Reinstala el paquete completo.')
    return _library,_model

def release():
    global _model
    with _lock:
        if _model and _library:_library.vosk_model_free(_model)
        _model=None

def keyword_end(words):
    """Accept Oye Vox at the start, allowing only a short preaudio artifact."""
    for index,row in enumerate(words):
        if row.get('word')!='oye':continue
        if row.get('start',99)>.9:return None
        before=words[:index]
        if any(item.get('word')!='[unk]' for item in before):return None
        if sum(max(0,item.get('end',0)-item.get('start',0)) for item in before)>.14:return None
        if index+1>=len(words):return None
        following=words[index+1]
        if following.get('word')!='vox' or row.get('conf',0)<.75 or following.get('conf',0)<.9:return None
        if not -.03<=following.get('start',99)-row.get('end',0)<=.25:return None
        if not .12<=following.get('end',0)-following.get('start',0)<=.65:return None
        if not .18<=following.get('end',0)-row.get('start',0)<=1.1:return None
        return following['end']
    return None

def detect(audio):
    try:
        with wave.open(io.BytesIO(audio),'rb') as source:
            if source.getnchannels()!=1 or source.getsampwidth()!=2 or source.getframerate()!=16000 or not 0<source.getnframes()<=968000:raise ValueError('Formato de audio local no válido.')
            pcm=source.readframes(source.getnframes())
            if len(pcm)!=source.getnframes()*2:raise ValueError('Audio incompleto.')
    except (wave.Error,EOFError):raise ValueError('Grabación WAV inválida.') from None
    with _lock:
        try:
            lib,model=_load();recognizer=lib.vosk_recognizer_new_grm(model,16000.,b'["oye vox", "[unk]"]')
            if not recognizer:raise ValueError('No pude iniciar el detector local de Oye Vox.')
            try:
                lib.vosk_recognizer_set_words(recognizer,1)
                if lib.vosk_recognizer_accept_waveform(recognizer,pcm,len(pcm))<0:raise ValueError('Falló el detector local.')
                result=json.loads(lib.vosk_recognizer_final_result(recognizer))
            finally:lib.vosk_recognizer_free(recognizer)
        except (OSError,AttributeError):raise ValueError('Falta el motor local de Oye Vox. Usa la app completa.') from None
        end=keyword_end(result.get('result',[]))
        if end is None:return False,None
    # Only audio after the detected keyword can become a command. The wake
    # detector's guesses for other words are never stored or sent to an LLM.
    offset=max(0,int((end+.04)*16000))*2
    tail=pcm[offset:]
    voiced_frames=0
    import struct
    samples=[value[0] for value in struct.iter_unpack('<h',tail)]
    for start in range(0,len(samples),160):
        frame=samples[start:start+160]
        if frame and (sum(value*value for value in frame)/len(frame))**.5>400:voiced_frames+=1
    if voiced_frames<25:return True,None
    output=io.BytesIO()
    with wave.open(output,'wb') as target:
        target.setparams((1,2,16000,0,'NONE','not compressed'));target.writeframes(tail)
    return True,output.getvalue()
