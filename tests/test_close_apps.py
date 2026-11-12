import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import skills_mac,agent_tools,tool_runtime
APP={'id':'/System/Applications/Notes.app','name':'Notas','aliases':['notas','notes']}
class CloseAppsTests(unittest.TestCase):
 def test_close_uses_catalog_and_normal_quit(self):
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_PUBLIC':'0'}),patch.object(skills_mac.platform,'system',return_value='Darwin'),patch.object(skills_mac.app_catalog,'resolve_app',return_value=(APP,None)),patch.object(skills_mac.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='CLOSED',stderr='')) as run:
   self.assertIn('He cerrado Notas',skills_mac.ejecutar_skill('cierra Notas'))
   self.assertEqual(run.call_args.args[0],['/usr/bin/osascript','-','--',APP['id']])
   self.assertNotIn(APP['id'],run.call_args.kwargs['input']);self.assertFalse(run.call_args.kwargs['shell'])
 def test_denied_and_unsaved(self):
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'0','GHOST_PUBLIC':'0'}),patch.object(skills_mac.subprocess,'run') as run:
   self.assertIn('bloqueadas',skills_mac.ejecutar_skill('cierra Notas'));run.assert_not_called()
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_PUBLIC':'0'}),patch.object(skills_mac.platform,'system',return_value='Darwin'),patch.object(skills_mac.app_catalog,'resolve_app',return_value=(APP,None)),patch.object(skills_mac.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='STILL_RUNNING',stderr='')):
   self.assertIn('Sigue abierta',skills_mac.ejecutar_skill('cierra Notas'))
 def test_model_cannot_close_without_explicit_request(self):
  with patch.object(skills_mac.app_catalog,'resolve_app',return_value=(APP,None)):
   self.assertTrue(skills_mac.cierre_pedido('¿Puedes cerrar Notas?','Notas'))
   for text in ['no cierres Notas','abre Notas','qué aplicaciones puedes cerrar','cierra Safari']:
    self.assertFalse(skills_mac.cierre_pedido(text,'Notas'),text)
  self.assertNotIn('core_music',[row['function']['name'] for row in agent_tools.CATALOG])
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1'}),patch.object(skills_mac,'ejecutar_skill') as execute:
   result=tool_runtime.execute({'name':'core_close_app','arguments':{'name':'Notas'}},'session','/tmp',request_text='hola')
   execute.assert_not_called();self.assertIn('directamente',result['respuesta'])
