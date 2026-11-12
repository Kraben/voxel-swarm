import os,json,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import httpx,ollama
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import agent_tools as tools,api_compatible

class AgentToolTests(unittest.TestCase):
 def setUp(self):tools.CAPABILITIES.clear()
 def test_same_catalog_for_ollama_and_cloud(self):
  catalog=tools.available(local=True,skills=True,web=True,text='localiza mis hojas')
  call={'function':{'name':'core_find_files','arguments':{'term':'.csv'}}}
  client=Mock();client.chat.return_value={'message':{'content':'','tool_calls':[call]}}
  with patch.dict(os.environ,{'GHOST_PROVIDER':'ollama','OLLAMA_HOST':'http://fixture.invalid'}),tools.scope(catalog):
   with self.assertRaises(tools.ToolSelected) as selected:tools.request('fixture',[],client)
   self.assertEqual(selected.exception.call['arguments'],{'term':'.csv'})
  for host in ('https://api.openai.com/v1','https://generativelanguage.googleapis.com/v1beta/openai','https://api.groq.com/openai/v1','https://api.deepseek.com','https://openrouter.ai/api/v1'):
   api_call={'function':{'name':'core_find_files','arguments':json.dumps({'term':'.csv'})}}
   response=httpx.Response(200,json={'choices':[{'message':{'content':None,'tool_calls':[api_call]}}]},request=httpx.Request('POST',host+'/chat/completions'))
   with patch.dict(os.environ,{'GHOST_PROVIDER':'openai','GHOST_API_BASE':host}),patch.object(api_compatible.httpx,'post',return_value=response) as post,tools.scope(catalog):
    with self.assertRaises(tools.ToolSelected) as selected:tools.request('fixture',[],None)
    self.assertEqual(selected.exception.call['name'],'core_find_files')
    self.assertEqual(post.call_args.kwargs['json']['tools'],catalog)
 def test_permissions_invalid_calls_and_no_multi_execution(self):
  catalog=tools.available(local=True,skills=True,web=True,text='hola')
  for name,args in [('shell',{'command':'whoami'}),('core_find_files',{'term':'/private/file'}),('core_group_results',{'path':'/tmp'}),('core_open_app',{'name':'Notes; say hi'}),('core_search_web',{'query':'sk-secrethere'})]:
   with self.assertRaises(tools.InvalidTool):tools.validate({'function':{'name':name,'arguments':args}},catalog)
  self.assertEqual(tools.available(local=False,skills=True,web=True,text='hola'),[])
  for private in ['ayuda sin internet','revisa mis tablas','mi clave api secreta','archivo /Users/fixture/informe']:
   self.assertNotIn('core_search_web',[t['function']['name'] for t in tools.available(local=True,skills=True,web=True,text=private)])
  client=Mock();client.chat.return_value={'message':{'tool_calls':[{},{}]}}
  with patch.dict(os.environ,{'GHOST_PROVIDER':'ollama'}),tools.scope(catalog):
   with self.assertRaises(tools.InvalidTool):tools.request('fixture',[],client)
 def test_unsupported_falls_back_and_auth_errors_do_not(self):
  client=Mock();client.chat.side_effect=ollama.ResponseError('model does not support tools',400)
  catalog=tools.available(local=True,skills=True,web=True,text='hola')
  with patch.dict(os.environ,{'GHOST_PROVIDER':'ollama','OLLAMA_HOST':'http://fixture.invalid'}),tools.scope(catalog) as state:
   self.assertIsNone(tools.request('fixture',[],client));self.assertEqual(state['mode'],'compatibility')
   self.assertIsNone(tools.request('fixture',[],client));client.chat.assert_called_once()
  tools.CAPABILITIES.clear();client.chat.side_effect=ollama.ResponseError('authentication failed',401)
  with patch.dict(os.environ,{'GHOST_PROVIDER':'ollama'}),tools.scope(catalog):
   with self.assertRaises(ollama.ResponseError):tools.request('fixture',[],client)
  self.assertEqual(tools.mode('fixture'),'unverified')

 def test_cloud_unsupported_only_for_tools_and_not_billing_errors(self):
  catalog=tools.available(local=True,skills=True,web=True,text='hola')
  request=httpx.Request('POST','https://fixture.invalid/v1/chat/completions')
  for status,message,expected in [(400,'tools not supported',True),(401,'invalid API key',False),(429,'quota exceeded',False)]:
   tools.CAPABILITIES.clear()
   response=httpx.Response(status,json={'error':{'message':message}},request=request)
   with patch.dict(os.environ,{'GHOST_PROVIDER':'openai','GHOST_API_BASE':'https://fixture.invalid/v1'}),patch.object(api_compatible.httpx,'post',return_value=response),tools.scope(catalog) as state:
    if expected:self.assertIsNone(tools.request('fixture',[],None));self.assertEqual(state['mode'],'compatibility')
    else:
     with self.assertRaises(httpx.HTTPStatusError):tools.request('fixture',[],None)

if __name__=='__main__':unittest.main()
