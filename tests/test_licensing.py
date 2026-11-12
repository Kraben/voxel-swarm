import os,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import licensing,api_compatible
FIXTURE=json.loads((Path(__file__).parent/'license-vectors.json').read_text())
class LicensingTests(unittest.TestCase):
 def test_signed_shared_grant(self):
  f=FIXTURE
  self.assertEqual(licensing.verify_license(f['token'],f['publicKey'],1500)['plan'],'pro')
  for now in [500,2000]:self.assertEqual(licensing.verify_license(f['token'],f['publicKey'],now)['plan'],'free')
  self.assertEqual(licensing.verify_license('X'+f['token'][1:],f['publicKey'],1500)['plan'],'free')
  self.assertEqual(licensing.verify_license(f['token'],None,1500)['plan'],'free')
 def test_provider_policy(self):
  self.assertTrue(licensing.free_provider('ollama','http://localhost:11434'))
  self.assertTrue(licensing.free_provider('openai','https://generativelanguage.googleapis.com/v1beta/openai'))
  for host in ['https://generativelanguage.googleapis.com.evil.test/v1beta/openai','https://generativelanguage.googleapis.com:444/v1beta/openai','https://api.openai.com/v1','https://generativelanguage.googleapis.com/other']:
   self.assertFalse(licensing.free_provider('openai',host))
 def test_backend_blocks_before_network(self):
  with patch.dict(os.environ,{'GHOST_LICENSE_ENFORCE':'1','GHOST_PROVIDER':'openai','GHOST_API_BASE':'https://api.openai.com/v1','GHOST_LICENSE_FILE':'/missing/voxel-license.json'}),patch.object(api_compatible.httpx,'post') as network:
   with self.assertRaises(licensing.LicenseRequired):api_compatible.chat('fixture',[])
   network.assert_not_called()
 def test_pro_allows_other_providers(self):
  with patch.dict(os.environ,{'GHOST_LICENSE_ENFORCE':'1','GHOST_PROVIDER':'openai','GHOST_API_BASE':'https://api.openai.com/v1'}),patch.object(licensing,'current',return_value={'plan':'pro'}):licensing.require_provider()
