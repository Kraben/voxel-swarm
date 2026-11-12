"""Pruebas con datos temporales. No ejecutan apps ni tocan memoria personal."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory()
os.environ.update(GHOST_DATA_DIR=TEMP.name, GHOST_API_TOKEN='test-access-token', GHOST_ALLOWED_HOSTS='testserver,localhost,127.0.0.1', GHOST_LEARNING='0', GHOST_PUBLIC='0', GHOST_ENABLE_SKILLS='0')
from fastapi.testclient import TestClient
import servidor as server
import skills_mac
client = TestClient(server.app)
HEADERS = {'Authorization':'Bearer test-access-token'}

class SecurityTests(unittest.TestCase):
    def setUp(self):
        server.limites.clear()
        self.session = str(uuid4())
    def post(self, text, **extra):
        return client.post('/chat',headers=HEADERS,json={'texto':text,'session_id':self.session,**extra})
    def test_auth_origin_body(self):
        self.assertEqual(client.get('/api/memory').status_code,401)
        self.assertEqual(client.get('/api/memory',headers={**HEADERS,'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(client.get('/api/memory',headers={**HEADERS,'sec-fetch-site':'cross-site'}).status_code,403)
        self.assertEqual(client.post('/chat',headers=HEADERS,json={'texto':'x'*21000,'session_id':self.session}).status_code,413)
        self.assertEqual(self.post('   ').status_code,422)
        self.assertEqual(self.post('x'*6001).status_code,422)
        self.assertEqual(client.get('/originales/servidor.py').status_code,404)
    def test_history_isolation_and_context(self):
        with patch.object(server.cerebro,'responder_chat',return_value='Enlace listo.'):
            self.assertEqual(self.post('Hola').status_code,200)
        own = client.get('/api/history/'+self.session,headers=HEADERS).json()
        self.assertEqual(own['turnos'][0]['usuario'],'Hola')
        other = client.get('/api/history/'+str(uuid4()),headers=HEADERS).json()
        self.assertEqual(other['turnos'],[])
        def responder(text):
            self.assertEqual(server.cerebro.HISTORIAL_SESION[-1]['content'],'Enlace listo.')
            return 'Recuerdo el contexto.'
        with patch.object(server.cerebro,'responder_chat',side_effect=responder):
            self.assertEqual(self.post('Continuar').status_code,200)
    def test_memory_and_style(self):
        brain = server.cerebro
        brain.guardar_json(brain.ARCHIVO_MEMORIA_USUARIO,[{'categoria':'gustos','dato':'Le gusta programar'}])
        self.assertIn('programar', self.post('ver memoria').json()['respuesta'])
        self.assertEqual(self.post('olvidar tu 1').json()['respuesta'],'Recuerdo eliminado.')
        with patch.object(brain,'responder_chat',return_value='Respuesta'):
            self.post('Hola de nuevo')
        self.post('así: Sistemas listos, Guardián.')
        self.assertIn('Sistemas listos',brain.construir_system_prompt())
    def test_skills_default_and_confirmation(self):
        with patch.object(skills_mac.subprocess,'run') as run:
            self.assertIn('bloqueadas',self.post('abre calculator').json()['respuesta'])
            run.assert_not_called()
        with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1'}):
            with patch.object(skills_mac,'ejecutar_skill',return_value='App abierta') as execute:
                response=self.post('abre calculator').json()
                self.assertEqual(response['respuesta'],'App abierta');self.assertFalse(response.get('requiere_confirmacion',False))
                execute.assert_called_once_with('abre calculator',autorizado=False)
        with patch.dict(os.environ,{'GHOST_PUBLIC':'1','GHOST_ENABLE_SKILLS':'1'}), patch.object(skills_mac.subprocess,'run') as run:
            self.assertIn('bloqueadas',skills_mac.ejecutar_skill('abre calculator',autorizado=True))
            run.assert_not_called()
    def test_ollama_error_and_busy(self):
        with patch.object(server.cerebro,'responder_chat',side_effect=ConnectionError('secret endpoint')):
            result = self.post('Hola')
            self.assertEqual(result.status_code,503)
            self.assertNotIn('secret endpoint',result.text)
        server.LOCK.acquire()
        try: self.assertEqual(self.post('Hola').status_code,409)
        finally: server.LOCK.release()
    def test_desktop_preview_confirmation_and_voice_guards(self):
        root=Path(TEMP.name)/('desktop-'+self.session);root.mkdir();(root/'nota.txt').write_text('contenido')
        with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_DESKTOP_ROOT':str(root)}),patch.object(server.cerebro,'responder_chat') as model:
            preview=self.post('organiza mi escritorio').json()
            model.assert_not_called();self.assertTrue((root/'nota.txt').exists())
            action={'plan_id':preview['accion']['id'],'session_id':self.session}
            self.assertEqual(client.post('/api/actions/execute',headers=HEADERS,json=action).status_code,400)
            result=client.post('/api/actions/execute',headers=HEADERS,json={**action,'confirmar':True})
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['resultado']['moved'],1)
            undo=self.post('deshacer organización del escritorio').json()['accion']
            self.assertEqual(client.post('/api/actions/execute',headers=HEADERS,json={'plan_id':undo['id'],'session_id':self.session,'confirmar':True}).status_code,200)
            self.assertEqual((root/'nota.txt').read_text(),'contenido')
        audio={'audio':'Zml4dHVyZQ==','mime':'audio/webm','consent':True}
        self.assertEqual(client.post('/api/voice/transcribe',headers=HEADERS,json=audio).status_code,403)
        with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'1'}),patch.object(server.voice_actions,'transcribe',return_value='hola') as transcribe:
            self.assertEqual(client.post('/api/voice/transcribe',headers=HEADERS,json={**audio,'consent':False}).status_code,400)
            self.assertEqual(client.post('/api/voice/transcribe',headers=HEADERS,json=audio).json()['texto'],'hola')
            transcribe.assert_called_once()

    def test_web_ready_by_default_and_never_runs_model(self):
        with patch.dict(os.environ,{},clear=False),patch.object(server.web_actions,'search',return_value=[{'title':'Fuente','body':'Texto','url':'https://example.com'}]) as search,patch.object(server.cerebro,'responder_chat') as model:
            prior=os.environ.pop('GHOST_ENABLE_WEB',None)
            try:
                result=self.post('busca documentación de Python').json()
                self.assertEqual(result['fuentes'][0]['url'],'https://example.com')
                search.assert_called_once();model.assert_not_called()
            finally:
                if prior is not None:os.environ['GHOST_ENABLE_WEB']=prior

    def test_direct_question_searches_and_optout_uses_conversation(self):
        with patch.object(server.web_actions,'search',return_value=[{'title':'JSON','body':'Formato JSON','url':'https://example.com/json'}]) as search,patch.object(server.cerebro,'responder_chat',return_value='Explicación sin consultar la web.') as model:
            result=self.post('qué es JSON').json()
            self.assertTrue(result['busqueda']['automatic']);self.assertEqual(result['fuentes'][0]['title'],'JSON')
            search.assert_called_once_with('qué es JSON');model.assert_not_called()
            self.post('qué es JSON sin internet');model.assert_called_once();self.assertEqual(search.call_count,1)

    def test_local_search_clarification_confirmation_and_privacy(self):
        with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1'}),patch.object(server.file_actions,'search',return_value='Encontré estos archivos por nombre:\n/fixture/private.pdf') as search,patch.object(server.web_actions,'search') as web,patch.object(server.cerebro,'responder_chat',return_value='Hola') as model:
            self.assertEqual(self.post('puedes buscar un archivo en mi Mac?').json()['respuesta'],server.file_actions.PROMPT)
            self.assertTrue(self.post('private.pdf').json()['requiere_confirmacion'])
            search.assert_not_called()
            self.assertIn('private.pdf',self.post('private.pdf',confirmar_skill=True).json()['respuesta'])
            search.assert_called_once_with('private.pdf',capture=[]);web.assert_not_called();model.assert_not_called()
            self.post('Hola')
            self.assertNotIn('/fixture/private.pdf',str(server.cerebro.HISTORIAL_SESION))
        with patch.object(server.file_actions,'search') as search:
            self.assertIn('Skills y permisos',self.post('busca el archivo prueba').json()['respuesta']);search.assert_not_called()

    def test_search_group_confirm_and_undo(self):
        root=Path(TEMP.name).resolve()/('group-'+self.session);root.mkdir()
        source=root/'downloads';source.mkdir();desktop=root/'desktop';desktop.mkdir()
        (source/'datos.csv').write_text('private data')
        with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_SEARCH_ROOT':str(source),'GHOST_DESKTOP_ROOT':str(desktop)}),patch.object(server.cerebro,'responder_chat') as model,patch.object(server.web_actions,'search') as web:
            self.post('busca un archivo con extensión .csv',confirmar_skill=True)
            preview=self.post('¿Puedes ayudarme a organizar esos archivos en una carpeta?').json()
            self.assertEqual(preview['accion']['kind'],'group');self.assertTrue((source/'datos.csv').exists())
            action={'plan_id':preview['accion']['id'],'session_id':self.session}
            self.assertEqual(client.post('/api/actions/execute',headers=HEADERS,json=action).status_code,400)
            result=client.post('/api/actions/execute',headers=HEADERS,json={**action,'confirmar':True})
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['resultado']['moved'],1)
            self.assertFalse((source/'datos.csv').exists())
            undo=self.post('deshacer agrupación de archivos').json()['accion']
            result=client.post('/api/actions/execute',headers=HEADERS,json={'plan_id':undo['id'],'session_id':self.session,'confirmar':True})
            self.assertEqual(result.status_code,200);self.assertEqual((source/'datos.csv').read_text(),'private data')
            model.assert_not_called();web.assert_not_called()

    def test_native_tool_confirmation_bound_to_message_and_session(self):
        from agent_tools import CAPABILITIES
        CAPABILITIES.clear()
        response={'message':{'content':'','tool_calls':[{'function':{'name':'core_find_files','arguments':'{"term":".csv"}'}}]}}
        text='Necesito localizar mis hojas de cálculo guardadas'
        with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_PROVIDER':'openai','GHOST_API_BASE':'https://fixture.invalid/v1'}),patch.object(server.api_compatible,'chat',return_value=response) as model,patch.object(server.file_actions,'search',return_value='Encontré estos archivos por nombre: fixture') as search:
            pending=self.post(text).json();self.assertTrue(pending['requiere_confirmacion']);search.assert_not_called()
            request_id=pending['tool_request_id']
            self.assertEqual(self.post(text,tool_request_id=request_id).status_code,400)
            self.assertEqual(self.post('otro texto',confirmar_skill=True,tool_request_id=request_id).status_code,409)
            other=client.post('/chat',headers=HEADERS,json={'texto':text,'session_id':str(uuid4()),'confirmar_skill':True,'tool_request_id':request_id})
            self.assertEqual(other.status_code,409);search.assert_not_called()
            result=self.post(text,confirmar_skill=True,tool_request_id=request_id)
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['herramienta']['name'],'core_find_files')
            search.assert_called_once();model.assert_called_once()
            self.assertEqual(self.post(text,confirmar_skill=True,tool_request_id=request_id).status_code,409)
        CAPABILITIES.clear()

    def test_native_model_cannot_offer_disabled_tools_or_execute_shell(self):
        import agent_tools
        agent_tools.CAPABILITIES.clear()
        for name,args in [('core_open_app','{"name":"calculator"}'),('run_shell','{"command":"echo hi"}')]:
            response={'message':{'content':'','tool_calls':[{'function':{'name':name,'arguments':args}}]}}
            with patch.dict(os.environ,{'GHOST_PROVIDER':'openai','GHOST_API_BASE':'https://fixture.invalid/v1','GHOST_ENABLE_SKILLS':'0'}),patch.object(server.api_compatible,'chat',return_value=response),patch.object(skills_mac,'ejecutar_skill') as execute:
                self.assertIn('No ejecuté',self.post('Ayúdame con una tarea').json()['respuesta']);execute.assert_not_called()
        agent_tools.CAPABILITIES.clear()

    def test_voxel_identity_keeps_memory_and_legacy_commands(self):
        brain=server.cerebro
        old={'nombre':'Ghost','descripcion':'Eres Ghost. Operas en una carcasa robótica. Mantienes una voz calmada.'}
        brain.guardar_json(brain.ARCHIVO_IDENTIDAD,old)
        prompt=brain.construir_system_prompt()
        self.assertIn('Enjambre de Vóxeles holográfico',prompt)
        self.assertIn('No tienes forma física',prompt)
        self.assertNotIn('carcasa robótica',prompt)
        self.assertEqual(brain.cargar_json(brain.ARCHIVO_IDENTIDAD,{}),old)
        brain.guardar_json(brain.ARCHIVO_CORE_MEMORY,[{'categoria':'estilo','dato':'voz calmada'}])
        self.assertIn('voz calmada',self.post('ver memoria').json()['respuesta'])
        self.assertEqual(self.post('olvidar nucleo 1').json()['respuesta'],'Recuerdo eliminado.')

    def test_rate_limit(self):
        for _ in range(30):
            self.assertEqual(self.post('ver memoria').status_code,200)
        self.assertEqual(self.post('ver memoria').status_code,429)

if __name__ == '__main__': unittest.main()

class LocalVoiceAPITests(unittest.TestCase):
    def setUp(self):
        server.limites.clear()
    def test_model_install_and_status_require_owner_local_mode_and_microphone(self):
        from unittest.mock import patch
        with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'1','GHOST_PROVIDER':'ollama'}),patch.object(server,'PUBLICO',False),patch.object(server.local_voice,'status',return_value={'ready':False,'mode':'local'}),patch.object(server.local_voice,'start_download',return_value={'ready':False,'download':{'state':'downloading'}}) as install:
            self.assertEqual(client.post('/api/voice/local/install',json={'consent':True}).status_code,401)
            self.assertEqual(client.post('/api/voice/local/install',headers=HEADERS,json={'consent':False}).status_code,400)
            install.assert_not_called()
            self.assertEqual(client.get('/api/voice/local/status',headers=HEADERS).status_code,200)
            self.assertEqual(client.post('/api/voice/local/install',headers=HEADERS,json={'consent':True}).status_code,200)
            install.assert_called_once()
        for env,public in [({'GHOST_ENABLE_MIC':'0','GHOST_PROVIDER':'ollama'},False),({'GHOST_ENABLE_MIC':'1','GHOST_PROVIDER':'ollama'},True)]:
            with patch.dict(os.environ,env),patch.object(server,'PUBLICO',public),patch.object(server.local_voice,'start_download') as install:
                self.assertIn(client.post('/api/voice/local/install',headers=HEADERS,json={'consent':True}).status_code,(403,409));install.assert_not_called()
    def test_wav_transcription_endpoint_keeps_existing_consent_gate(self):
        import base64
        with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'1','GHOST_PROVIDER':'ollama'}),patch.object(server,'PUBLICO',False),patch.object(server.voice_actions,'transcribe',return_value='Hola local') as transcribe:
            payload={'audio':base64.b64encode(b'fixture').decode(),'mime':'audio/wav','consent':False}
            self.assertEqual(client.post('/api/voice/transcribe',headers=HEADERS,json=payload).status_code,400);transcribe.assert_not_called()
            response=client.post('/api/voice/transcribe',headers=HEADERS,json={**payload,'consent':True})
            self.assertEqual(response.json()['texto'],'Hola local')

class ApplicationCatalogAPITests(unittest.TestCase):
    def setUp(self):server.limites.clear()
    def test_inventory_is_owner_only_local_and_available_before_enabling_skills(self):
        rows=[{'id':'/Applications/Fixture.app','name':'Fixture','command':'Fixture','aliases':['fixture'],'path':'/Applications/Fixture.app'}]
        with patch.object(server.app_catalog,'installed_apps',return_value=rows) as scan,patch.object(server.skills_mac.platform,'system',return_value='Darwin'),patch.object(server,'PUBLICO',False),patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'0'}):
            self.assertEqual(client.get('/api/apps').status_code,401);scan.assert_not_called()
            self.assertEqual(client.get('/api/apps',headers={**HEADERS,'Origin':'https://untrusted.example'}).status_code,403);scan.assert_not_called()
            response=client.get('/api/apps',headers=HEADERS);self.assertEqual(response.status_code,200);self.assertEqual(response.json()['apps'],rows)
            with patch.object(server,'PUBLICO',True):self.assertEqual(client.get('/api/apps',headers=HEADERS).status_code,403)
    def test_voice_text_open_request_uses_current_selection_without_repeated_confirmation(self):
        import json
        selected='/Applications/Fixture.app'
        rows=[{'id':selected,'name':'Fixture','command':'Fixture','aliases':['fixture'],'path':selected}]
        with patch.object(server.app_catalog,'installed_apps',return_value=rows),patch.object(server.skills_mac.platform,'system',return_value='Darwin'),patch.object(server,'PUBLICO',False),patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_ALLOWED_APPS_JSON':json.dumps([selected])}),patch.object(server.skills_mac.subprocess,'run') as launch:
            payload={'texto':'Abre la app Fixture.','session_id':str(uuid4())}
            response=client.post('/chat',headers=HEADERS,json=payload);self.assertFalse(response.json().get('requiere_confirmacion',False));self.assertIn('He abierto',response.json()['respuesta']);launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0],['/usr/bin/open','-a',selected])
            launch.reset_mock()
            with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':'[]'}):
                response=client.post('/chat',headers=HEADERS,json={**payload,'confirmar_skill':True});self.assertIn('fuera',response.json()['respuesta']);launch.assert_not_called()

class WakeTranscriptionAPITests(unittest.TestCase):
    def setUp(self):server.limites.clear()
    def payload(self,**extra):
        import base64
        return {'audio':base64.b64encode(b'fake wav').decode(),'mime':'audio/wav','consent':True,'wake':True,**extra}
    def test_background_audio_is_local_and_non_keyword_never_reaches_whisper_or_cloud(self):
        with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'1','GHOST_PROVIDER':'openai'}),patch.object(server,'PUBLICO',False),patch.object(server.wake_voice,'detect',return_value=(False,None)),patch.object(server.local_voice,'transcribe') as whisper,patch.object(server.voice_actions.httpx,'post') as cloud:
            result=client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload())
            self.assertEqual(result.json(),{'wake':False,'texto':''});whisper.assert_not_called();cloud.assert_not_called()
    def test_keyword_alone_and_keyword_with_command(self):
        with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'1','GHOST_PROVIDER':'openai'}),patch.object(server,'PUBLICO',False),patch.object(server.local_voice,'transcribe',return_value='abre Safari') as whisper,patch.object(server.voice_actions.httpx,'post') as cloud:
            with patch.object(server.wake_voice,'detect',return_value=(True,None)):
                result=client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload());self.assertEqual(result.json(),{'wake':True,'texto':''});whisper.assert_not_called()
            with patch.object(server.wake_voice,'detect',return_value=(True,b'command wav')):
                result=client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload());self.assertEqual(result.json(),{'wake':True,'texto':'abre Safari'});whisper.assert_called_once_with(b'command wav','audio/wav')
            cloud.assert_not_called()
    def test_gate_requires_auth_microphone_and_consent_and_blocks_public(self):
        with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'1'}),patch.object(server,'PUBLICO',False),patch.object(server.wake_voice,'detect') as detector:
            self.assertEqual(client.post('/api/voice/local/transcribe',json=self.payload()).status_code,401)
            self.assertEqual(client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload(consent=False)).status_code,400)
            with patch.object(server,'PUBLICO',True):self.assertEqual(client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload()).status_code,403)
            with patch.dict(os.environ,{'GHOST_ENABLE_MIC':'0'}):self.assertEqual(client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload()).status_code,403)
            self.assertEqual(client.post('/api/voice/local/transcribe',headers=HEADERS,json=self.payload(audio='not-base64')).status_code,400);detector.assert_not_called()
