import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import api_compatible

class APITests(unittest.TestCase):
    def test_chat_and_memory_adapter(self):
        request=httpx.Request('POST','https://fixture.invalid/v1/chat/completions')
        response=httpx.Response(200,json={'choices':[{'message':{'content':'Respuesta de prueba'}}]},request=request)
        with patch.dict(os.environ,{'GHOST_API_BASE':'https://fixture.invalid/v1','GHOST_API_KEY':'fixture-key'}),patch.object(api_compatible.httpx,'post',return_value=response) as post:
            self.assertEqual(api_compatible.chat('fixture',[{'role':'user','content':'hola'}])['message']['content'],'Respuesta de prueba')
            self.assertEqual(api_compatible.generate('fixture','extraer dato')['response'],'Respuesta de prueba')
            self.assertEqual(post.call_args.kwargs['headers']['Authorization'],'Bearer fixture-key')
            self.assertFalse(post.call_args.kwargs['follow_redirects'])
    def test_error_and_incompatible_output(self):
        request=httpx.Request('POST','https://fixture.invalid/v1/chat/completions')
        with patch.dict(os.environ,{'GHOST_API_BASE':'https://fixture.invalid/v1'}):
            for status,payload,error in [(401,{'error':'private details'},httpx.HTTPStatusError),(200,{'choices':[]},ValueError)]:
                with patch.object(api_compatible.httpx,'post',return_value=httpx.Response(status,json=payload,request=request)):
                    with self.assertRaises(error):api_compatible.chat('fixture',[])
