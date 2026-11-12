import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import wake_voice

class WakeKeywordTests(unittest.TestCase):
    def word(self,text,start,end,confidence=1):return {'word':text,'start':start,'end':end,'conf':confidence}
    def test_keyword_is_near_the_beginning_with_required_confidence(self):
        words=[self.word('[unk]',0,.03,.5),self.word('oye',.04,.24,.89),self.word('vox',.27,.54)]
        self.assertEqual(wake_voice.keyword_end(words),.54)
        for invalid in [[self.word('oye',1,1.2),self.word('vox',1.2,1.5)],[self.word('oye',0,.2,.4),self.word('vox',.2,.5)],[self.word('oye',0,.2),self.word('vox',.2,.5,.6)],[self.word('oye',0,.2),self.word('vox',2,2.4)],[self.word('hola',0,.2),*words],[self.word('[unk]',0,.3),*words[1:]],[]]:
            self.assertIsNone(wake_voice.keyword_end(invalid))
    def test_invalid_audio_never_loads_native_model(self):
        with patch.object(wake_voice,'_load') as load:
            with self.assertRaises(ValueError):wake_voice.detect(b'not audio')
            load.assert_not_called()
