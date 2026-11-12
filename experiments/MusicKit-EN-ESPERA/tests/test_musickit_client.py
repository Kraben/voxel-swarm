import os,sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import musickit_client,music_actions
class MusicKitTests(unittest.TestCase):
 def test_no_remote_or_credentials(self):
  for url in ['https://example.org/music','http://localhost/music','http://127.0.0.1/music?x=1','http://user@127.0.0.1:123/music']:
   with patch.dict(os.environ,{'GHOST_MUSICKIT_ENDPOINT':url,'GHOST_MUSICKIT_TOKEN':'x'*40}),patch.object(musickit_client.httpx,'Client') as client:
    self.assertIn('no está preparado',musickit_client.execute({'action':'pause'}));client.assert_not_called()
 def test_catalog_routing_requires_permission(self):
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_ENABLE_MUSIC':'1','GHOST_PUBLIC':'0','GHOST_MUSIC_MODE':'catalog'}),patch.object(music_actions.platform,'system',return_value='Darwin'),patch.object(musickit_client,'execute',return_value='Reproduciendo: Sonne') as call,patch.object(music_actions.subprocess,'run') as script:
   self.assertIn('Sonne',music_actions.execute({'action':'play','query':'Rammstein'}));script.assert_not_called();call.assert_called_once()
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_ENABLE_MUSIC':'1','GHOST_PUBLIC':'1','GHOST_MUSIC_MODE':'catalog'}),patch.object(musickit_client,'execute') as call:
   music_actions.execute({'action':'pause'});call.assert_not_called()
 def test_transport_no_proxies_or_redirects(self):
  with patch.dict(os.environ,{'GHOST_MUSICKIT_ENDPOINT':'http://127.0.0.1:12345/music','GHOST_MUSICKIT_TOKEN':'x'*40}),patch.object(musickit_client.httpx,'Client') as constructor:
   client=constructor.return_value.__enter__.return_value;client.post.return_value.json.return_value={'ok':True,'message':'Música en pausa.'}
   self.assertEqual(musickit_client.execute({'action':'pause'}),'Música en pausa.')
   self.assertFalse(constructor.call_args.kwargs['trust_env']);self.assertFalse(constructor.call_args.kwargs['follow_redirects'])
