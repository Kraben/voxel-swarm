import base64
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import voice_actions,web_actions

class CapabilityTests(unittest.TestCase):
    def test_gemini_audio_without_microphone_or_paid_calls(self):
        response=httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'Hola Ghost'}]}}]},request=httpx.Request('POST','https://fixture.invalid'))
        with patch.dict(os.environ,{'GHOST_PROVIDER':'openai','GHOST_API_BASE':'https://generativelanguage.googleapis.com/v1beta/openai','GHOST_API_KEY':'fixture','GHOST_MODEL':'models/gemini-fixture'}),patch.object(voice_actions.httpx,'post',return_value=response) as request:
            self.assertTrue(voice_actions.provider_info()['supported'])
            self.assertEqual(voice_actions.transcribe(base64.b64encode(b'fixture audio').decode(),'audio/webm;codecs=opus'),'Hola Ghost')
            args=request.call_args
            self.assertTrue(args.args[0].endswith('/models/gemini-fixture:generateContent'))
            self.assertEqual(args.kwargs['json']['contents'][0]['parts'][1]['inlineData']['mimeType'],'audio/webm')
            self.assertNotIn('memoria',str(args.kwargs['json']))
            with self.assertRaises(ValueError):voice_actions.transcribe('not-base64','audio/webm')
        with patch.dict(os.environ,{'GHOST_PROVIDER':'ollama','GHOST_API_BASE':'http://127.0.0.1:11434'}),patch.object(voice_actions.local_voice,'status',return_value={'mode':'local','supported':True,'ready':False}):
            self.assertEqual(voice_actions.provider_info()['mode'],'local')
            self.assertFalse(voice_actions.provider_info()['ready'])
    def test_sources_are_real_search_records_not_generated_urls(self):
        with patch.object(web_actions,'fetch_engine') as cls:
            cls.return_value=[{'title':'Consulta','body':'Texto de la consulta','href':'https://example.com'},{'title':'bad','href':'javascript:alert(1)'}]
            self.assertEqual(web_actions.search('consulta')[0]['url'],'https://example.com')
            self.assertEqual(len(web_actions.search('consulta')),1)
        self.assertEqual(web_actions.query_from('busca en internet noticias de tecnología'),'noticias de tecnología')
        self.assertEqual(web_actions.query_from('busca información de Python'),'información de Python')
        self.assertIsNone(web_actions.query_from('busca el archivo informe'))
        self.assertIsNone(web_actions.query_from('no debes buscar en internet nada'))
