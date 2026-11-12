import os,sys,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import music_actions as m

class MusicTests(unittest.TestCase):
 def test_intents(self):
  for text,action in [('reproduce Rammstein','play'),('Oye Vox, pausa la música','pause'),('reanuda la música','resume'),('siguiente canción','next'),('canción anterior','previous')]:
   self.assertEqual(m.intent(text)['action'],action)
  for text in ['no reproduce Rammstein','¿puedes controlar Música?','qué canción sigue','abre Música']:self.assertIsNone(m.intent(text))
 def test_gates_and_arguments(self):
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_ENABLE_MUSIC':'0','GHOST_PUBLIC':'0'}),patch.object(m.subprocess,'run') as run:
   self.assertIn('Activa',m.execute({'action':'pause'}));run.assert_not_called()
  with patch.dict(os.environ,{'GHOST_ENABLE_SKILLS':'1','GHOST_ENABLE_MUSIC':'1','GHOST_PUBLIC':'0'}),patch.object(m.platform,'system',return_value='Darwin'),patch.object(m.app_catalog,'resolve_app',return_value=({'id':'/System/Applications/Music.app'},None)),patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='PLAYING: Sonne — Rammstein',stderr='')) as run:
   query='Rammstein " & do shell script "bad'
   self.assertIn('Sonne',m.execute({'action':'play','query':query}))
   self.assertEqual(run.call_args.args[0][-1],query)
   self.assertNotIn(query,run.call_args.kwargs['input'])
   self.assertFalse(run.call_args.kwargs['shell'])
 def test_invalid(self):
  with patch.object(m.subprocess,'run') as run:
   self.assertIn('no válido',m.execute({'action':'shell'}));run.assert_not_called()
if __name__=='__main__':unittest.main()
